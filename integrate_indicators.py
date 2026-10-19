import json

with open("dashboard_data.json") as f:
    dashboard_data = json.load(f)

with open("hospital_indicators.json") as f:
    hosp = json.load(f)

# Embed into dashboard_data.json
dashboard_data["hospitalIndicators"] = hosp

with open("dashboard_data.json", "w", encoding="utf-8") as f:
    json.dump(dashboard_data, f, ensure_ascii=False, indent=2)

print("Embedded hospitalIndicators into dashboard_data.json successfully!")
