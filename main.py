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

@app.get("/")
def read_root():
    return {"status": "online", "endpoints": ["/health", "/api/market-data", "/api/market/vix", "/api/market/wti"]}

@app.get("/health")
def health_check():
    return {"status": "awake"}

@app.get("/api/market-data")
async def get_market_data():
    vix_data = await fetch_vix()
    wti_data = await fetch_wti()
    return {"vix": vix_data, "wti": wti_data}

@app.get("/api/market/vix")
async def get_vix():
    data = await fetch_vix()
    if not data:
        raise HTTPException(status_code=404, detail="VIX data unavailable")
    return data

@app.get("/api/market/wti")
async def get_wti():
    data = await fetch_wti()
    if not data:
        raise HTTPException(status_code=404, detail="WTI data unavailable")
    return data

async def fetch_vix():
    async with httpx.AsyncClient(headers=HEADERS, timeout=10.0, follow_redirects=True) as client:
        try:
            vix_res = await client.get("https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX")
            if vix_res.status_code == 200:
                meta = vix_res.json()["chart"]["result"][0]["meta"]
                return {
                    "price": meta.get("regularMarketPrice"),
                    "prev": meta.get("chartPreviousClose"),
                    "source": "Yahoo API"
                }
        except Exception:
            pass

        try:
            cnbc_vix = await client.get("https://www.cnbc.com/quotes/.VIX")
            soup = BeautifulSoup(cnbc_vix.text, "html.parser")
            price_meta = soup.find("meta", {"itemprop": "price"})
            if price_meta and price_meta.get("content"):
                return {
                    "price": float(price_meta["content"]),
                    "prev": None,
                    "source": "CNBC Scrape"
                }
        except Exception:
            pass
    return None

async def fetch_wti():
    async with httpx.AsyncClient(headers=HEADERS, timeout=10.0, follow_redirects=True) as client:
        try:
            wti_res = await client.get("https://query1.finance.yahoo.com/v8/finance/chart/CL=F")
            if wti_res.status_code == 200:
                meta = wti_res.json()["chart"]["result"][0]["meta"]
                return {
                    "price": meta.get("regularMarketPrice"),
                    "prev": meta.get("chartPreviousClose"),
                    "source": "Yahoo API"
                }
        except Exception:
            pass
    return None
