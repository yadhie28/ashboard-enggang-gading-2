import json
import re

with open("dashboard_data.json") as f:
    data = json.load(f)

recent_days = data["recentDays"]
history = data["history"]
print("Total history days:", len(history))

# Let us inspect notes across patients for mentions of discharge / death / etc.
discharge_keywords = ["BLPL", "KRS", "PULANG", "RAWAT JALAN", "RAJAL", "APS", "ACC PULANG"]
death_keywords = ["MENINGGAL", "EXIT", "MENINGGAL DUNIA", "WAFAT", "MENINGGAL DI RUANGAN", "DEATH", "DOA"]

death_cases = []
discharge_cases = []

for dt, day in recent_days.items():
    patients = day["eg2a"] + day["eg2b"]
    for p in patients:
        notes = " ".join([p["notes"].get("pagi",""), p["notes"].get("sore",""), p["notes"].get("malam","")]).upper()
        name = p["name"]
        bed = f"{p['room']}-{p['bed']}"
        
        # Check death
        if any(k in notes for k in death_keywords) and not p["isEmpty"]:
            death_cases.append({"date": dt, "bed": bed, "name": name, "notes": notes[:120]})
            
        # Check discharge
        if any(k in notes for k in discharge_keywords) and not p["isEmpty"]:
            discharge_cases.append({"date": dt, "bed": bed, "name": name})

print(f"Sample recent 45 days:")
print(f"Discharge mentions: {len(discharge_cases)}")
print(f"Death mentions: {len(death_cases)}")
if death_cases:
    print("Sample death cases:", death_cases[:5])

