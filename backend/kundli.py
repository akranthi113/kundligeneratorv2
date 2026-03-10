from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import floor
from pathlib import Path
from typing import Any, Literal

try:
    import swisseph as swe  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    # Use the official Swiss Ephemeris DLL (Windows) when pyswisseph isn't available.
    from . import swe_ctypes as swe


SIGN_NAMES = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]


@dataclass(frozen=True)
class Lon:
    abs_deg: float

    @property
    def norm(self) -> float:
        v = self.abs_deg % 360.0
        # Normalize -0.0 to 0.0 for nicer JSON.
        return 0.0 if abs(v) < 1e-12 else v

    @property
    def sign_index(self) -> int:
        return int(floor(self.norm / 30.0))

    @property
    def sign_name(self) -> str:
        return SIGN_NAMES[self.sign_index]

    @property
    def deg_in_sign(self) -> float:
        return self.norm - (self.sign_index * 30.0)


def _parse_tz_offset(tz_offset: str) -> timezone:
    # Accept "+05:30", "-04:00", "+0530", "-0400", "5.5".
    s = tz_offset.strip()
    if not s:
        return timezone.utc

    if ":" in s:
        sign = 1
        if s[0] in "+-":
            sign = 1 if s[0] == "+" else -1
            s = s[1:]
        hh, mm = s.split(":", 1)
        minutes = sign * (int(hh) * 60 + int(mm))
        return timezone(timedelta(minutes=minutes))

    if len(s) in (5, 4) and s[0] in "+-":
        sign = 1 if s[0] == "+" else -1
        digits = s[1:]
        if len(digits) == 4:
            minutes = sign * (int(digits[:2]) * 60 + int(digits[2:]))
            return timezone(timedelta(minutes=minutes))
        # "+530" style is ambiguous; reject.

    # Fallback: hours as float, e.g. "5.5" or "-4"
    try:
        hours = float(s)
    except ValueError as e:
        raise ValueError(f"Invalid tz_offset: {tz_offset!r}") from e
    minutes = int(round(hours * 60))
    return timezone(timedelta(minutes=minutes))


def _to_jd_ut(local_dt: datetime, tz: timezone) -> float:
    aware = local_dt.replace(tzinfo=tz)
    utc_dt = aware.astimezone(timezone.utc)
    hour = (
        utc_dt.hour
        + utc_dt.minute / 60.0
        + utc_dt.second / 3600.0
        + utc_dt.microsecond / 3_600_000_000.0
    )
    return swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, hour, swe.GREG_CAL)


def _house_of(lon: float, cusps: list[float]) -> int:
    # cusps are 1..12 in zodiac order; Swiss Ephemeris returns them that way.
    lon_n = lon % 360.0
    for i in range(12):
        start = cusps[i] % 360.0
        end = cusps[(i + 1) % 12] % 360.0
        if end <= start:
            end += 360.0
        probe = lon_n
        if probe < start:
            probe += 360.0
        if start <= probe < end:
            return i + 1
    return 12


def _swe_setup(ephe_path: Path, zodiac: Literal["sidereal", "tropical"], ayanamsa: str) -> int:
    swe.set_ephe_path(str(ephe_path))
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    
    if zodiac == "sidereal":
        # Sidereal (Vedic) output with Lahiri or other ayanamsa.
        mode_map = {
            "lahiri": swe.SIDM_LAHIRI,
            "krishnamurti": swe.SIDM_KRISHNAMURTI,
            "raman": swe.SIDM_RAMAN,
            "fagan_bradley": swe.SIDM_FAGAN_BRADLEY,
        }
        sidm = mode_map.get(ayanamsa.strip().lower(), swe.SIDM_LAHIRI)
        swe.set_sid_mode(sidm, 0, 0)
        flags |= swe.FLG_SIDEREAL
    # else: tropical mode uses default (no sidereal flag)
    
    return flags


def compute_kundli(
    *,
    ephe_path: Path,
    date: str,
    time: str,
    tz_offset: str,
    lat: float,
    lon: float,
    # Kept as args for backward-compat, but sidereal is enforced in _swe_setup().
    zodiac: Literal["sidereal", "tropical"] = "sidereal",
    ayanamsa: str = "lahiri",
    node: Literal["mean", "true"] = "mean",
    house_system: str = "P",
) -> dict[str, Any]:
    local_dt = datetime.fromisoformat(f"{date}T{time}")
    tz = _parse_tz_offset(tz_offset)
    jd_ut = _to_jd_ut(local_dt, tz)

    flags = _swe_setup(ephe_path, zodiac, ayanamsa)

    # Houses (cusps[1..12]) and ascmc[0]=Asc, ascmc[1]=MC
    # pyswisseph/swe_ctypes signature: (jd, lat, lon, hsys, iflag)
    cusps_arr, ascmc = swe.houses_ex(jd_ut, lat, lon, house_system.encode(), flags)
    cusps = [float(cusps_arr[i]) for i in range(1, 13)]
    asc = float(ascmc[0])
    mc = float(ascmc[1])

    bodies: list[tuple[str, int]] = [
        ("Sun", swe.SUN),
        ("Moon", swe.MOON),
        ("Mars", swe.MARS),
        ("Mercury", swe.MERCURY),
        ("Jupiter", swe.JUPITER),
        ("Venus", swe.VENUS),
        ("Saturn", swe.SATURN),
        ("Uranus", getattr(swe, "URANUS", 7)),
        ("Neptune", getattr(swe, "NEPTUNE", 8)),
        ("Pluto", getattr(swe, "PLUTO", 9)),
    ]

    node_id = swe.MEAN_NODE if node == "mean" else swe.TRUE_NODE
    bodies.append(("Rahu", node_id))

    planets: list[dict[str, Any]] = []
    planet_file: str | None = None
    moon_file: str | None = None
    for name, body in bodies:
        xx, retflag = swe.calc_ut(jd_ut, body, flags)
        # Ensure we are actually using Swiss Ephemeris data files (se*.se1),
        # not silently falling back to another ephemeris.
        if (retflag & swe.FLG_SWIEPH) == 0:
            raise RuntimeError(
                "Swiss Ephemeris data files were not used for calculation. "
                f"Check that .se1 files are present in: {ephe_path}"
            )
        # Expose which ephemeris file Swiss Ephemeris actually used.
        # ifno=0: planet file sepl_xxx; ifno=1: moon file semo_xxx
        if name == "Sun" and hasattr(swe, "get_current_file_data"):
            planet_file, _, _, _ = swe.get_current_file_data(0)
        if name == "Moon" and hasattr(swe, "get_current_file_data"):
            moon_file, _, _, _ = swe.get_current_file_data(1)
        lon_abs = float(xx[0])
        speed = float(xx[3])
        pos = Lon(lon_abs)
        planets.append(
            {
                "name": name,
                "longitude": round(pos.norm, 6),
                "sign_index": pos.sign_index,
                "sign": pos.sign_name,
                "deg_in_sign": round(pos.deg_in_sign, 6),
                "speed": round(speed, 9),
                "retrograde": bool(speed < 0.0),
                "house": _house_of(pos.norm, cusps),
            }
        )

    # Ketu is always 180 degrees opposite Rahu in ecliptic longitude.
    rahu = next(p for p in planets if p["name"] == "Rahu")
    rahu_lon = float(rahu["longitude"])
    ketu_abs = (float(rahu_lon) + 180.0) % 360.0
    ketu = Lon(ketu_abs)
    ketu_speed = rahu.get("speed")
    planets.append(
        {
            "name": "Ketu",
            "longitude": round(ketu.norm, 6),
            "sign_index": ketu.sign_index,
            "sign": ketu.sign_name,
            "deg_in_sign": round(ketu.deg_in_sign, 6),
            "speed": ketu_speed,
            "retrograde": bool(rahu.get("retrograde", True)),
            "house": _house_of(ketu.norm, cusps),
        }
    )

    houses: list[dict[str, Any]] = []
    for i, c in enumerate(cusps, start=1):
        p = Lon(c)
        houses.append(
            {
                "house": i,
                "cusp_longitude": round(p.norm, 6),
                "sign_index": p.sign_index,
                "sign": p.sign_name,
                "deg_in_sign": round(p.deg_in_sign, 6),
            }
        )

    asc_pos = Lon(asc)
    mc_pos = Lon(mc)

    return {
        "meta": {
            "jd_ut": round(float(jd_ut), 9),
            "zodiac": "sidereal",
            "ayanamsa": ayanamsa,
            "node": node,
            "house_system": house_system,
            "flags": int(flags),
            "ephe_files": {
                "planets": planet_file,
                "moon": moon_file,
            },
        },
        "angles": {
            "ascendant": {
                "longitude": round(asc_pos.norm, 6),
                "sign_index": asc_pos.sign_index,
                "sign": asc_pos.sign_name,
                "deg_in_sign": round(asc_pos.deg_in_sign, 6),
            },
            "mc": {
                "longitude": round(mc_pos.norm, 6),
                "sign_index": mc_pos.sign_index,
                "sign": mc_pos.sign_name,
                "deg_in_sign": round(mc_pos.deg_in_sign, 6),
            },
        },
        "planets": planets,
        "houses": houses,
    }
