import httpx

headers = {"User-Agent": "Mozilla/5.0"}

r = httpx.get("https://api.mercadolibre.com/sites/MLA/categories", headers=headers)
print("Categories:", r.status_code)

r2 = httpx.get(
    "https://api.mercadolibre.com/sites/MLA/search?q=departamento+tucuman&limit=2",
    headers=headers,
)
print("Search:", r2.status_code, r2.text[:300])
