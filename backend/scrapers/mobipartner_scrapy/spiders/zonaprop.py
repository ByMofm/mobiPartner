import json
import re

import scrapy
from scrapy_playwright.page import PageMethod

from mobipartner_scrapy.items import PropertyItem


class ZonaPropSpider(scrapy.Spider):
    """Spider for ZonaProp using Playwright (Firefox).

    Extracts all data from listing cards — no detail page visits.
    Card selectors confirmed: POSTING_CARD_PRICE, POSTING_CARD_FEATURES,
    POSTING_CARD_LOCATION, POSTING_CARD_DESCRIPTION, img[src*=zonapropcdn].
    """

    name = "zonaprop"
    allowed_domains = ["www.zonaprop.com.ar"]

    BASE_URL = "https://www.zonaprop.com.ar"
    MAX_PAGES = 50

    SEARCHES = [
        ("departamentos-venta-tucuman", "departamento", "venta"),
        ("departamentos-alquiler-tucuman", "departamento", "alquiler"),
        ("casas-venta-tucuman", "casa", "venta"),
        ("casas-alquiler-tucuman", "casa", "alquiler"),
        ("terrenos-venta-tucuman", "terreno", "venta"),
        ("ph-venta-tucuman", "ph", "venta"),
        ("locales-comerciales-venta-tucuman", "local", "venta"),
        ("locales-comerciales-alquiler-tucuman", "local", "alquiler"),
        ("oficinas-venta-tucuman", "oficina", "venta"),
        ("cocheras-venta-tucuman", "cochera", "venta"),
    ]

    custom_settings = {
        "PLAYWRIGHT_BROWSER_TYPE": "firefox",
        "DOWNLOAD_DELAY": 3,
        "CONCURRENT_REQUESTS": 1,
        "ROBOTSTXT_OBEY": False,
        "COOKIES_ENABLED": False,
        "DOWNLOADER_MIDDLEWARES": {
            "mobipartner_scrapy.middlewares.RotateUserAgentMiddleware": None,
        },
        "USER_AGENT": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
    }

    def start_requests(self):
        for slug, prop_type, listing_type in self.SEARCHES:
            url = f"{self.BASE_URL}/{slug}.html"
            yield scrapy.Request(
                url,
                meta={
                    "playwright": True,
                    "playwright_context": f"zp-{slug}-p1",
                    "playwright_page_methods": [
                        PageMethod("wait_for_load_state", "networkidle"),
                    ],
                    "property_type": prop_type,
                    "listing_type": listing_type,
                    "page": 1,
                    "slug": slug,
                },
                callback=self.parse_listing_page,
                errback=self.handle_error,
            )

    def handle_error(self, failure):
        self.logger.error(f"Request failed: {failure.request.url} — {failure.value}")

    def _extract_geo_from_page(self, response) -> dict:
        """Extract {posting_id: {lat, lng}} from ZonaProp's embedded __PRELOADED_STATE__."""
        geo_map = {}

        text = response.text
        marker = "__PRELOADED_STATE__ = {"
        idx = text.find(marker)
        if idx == -1:
            return geo_map

        try:
            start = idx + len(marker) - 1  # position of the opening {
            state, _ = json.JSONDecoder().raw_decode(text, start)
            postings = state.get("listStore", {}).get("listPostings", [])
            for p in postings:
                pid = str(p.get("postingId", ""))
                geo = (
                    p.get("postingLocation", {})
                    .get("postingGeolocation", {})
                    .get("geolocation", {})
                )
                lat = geo.get("latitude")
                lng = geo.get("longitude")
                if pid and lat and lng:
                    geo_map[pid] = {"lat": float(lat), "lng": float(lng)}
        except Exception as e:
            self.logger.debug(f"Could not parse __PRELOADED_STATE__: {e}")

        return geo_map

    def parse_listing_page(self, response):
        cards = response.css("div[data-posting-type=PROPERTY]")

        self.logger.info(
            f"Page {response.meta['page']} — {response.url}: {len(cards)} listings"
        )

        geo_map = self._extract_geo_from_page(response)
        self.logger.info(f"Geo data found for {len(geo_map)} postings on this page")

        for card in cards:
            source_id = card.attrib.get("data-id", "")
            detail_path = card.attrib.get("data-to-posting", "")
            if not source_id:
                continue

            item = PropertyItem()
            item["source"] = "zonaprop"
            item["source_id"] = source_id
            item["source_url"] = (
                self.BASE_URL + detail_path.split("?")[0]
                if detail_path else response.url
            )
            item["property_type"] = response.meta["property_type"]
            item["listing_type"] = response.meta["listing_type"]

            # Price: "USD 130.000" or "$ 85.000.000"
            price_text = card.css("[data-qa=POSTING_CARD_PRICE]::text").get("").strip()
            item["price"], item["currency"] = self._parse_price(price_text)

            # Location — join all parts for a fuller address
            location_parts = [
                t.strip() for t in card.css("[data-qa=POSTING_CARD_LOCATION]::text, [data-qa=POSTING_CARD_LOCATION] *::text").getall()
                if t.strip()
            ]
            item["address"] = ", ".join(dict.fromkeys(location_parts)) if location_parts else ""

            # Coordinates from embedded page data
            geo = geo_map.get(source_id, {})
            item["latitude"] = geo.get("lat")
            item["longitude"] = geo.get("lng")

            # Features: "152 m² tot.\n6 amb.\n3 dorm.\n2 baños\n1 coch."
            feat_text = card.css("[data-qa=POSTING_CARD_FEATURES]::text").get("").strip()
            feats = self._parse_features(feat_text)
            item["total_area_m2"] = feats.get("total_area_m2")
            item["covered_area_m2"] = feats.get("covered_area_m2")
            item["rooms"] = feats.get("rooms")
            item["bedrooms"] = feats.get("bedrooms")
            item["bathrooms"] = feats.get("bathrooms")
            item["garages"] = feats.get("garages")
            item["age_years"] = None

            # Description (used as title too since cards have no h1)
            desc = card.css("[data-qa=POSTING_CARD_DESCRIPTION]::text").get("").strip()
            item["title"] = desc[:120] if desc else item["address"]
            item["description"] = desc

            # Apto crédito hipotecario — check URL slug, description, and address
            all_text = (item.get("source_url", "") + " " + desc + " " + item["address"]).lower()
            item["apto_credito"] = "crédito" in all_text or "credito" in all_text or "hipotecario" in all_text

            # Images from card gallery
            images = card.css(
                "img[src*='zonapropcdn.com']::attr(src), "
                "img[data-flickity-lazyload*='zonapropcdn']::attr(data-flickity-lazyload)"
            ).getall()
            item["image_urls"] = [
                img for img in dict.fromkeys(images)
                if img and "placeholder" not in img and "empresas" not in img
            ]

            item["raw_data"] = {"url": item["source_url"], "features_text": feat_text}

            yield item

        # Pagination
        page = response.meta["page"]
        if page < self.MAX_PAGES:
            next_href = response.css("a[data-qa=PAGING_NEXT]::attr(href)").get()
            if next_href:
                yield scrapy.Request(
                    self.BASE_URL + next_href if next_href.startswith("/") else next_href,
                    meta={
                        "playwright": True,
                        "playwright_context": f"zp-{response.meta['slug']}-p{page + 1}",
                        "playwright_page_methods": [
                            PageMethod("wait_for_selector", "div[data-posting-type]", timeout=30000),
                        ],
                        "property_type": response.meta["property_type"],
                        "listing_type": response.meta["listing_type"],
                        "page": page + 1,
                        "slug": response.meta["slug"],
                    },
                    callback=self.parse_listing_page,
                    errback=self.handle_error,
                )

    def _parse_features(self, text: str) -> dict:
        """Parse card feature line: '152 m² tot.\n6 amb.\n3 dorm.\n2 baños\n1 coch.'"""
        result = {}
        if not text:
            return result
        for part in re.split(r"[\n·|]", text):
            part = part.strip()
            num = re.search(r"[\d.,]+", part)
            if not num:
                continue
            val_str = num.group().replace(".", "").replace(",", ".")
            try:
                val = float(val_str)
            except ValueError:
                continue
            low = part.lower()
            if "m²" in low and "cub" in low:
                result["covered_area_m2"] = val
            elif "m²" in low:
                result["total_area_m2"] = val
            elif "amb" in low:
                result["rooms"] = int(val)
            elif "dorm" in low or "hab" in low:
                result["bedrooms"] = int(val)
            elif "baño" in low or "bano" in low:
                result["bathrooms"] = int(val)
            elif "coch" in low or "gar" in low:
                result["garages"] = int(val)
        return result

    def _parse_price(self, text: str) -> tuple:
        if not text or not text.strip():
            return None, None
        text = text.strip()
        currency = "USD" if any(s in text for s in ("USD", "U$S", "US$")) else "ARS"
        numbers = re.findall(r"[\d.,]+", text)
        if numbers:
            try:
                return float(numbers[0].replace(".", "").replace(",", ".")), currency
            except ValueError:
                pass
        return None, currency
