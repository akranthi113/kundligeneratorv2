from typing import List, Dict, Any
from datetime import datetime, timedelta

# Planets in order of Vimshottari Dasha
PLANET_LORDS = [
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"
]

# Dasha periods in years
DASHA_YEARS = {
    "Ketu": 7,
    "Venus": 20,
    "Sun": 6,
    "Moon": 10,
    "Mars": 7,
    "Rahu": 18,
    "Jupiter": 16,
    "Saturn": 19,
    "Mercury": 17
}

NAKSHATRA_NAMES = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", 
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]

# Each Nakshatra is 13° 20' = 13.333333 degrees
# There are 27 Nakshatras in 360 degrees.
# Each Nakshatra is ruled by one of the 9 planets in a cycle.

def get_nakshatra_info(longitude: float) -> Dict[str, Any]:
    norm_lon = longitude % 360
    nak_deg = 360 / 27  # 13.333333
    nak_index = int(norm_lon / nak_deg)
    nak_name = NAKSHATRA_NAMES[nak_index]
    
    # Lord of Nakshatra
    # The cycle starts with Ashwini ruled by Ketu.
    lord_index = nak_index % 9
    nak_lord = PLANET_LORDS[lord_index]
    
    # Sub-lord calculation
    # A Nakshatra is divided into 9 parts proportional to the Vimshottari Dasha years.
    # Total years = 120
    # One Nakshatra = 13° 20' = 800 minutes
    # Sub portion = (Dasha years / 120) * 800 minutes
    
    elapsed_in_nak = norm_lon % nak_deg
    elapsed_minutes = elapsed_in_nak * 60
    
    current_min = 0.0
    sub_lord = ""
    # The sub-lord cycle starts with the Nakshatra Lord itself and follows the same sequence.
    # We use (lord_index + i) % 9 to ensure it starts with the planet that rules the Nakshatra.
    for i in range(9):
        l_idx = (lord_index + i) % 9
        l_name = PLANET_LORDS[l_idx]
        l_years = DASHA_YEARS[l_name]
        # One Nakshatra is 800 minutes. Total years = 120.
        l_minutes = (l_years / 120) * 800
        
        if current_min <= elapsed_minutes < current_min + l_minutes + 1e-9:
            sub_lord = l_name
            # Sub-Sub lord calculation (SS)
            # Divide the sub-lord portion further into 9 parts proportional to dasha years.
            # The SS cycle starts with the Sub-Lord itself.
            elapsed_in_sub = elapsed_minutes - current_min
            sub_sub_min = 0.0
            sub_sub_lord = ""
            for j in range(9):
                ss_idx = (l_idx + j) % 9
                ss_name = PLANET_LORDS[ss_idx]
                ss_years = DASHA_YEARS[ss_name]
                ss_minutes = (ss_years / 120) * l_minutes
                
                if sub_sub_min <= elapsed_in_sub < sub_sub_min + ss_minutes + 1e-9:
                    sub_sub_lord = ss_name
                    break
                sub_sub_min += ss_minutes
            
            return {
                "nakshatra": nak_name,
                "nak_lord": nak_lord,
                "sub_lord": sub_lord,
                "sub_sub_lord": sub_sub_lord
            }
        current_min += l_minutes
        
    return {
        "nakshatra": nak_name,
        "nak_lord": nak_lord,
        "sub_lord": PLANET_LORDS[lord_index], # Fallback
        "sub_sub_lord": PLANET_LORDS[lord_index]
    }

def get_day_lord(date_str: str) -> str:
    dt = datetime.fromisoformat(date_str)
    # 0 = Monday, 1 = Tuesday, ..., 6 = Sunday
    days = ["Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Sun"]
    return days[dt.weekday()]

def get_v_dasha(moon_lon: float, dob: datetime) -> List[Dict[str, Any]]:
    # Vimshottari Mahadasha
    # One Cycle = 120 Years
    # Current Nakshatra and elapsed part
    nak_deg = 360 / 27
    nak_index = int(moon_lon / nak_deg)
    lord_index = nak_index % 9
    
    elapsed_in_nak = moon_lon % nak_deg
    total_nak_deg = nak_deg
    
    # Balance of dasha at birth
    first_lord = PLANET_LORDS[lord_index]
    first_lord_years = DASHA_YEARS[first_lord]
    
    # Balance = (Remaining deg in Nak / Total Nak deg) * Total Dasha Years
    remaining_deg = total_nak_deg - elapsed_in_nak
    balance_years = (remaining_deg / total_nak_deg) * first_lord_years
    
    dashas = []
    current_start = dob
    
    # We'll calculate for one full cycle (120 years) starting from the birth dasha
    for i in range(9):
        l_idx = (lord_index + i) % 9
        l_name = PLANET_LORDS[l_idx]
        
        if i == 0:
            duration_days = balance_years * 365.25
        else:
            duration_days = DASHA_YEARS[l_name] * 365.25
            
        current_end = current_start + timedelta(days=duration_days)
        
        # Antardashas (Sub-dashas)
        antardashas = []
        # Total years for this Mahadasha
        m_years = DASHA_YEARS[l_name]
        m_start = current_start
        
        for j in range(9):
            a_idx = (l_idx + j) % 9
            a_name = PLANET_LORDS[a_idx]
            a_years = DASHA_YEARS[a_name]
            # Antardasha period = (M_years * A_years) / 120
            a_duration_days = (m_years * a_years / 120) * 365.25
            
            # If it's the first MD, we need to adjust the first ADs that might have passed
            # Actually, the balance applies to the whole MD. 
            # It's simpler to calculate the full MD and then truncate/shift if needed, 
            # but usually, we just show the start dates.
            
            a_end = m_start + timedelta(days=a_duration_days)
            
            # Paryantardashas
            paryantardashas = []
            p_start = m_start
            for k in range(9):
                p_idx = (a_idx + k) % 9
                p_name = PLANET_LORDS[p_idx]
                p_years = DASHA_YEARS[p_name]
                # Paryantardasha period = (AD_years * P_years) / 120
                # AD_years = (M_years * A_years) / 120
                p_duration_days = ((m_years * a_years / 120) * p_years / 120) * 365.25
                p_end = p_start + timedelta(days=p_duration_days)
                
                paryantardashas.append({
                    "planet": p_name,
                    "start": p_start.isoformat(),
                    "end": p_end.isoformat()
                })
                p_start = p_end

            antardashas.append({
                "planet": a_name,
                "start": m_start.isoformat(),
                "end": a_end.isoformat(),
                "paryantardashas": paryantardashas
            })
            m_start = a_end
            
        # If it's the first MD, we should filter out ADs that ended before birth
        if i == 0:
            # Shift all ADs and PDs back to align with the birth 'balance'
            # The total duration of MD was balance_years
            # The full duration is DASHA_YEARS[l_name]
            # Time passed before birth = (DASHA_YEARS[l_name] - balance_years)
            passed_days = (DASHA_YEARS[l_name] - balance_years) * 365.25
            
            md_full_start = dob - timedelta(days=passed_days)
            # Re-calculate ADs for the first MD specifically to get correct start dates
            m_start = md_full_start
            antardashas = []
            for j in range(9):
                a_idx = (l_idx + j) % 9
                a_name = PLANET_LORDS[a_idx]
                a_years = DASHA_YEARS[a_name]
                a_duration_days = (m_years * a_years / 120) * 365.25
                a_end = m_start + timedelta(days=a_duration_days)
                
                # Only include ADs that end after birth
                if a_end > dob:
                    # Filter PDs as well
                    p_start = m_start
                    paryantardashas = []
                    for k in range(9):
                        p_idx = (a_idx + k) % 9
                        p_name = PLANET_LORDS[p_idx]
                        p_years = DASHA_YEARS[p_name]
                        p_duration_days = ((m_years * a_years / 120) * p_years / 120) * 365.25
                        p_end = p_start + timedelta(days=p_duration_days)
                        
                        if p_end > dob:
                            paryantardashas.append({
                                "planet": p_name,
                                "start": max(p_start, dob).isoformat(),
                                "end": p_end.isoformat()
                            })
                        p_start = p_end

                    antardashas.append({
                        "planet": a_name,
                        "start": max(m_start, dob).isoformat(),
                        "end": a_end.isoformat(),
                        "paryantardashas": paryantardashas
                    })
                m_start = a_end
            current_end = m_start # This matches the full MD end

        dashas.append({
            "planet": l_name,
            "start": current_start.isoformat(),
            "end": current_end.isoformat(),
                "antardashas": antardashas
        })
        current_start = current_end
        
    return dashas

SIGN_LORDS = [
    "Mars",   # Aries
    "Venus",  # Taurus
    "Mercury",# Gemini
    "Moon",   # Cancer
    "Sun",    # Leo
    "Mercury",# Virgo
    "Venus",  # Libra
    "Mars",   # Scorpio
    "Jupiter",# Sagittarius
    "Saturn", # Capricorn
    "Saturn", # Aquarius
    "Jupiter" # Pisces
]

def get_sign_lord(longitude: float) -> str:
    sign_index = int((longitude % 360) / 30)
    return SIGN_LORDS[sign_index]

def get_analysis(longitude: float) -> Dict[str, str]:
    nak_info = get_nakshatra_info(longitude)
    return {
        "sign_lord": get_sign_lord(longitude),
        "nak_lord": nak_info["nak_lord"],
        "sub_lord": nak_info["sub_lord"],
        "sub_sub_lord": nak_info["sub_sub_lord"]
    }
