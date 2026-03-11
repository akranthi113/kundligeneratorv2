import urllib.request
import json

payload = {
    "date": "1995-08-12",
    "time": "14:35",
    "tz_offset": "+05:30",
    "lat": 19.0760,
    "lon": 72.8777,
    "node": "mean",
    "house_system": "P"
}

try:
    req = urllib.request.Request(
        "http://localhost:8000/api/kundli",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as response:
        if response.status == 200:
            data = json.loads(response.read().decode())
            print("Success!")
            print("Ruling Planets:", json.dumps(data.get("ruling_planets"), indent=2))
            print("First Planet Analysis:", json.dumps(data.get("planets")[0].get("analysis"), indent=2))
            print("First House Analysis:", json.dumps(data.get("houses")[0].get("analysis"), indent=2))
            print("Number of Dashas:", len(data.get("dashas", [])))
        else:
            print(f"Error: {response.status}")
except Exception as e:
    print(f"Failed: {e}")
