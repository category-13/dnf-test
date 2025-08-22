import os, time, requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

API_KEY = os.getenv("NEOPLE_API_KEY")
if not API_KEY:
    raise RuntimeError("환경변수 NEOPLE_API_KEY가 없습니다.")

BASE = "https://api.dfoneople.com/df"

app = FastAPI(title="DNF Proxy")

# GitHub Pages 프로젝트 페이지의 ORIGIN(도메인)만 허용
# origin에는 경로(/dnf-test)는 포함하지 않음
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://category-13.github.io"],
    allow_methods=["*"], allow_headers=["*"]
)

_cache = {}  # 아주 단순한 메모리 캐시
def get_json(url, params=None, ttl=60):
    if params is None: params = {}
    params["apikey"] = API_KEY
    key = (url, tuple(sorted(params.items())))
    now = time.time()
    if key in _cache and _cache[key][0] > now:
        return _cache[key][1]
    r = requests.get(url, params=params, timeout=10)
    if r.status_code == 429:
        raise HTTPException(429, "Rate limited by Neople API")
    if not r.ok:
        raise HTTPException(r.status_code, r.text)
    js = r.json()
    _cache[key] = (now + ttl, js)
    return js

@app.get("/api/servers")
def servers():
    return get_json(f"{BASE}/servers", ttl=3600)

@app.get("/api/search")
def search(server: str, name: str):
    js = get_json(f"{BASE}/servers/{server}/characters",
                  params={"characterName": name, "limit": 10}, ttl=30)
    rows = js.get("rows", [])
    if not rows:
        raise HTTPException(404, "캐릭터 없음")
    return rows

@app.get("/api/character")
def character(server: str, characterId: str):
    base = f"{BASE}/servers/{server}/characters/{characterId}"
    basic = get_json(base, ttl=60)
    equip = get_json(f"{base}/equip/equipment", ttl=60)
    return {"basic": basic, "equipment": equip}
