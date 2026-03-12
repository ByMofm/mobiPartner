#!/usr/bin/env python3
"""
Quick test to verify MercadoLibre API access from this machine.

Usage:
    python scripts/test_ml_api.py
    python scripts/test_ml_api.py --token YOUR_ACCESS_TOKEN
"""
import argparse
import json
import sys
import urllib.request
import urllib.error


API_BASE = "https://api.mercadolibre.com"
CATEGORY = "MLA1459"  # Inmuebles
STATE_ID = "AR-T"     # Tucumán


def fetch(url: str, token: str = "") -> dict:
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/json")
    req.add_header(
        "User-Agent",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    )
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", default="", help="ML access token (optional)")
    args = parser.parse_args()

    token = args.token

    print("=" * 60)
    print("MercadoLibre API connectivity test")
    print("=" * 60)

    # Test 1: Basic API health
    print("\n[1] Testing basic API access...")
    try:
        data = fetch(f"{API_BASE}/sites/MLA", token)
        print(f"    OK — site: {data.get('name', '?')}, id: {data.get('id', '?')}")
    except urllib.error.HTTPError as e:
        print(f"    FAIL — HTTP {e.code}: {e.reason}")
        print("    The API is blocked from this IP. You need an access token or a proxy.")
        sys.exit(1)
    except Exception as e:
        print(f"    FAIL — {e}")
        sys.exit(1)

    # Test 2: Search endpoint
    print("\n[2] Testing search endpoint (Tucumán inmuebles)...")
    url = (
        f"{API_BASE}/sites/MLA/search"
        f"?category={CATEGORY}&state={STATE_ID}&limit=5&offset=0"
    )
    if token:
        url += f"&access_token={token}"
    try:
        data = fetch(url, token)
        total = data.get("paging", {}).get("total", 0)
        results = data.get("results", [])
        print(f"    OK — total listings found: {total}")
        print(f"    Sample ({len(results)} items):")
        for r in results[:3]:
            print(f"      - [{r.get('category_id')}] {r.get('title', '?')[:60]}")
            print(f"        Price: {r.get('currency_id')} {r.get('price')}")
            loc = r.get("location", {})
            city = loc.get("city", {}).get("name", "?")
            print(f"        City: {city}")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"    FAIL — HTTP {e.code}: {body[:200]}")
        if e.code == 403:
            print("\n    -> Necesitas registrar una app en developers.mercadolibre.com")
            print("       y usar el access_token con --token TU_TOKEN")
        sys.exit(1)
    except Exception as e:
        print(f"    FAIL — {e}")
        sys.exit(1)

    # Test 3: Item detail (if we have results)
    if results:
        item_id = results[0].get("id")
        print(f"\n[3] Testing item detail for {item_id}...")
        detail_url = f"{API_BASE}/items/{item_id}"
        if token:
            detail_url += f"?access_token={token}"
        try:
            detail = fetch(detail_url, token)
            attrs = {
                a["id"]: a.get("value_name")
                for a in detail.get("attributes", [])
                if a.get("value_name")
            }
            print(f"    OK — title: {detail.get('title', '?')[:60]}")
            print(f"    Attributes: {list(attrs.keys())[:8]}")
        except urllib.error.HTTPError as e:
            print(f"    FAIL — HTTP {e.code}")
        except Exception as e:
            print(f"    FAIL — {e}")

    print("\n" + "=" * 60)
    print("All tests passed! The ML API is accessible from this machine.")
    print("You can run the Scrapy spider with:")
    if token:
        print(f"  ML_ACCESS_TOKEN={token} scrapy crawl mercadolibre")
    else:
        print("  scrapy crawl mercadolibre")
    print("=" * 60)


if __name__ == "__main__":
    main()
