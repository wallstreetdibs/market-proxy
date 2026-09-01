from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
from bs4 import BeautifulSoup

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

@app.get("/health")
def health_check():
    return {"status": "awake"}

@app.get("/api/market-data")
async def get_market_data():
    data = {"vix": None, "wti": None}
    
    async with httpx.AsyncClient(headers=HEADERS, timeout=10.0, follow_redirects=True) as client:
        # Fetch VIX via Yahoo Finance API backend
        try:
            vix_res = await client.get("https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX")
            if vix_res.status_code == 200:
                vix_json = vix_res.json()
                meta = vix_json["chart"]["result"][0]["meta"]
                data["vix"] = {
                    "price": meta.get("regularMarketPrice"),
                    "prev": meta.get("chartPreviousClose"),
                    "source": "Yahoo API"
                }
        except Exception:
            pass

        # Fallback to scraping CNBC for VIX if API fails
        if not data["vix"]:
            try:
                cnbc_vix = await client.get("https://www.cnbc.com/quotes/.VIX")
                soup = BeautifulSoup(cnbc_vix.text, "html.parser")
                price_meta = soup.find("meta", {"itemprop": "price"})
                if price_meta and price_meta.get("content"):
                    data["vix"] = {
                        "price": float(price_meta["content"]),
                        "prev": None,
                        "source": "CNBC Scrape"
                    }
            except Exception:
                pass

        # Fetch WTI Crude via Yahoo Finance API backend
        try:
            wti_res = await client.get("https://query1.finance.yahoo.com/v8/finance/chart/CL=F")
            if wti_res.status_code == 200:
                wti_json = wti_res.json()
                meta = wti_json["chart"]["result"][0]["meta"]
                data["wti"] = {
                    "price": meta.get("regularMarketPrice"),
                    "prev": meta.get("chartPreviousClose"),
                    "source": "Yahoo API"
                }
        except Exception:
            pass

    return data
