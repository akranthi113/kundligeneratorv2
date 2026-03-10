from __future__ import annotations

import ctypes
from ctypes import c_char_p, c_double, c_int
from pathlib import Path

# Minimal Swiss Ephemeris binding via official Windows DLL.
# This avoids needing a C compiler for `pyswisseph` on Python 3.13.

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DLL = REPO_ROOT / "vendor" / "swe" / "swedll64.dll"

# Common Swiss Ephemeris constants (subset).
GREG_CAL = 1

FLG_JPLEPH = 1
FLG_SWIEPH = 2
FLG_MOSEPH = 4
FLG_SPEED = 256
# From vendor/swe/sweph/src/swephexp.h:
#   #define SEFLG_SIDEREAL (64*1024)
FLG_SIDEREAL = 64 * 1024

SUN = 0
MOON = 1
MERCURY = 2
VENUS = 3
MARS = 4
JUPITER = 5
SATURN = 6
URANUS = 7
NEPTUNE = 8
PLUTO = 9

MEAN_NODE = 10
TRUE_NODE = 11

# Sidereal modes (subset; values match Swiss Ephemeris `swephexp.h`).
SIDM_FAGAN_BRADLEY = 0
SIDM_LAHIRI = 1
SIDM_RAMAN = 3
SIDM_KRISHNAMURTI = 5


class SwissEphDll:
    def __init__(self, dll_path: Path) -> None:
        if not dll_path.exists():
            raise FileNotFoundError(
                f"Swiss Ephemeris DLL not found at {dll_path}. "
                "Download `swedll64.dll` into `vendor/swe/` (see scripts/fetch_swe_dll.ps1)."
            )

        self._dll = ctypes.WinDLL(str(dll_path))

        self._dll.swe_set_ephe_path.argtypes = [c_char_p]
        self._dll.swe_set_ephe_path.restype = None

        self._dll.swe_set_sid_mode.argtypes = [c_int, c_double, c_double]
        self._dll.swe_set_sid_mode.restype = None

        self._dll.swe_julday.argtypes = [c_int, c_int, c_int, c_double, c_int]
        self._dll.swe_julday.restype = c_double

        self._dll.swe_calc_ut.argtypes = [
            c_double,
            c_int,
            c_int,
            ctypes.POINTER(c_double),
            ctypes.c_char_p,
        ]
        self._dll.swe_calc_ut.restype = c_int

        self._dll.swe_houses_ex.argtypes = [
            c_double,
            c_int,
            c_double,
            c_double,
            c_int,  # char house system, passed as int
            ctypes.POINTER(c_double),
            ctypes.POINTER(c_double),
        ]
        self._dll.swe_houses_ex.restype = c_int

        self._dll.swe_get_current_file_data.argtypes = [
            c_int,
            ctypes.POINTER(c_double),
            ctypes.POINTER(c_double),
            ctypes.POINTER(c_int),
        ]
        self._dll.swe_get_current_file_data.restype = c_char_p

    def set_ephe_path(self, path: str) -> None:
        self._dll.swe_set_ephe_path(path.encode("utf-8"))

    def set_sid_mode(self, sid_mode: int, t0: float, ayan_t0: float) -> None:
        self._dll.swe_set_sid_mode(int(sid_mode), float(t0), float(ayan_t0))

    def julday(self, year: int, month: int, day: int, hour: float, gregflag: int) -> float:
        return float(self._dll.swe_julday(int(year), int(month), int(day), float(hour), int(gregflag)))

    def calc_ut(self, tjd_ut: float, ipl: int, iflag: int) -> tuple[list[float], int]:
        xx = (c_double * 6)()
        serr = ctypes.create_string_buffer(256)
        retflag = int(self._dll.swe_calc_ut(float(tjd_ut), int(ipl), int(iflag), xx, serr))
        if retflag < 0:
            raise RuntimeError(serr.value.decode("utf-8", "replace") or "Swiss Ephemeris error")
        return [float(v) for v in xx], retflag

    def houses_ex(
        self, tjd_ut: float, geolat: float, geolon: float, hsys: str | bytes, iflag: int = 0
    ) -> tuple[list[float], list[float]]:
        # pyswisseph/Render signature seems to be (jd, lat, lon, hsys, iflag)
        # where hsys is at position 4 (1-indexed).
        if isinstance(hsys, str):
            if len(hsys) != 1:
                raise ValueError("house_system must be a single character, e.g. 'P' or 'E'")
            hsys_code = ord(hsys)
        else:
            # bytes
            hsys_code = hsys[0]

        cusp = (c_double * 13)()
        ascmc = (c_double * 10)()
        _ = int(
            self._dll.swe_houses_ex(
                float(tjd_ut), int(iflag), float(geolat), float(geolon), hsys_code, cusp, ascmc
            )
        )
        return [float(v) for v in cusp], [float(v) for v in ascmc]

    def get_current_file_data(self, ifno: int) -> tuple[str | None, float, float, int]:
        tfstart = c_double(0.0)
        tfend = c_double(0.0)
        denum = c_int(0)
        p = self._dll.swe_get_current_file_data(int(ifno), ctypes.byref(tfstart), ctypes.byref(tfend), ctypes.byref(denum))
        if not p:
            return None, 0.0, 0.0, 0
        return p.decode("utf-8", "replace"), float(tfstart.value), float(tfend.value), int(denum.value)


_SWE = SwissEphDll(DEFAULT_DLL)


def set_ephe_path(path: str) -> None:
    _SWE.set_ephe_path(path)


def set_sid_mode(sid_mode: int, t0: float, ayan_t0: float) -> None:
    _SWE.set_sid_mode(sid_mode, t0, ayan_t0)


def julday(year: int, month: int, day: int, hour: float, gregflag: int) -> float:
    return _SWE.julday(year, month, day, hour, gregflag)


def calc_ut(tjd_ut: float, ipl: int, iflag: int) -> tuple[list[float], int]:
    return _SWE.calc_ut(tjd_ut, ipl, iflag)


def houses_ex(
    tjd_ut: float, geolat: float, geolon: float, hsys: str | bytes, iflag: int = 0
) -> tuple[list[float], list[float]]:
    return _SWE.houses_ex(tjd_ut, geolat, geolon, hsys, iflag)


def get_current_file_data(ifno: int) -> tuple[str | None, float, float, int]:
    return _SWE.get_current_file_data(ifno)
