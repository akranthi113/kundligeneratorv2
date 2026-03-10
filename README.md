# Kundli Generator (Website)

This is a small website that generates a Kundli using **Swiss Ephemeris `.se1` files** located in `./ephe`.

It calculates:
- 9 planets: Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, **Rahu**, **Ketu**
- 12 house cusps (degrees + sign)
- Ascendant and MC

## Run

From the repo root:

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File .\\scripts\\fetch_swe_dll.ps1
python -m uvicorn backend.app:app --reload --port 8000
```

Open `http://localhost:8000`.

## Notes

- Default zodiac is **Sidereal (Lahiri)**.
- Rahu can be Mean or True node; Ketu is computed as Rahu + 180 degrees.
- House system defaults to Placidus (`P`) but you can change it in the UI.
- Swiss Ephemeris is subject to its own license terms (see `sweph/src/LICENSE` inside the downloaded `sweph.zip`).
