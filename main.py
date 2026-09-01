from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SYMBOLS = {
    "vix": "^VIX",
    "wti": "CL=F"
}

@app.get("/api/market/{asset}")
async def get_market_value(asset: str):
    asset_key = asset.lower()
    if asset_key not in SYMBOLS:
        return {"error": "Invalid asset. Use 'vix' or 'wti'."}, 400

    symbol = SYMBOLS[asset_key]
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            price = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
            return {"asset": asset_key, "price": float(price), "source": "Yahoo Finance"}
    except Exception as e:
        return {"error": f"Failed to fetch live data for {asset_key}"}, 500
