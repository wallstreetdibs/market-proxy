from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx
from bs4 import BeautifulSoup
import random

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
]

# In-memory server-side cache
CACHE = {
    "vix": None,
    "wti": None
}

def get_random_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    }

# --- VIX Fetchers ---
async def fetch_vix_yahoo(client: httpx.AsyncClient):
    res = await client.get("https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX")
    if res.status_code == 200:
        meta = res.json()["chart"]["result"][0]["meta"]
        price = meta.get("regularMarketPrice")
        prev = meta.get("chartPreviousClose")
        if price is not None:
            return {"price": float(price), "prev": float(prev) if prev else None, "source": "Yahoo API"}
    return None

async def fetch_vix_cnbc(client: httpx.AsyncClient):
    res = await client.get("https://www.cnbc.com/quotes/.VIX")
    if res.status_code == 200:
        soup = BeautifulSoup(res.text, "html.parser")
        meta = soup.find("meta", {"itemprop": "price"})
        if meta and meta.get("content"):
            return {"price": float(meta["content"]), "prev": None, "source": "CNBC Scrape"}
    return None

async def fetch_vix_stooq(client: httpx.AsyncClient):
    res = await client.get("https://stooq.com/q/l/?s=^vix&f=sdgl1otc&e=csv")
    if res.status_code == 200 and "Date" in res.text:
        lines = res.text.strip().split("\n")
        if len(lines) >= 2:
            parts = lines[1].split(",")
            if len(parts) >= 5 and parts[4] != "N/D":
                return {"price": float(parts[4]), "prev": None, "source": "Stooq"}
    return None

# --- WTI Fetchers ---
async def fetch_wti_yahoo(client: httpx.AsyncClient):
    res = await client.get("https://query1.finance.yahoo.com/v8/finance/chart/CL=F")
    if res.status_code == 200:
        meta = res.json()["chart"]["result"][0]["meta"]
        price = meta.get("regularMarketPrice")
        prev = meta.get("chartPreviousClose")
        if price is not None:
            return {"price": float(price), "prev": float(prev) if prev else None, "source": "Yahoo API"}
    return None

async def fetch_wti_cnbc(client: httpx.AsyncClient):
    res = await client.get("https://www.cnbc.com/quotes/@CL.1")
    if res.status_code == 200:
        soup = BeautifulSoup(res.text, "html.parser")
        meta = soup.find("meta", {"itemprop": "price"})
        if meta and meta.get("content"):
            return {"price": float(meta["content"]), "prev": None, "source": "CNBC Scrape"}
    return None

async def fetch_wti_stooq(client: httpx.AsyncClient):
    res = await client.get("https://stooq.com/q/l/?s=cl.f&f=sdgl1otc&e=csv")
    if res.status_code == 200 and "Date" in res.text:
        lines = res.text.strip().split("\n")
        if len(lines) >= 2:
            parts = lines[1].split(",")
            if len(parts) >= 5 and parts[4] != "N/D":
                return {"price": float(parts[4]), "prev": None, "source": "Stooq"}
    return None

@app.get("/")
def read_root():
    return {"status": "online", "endpoints": ["/health", "/api/market-data"]}

@app.get("/health")
def health_check():
    return {"status": "awake"}

@app.get("/api/market-data")
async def get_market_data():
    headers = get_random_headers()
    
    async with httpx.AsyncClient(headers=headers, timeout=8.0, follow_redirects=True) as client:
        # 1. Fetch VIX through multi-tiered fallbacks
        vix_data = None
        for vix_fetcher in [fetch_vix_yahoo, fetch_vix_cnbc, fetch_vix_stooq]:
            try:
                vix_data = await vix_fetcher(client)
                if vix_data:
                    vix_data["stale"] = False
                    CACHE["vix"] = vix_data
                    break
            except Exception:
                continue

        if not vix_data and CACHE["vix"]:
            vix_data = CACHE["vix"].copy()
            vix_data["stale"] = True

        # 2. Fetch WTI Crude through multi-tiered fallbacks
        wti_data = None
        for wti_fetcher in [fetch_wti_yahoo, fetch_wti_cnbc, fetch_wti_stooq]:
            try:
                wti_data = await wti_fetcher(client)
                if wti_data:
                    wti_data["stale"] = False
                    CACHE["wti"] = wti_data
                    break
            except Exception:
                continue

        if not wti_data and CACHE["wti"]:
            wti_data = CACHE["wti"].copy()
            wti_data["stale"] = True

    return {
        "vix": vix_data,
        "wti": wti_data
    }
