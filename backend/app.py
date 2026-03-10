from __future__ import annotations

from pathlib import Path
from typing import Literal
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .kundli import compute_kundli


REPO_ROOT = Path(__file__).resolve().parents[1]
EPHE_PATH = REPO_ROOT / "ephe"
WEB_DIR = REPO_ROOT / "web"


class KundliRequest(BaseModel):
    date: str = Field(..., examples=["1995-08-12"])
    time: str = Field(..., examples=["14:35"])
    tz_offset: str = Field(..., examples=["+05:30"])
    lat: float = Field(..., examples=[19.0760])
    lon: float = Field(..., examples=[72.8777])
    node: Literal["mean", "true"] = "mean"
    house_system: str = "P"


app = FastAPI(title="Kundli Generator", version="0.4.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": app.version, "mode": "sidereal_lahiri"}


@app.get("/api/geocode")
def api_geocode(q: str) -> dict:
    q = (q or "").strip()
    if len(q) < 2:
        raise HTTPException(status_code=400, detail="Query too short")

    # Free geocoder (no key): OpenStreetMap Nominatim.
    # Usage policy expects a descriptive User-Agent.
    params = {
        "q": q,
        "format": "jsonv2",
        "addressdetails": 1,
        "limit": 5,
    }
    url = "https://nominatim.openstreetmap.org/search?" + urlencode(params)
    req = Request(
        url,
        headers={
            "User-Agent": f"KundliGenerator2/{app.version} (local)",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8", "replace")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Geocoding failed: {e}") from e

    # Parse without extra deps.
    import json

    try:
        items = json.loads(raw)
    except Exception as e:
        raise HTTPException(status_code=502, detail="Invalid geocoder response") from e

    results = []
    for it in items if isinstance(items, list) else []:
        try:
            results.append(
                {
                    "display_name": it.get("display_name"),
                    "lat": float(it.get("lat")),
                    "lon": float(it.get("lon")),
                }
            )
        except Exception:
            continue

    return {"query": q, "results": results}


@app.post("/api/kundli")
def api_kundli(payload: KundliRequest) -> dict:
    if not EPHE_PATH.exists():
        raise HTTPException(status_code=500, detail=f"Ephemeris folder not found: {EPHE_PATH}")
    try:
        return compute_kundli(
            ephe_path=EPHE_PATH,
            date=payload.date,
            time=payload.time,
            tz_offset=payload.tz_offset,
            lat=payload.lat,
            lon=payload.lon,
            # Force pure sidereal (Vedic) output for consistent results.
            zodiac="sidereal",
            ayanamsa="lahiri",
            node=payload.node,
            house_system=payload.house_system,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
