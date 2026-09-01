from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from bs4 import BeautifulSoup
import httpx
import random
import asyncio

app = FastAPI()

# Enable CORS for your client dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Randomized User-Agents to prevent bot detection and blocking
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0"
]

SCRAPE_TARGETS = {
    "vix": [
        {"name": "CNBC", "url": "https://www.cnbc.com/quotes/.VIX"},
        {"name": "MarketWatch", "url": "https://www.marketwatch.com/investing/index/vix"}
    ],
    "wti": [
        {"name": "CNBC", "url": "https://www.cnbc.com/quotes/@CL.1"},
        {"name": "MarketWatch", "url": "https://www.marketwatch.com/investing/future/crude%20oil%20-%20electronic"}
    ]
}

async def fetch_html(url: str) -> str:
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.text

@app.get("/api/market/{asset}")
async def get_market_value(asset: str):
    asset_key = asset.lower()
    if asset_key not in SCRAPE_TARGETS:
        return {"error": "Invalid asset. Use 'vix' or 'wti'."}, 400

    for source in SCRAPE_TARGETS[asset_key]:
        try:
            html = await fetch_html(source["url"])
            soup = BeautifulSoup(html, "html.parser")
            
            val = None
            if source["name"] == "CNBC":
                meta = soup.find("meta", {"itemprop": "price"})
                if meta and meta.get("content"):
                    val = float(meta["content"].replace(",", ""))
            elif source["name"] == "MarketWatch":
                meta = soup.find("meta", {"name": "price"})
                if meta and meta.get("content"):
                    val = float(meta["content"].replace(",", ""))

            if val is not None:
                return {"asset": asset_key, "price": val, "source": source["name"]}
        except Exception as e:
            continue

    return {"error": f"Failed to fetch live data for {asset_key}"}, 500
