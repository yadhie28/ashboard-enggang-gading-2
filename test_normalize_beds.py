import json

with open("dashboard_data.json") as f:
    d = json.load(f)

today = d["today"]
pts_a = today["eg2a"]
pts_b = today["eg2b"]

print("Original EG2A count:", len(pts_a))
for p in pts_a:
    print(f"  Bed {p['bed']}: {p['name']} ({p['status']})")

print("\nOriginal EG2B count:", len(pts_b))
for p in pts_b[:10]:
    print(f"  Bed {p['bed']}: {p['name']} ({p['status']})")

