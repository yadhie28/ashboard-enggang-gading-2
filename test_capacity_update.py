import json

def normalize_wing_beds(patients_raw, wing_name, target_capacity):
    occupied = [p for p in patients_raw if not p.get("isEmpty")]
    empty_raw = [p for p in patients_raw if p.get("isEmpty")]
    
    # Try mapping by bed number if possible
    bed_slots = {}
    overflow = []
    
    for p in occupied:
        try:
            b_int = int(re.sub(r"[^0-9]", "", str(p["bed"])))
        except:
            b_int = None
            
        if b_int and 1 <= b_int <= target_capacity and b_int not in bed_slots:
            bed_slots[b_int] = p
        else:
            overflow.append(p)
            
    # Also handle BAU / repair beds from raw
    for p in empty_raw:
        try:
            b_int = int(re.sub(r"[^0-9]", "", str(p["bed"])))
        except:
            b_int = None
        if b_int and 1 <= b_int <= target_capacity and b_int not in bed_slots:
            bed_slots[b_int] = p
            
    # Place overflow patients into available slots
    for slot in range(1, target_capacity + 1):
        if slot not in bed_slots and overflow:
            p = overflow.pop(0)
            p_copy = dict(p)
            p_copy["bed"] = str(slot)
            bed_slots[slot] = p_copy
            
    # Any remaining unassigned slots are marked as Bed Kosong
    result = []
    for slot in range(1, target_capacity + 1):
        if slot in bed_slots:
            result.append(bed_slots[slot])
        else:
            result.append({
                "bed": str(slot),
                "room": wing_name,
                "status": "Kosong",
                "isEmpty": True,
                "name": "Bed Kosong",
                "mrNo": "",
                "gender": "-",
                "age": "",
                "admissionDate": "-",
                "los": 0,
                "insurance": "-",
                "doctor": "-",
                "doctorPrimary": "-",
                "diagnosis": "-",
                "category": "-",
                "notes": {"pagi": "", "sore": "", "malam": ""},
                "tags": []
            })
    return result

import re
with open("dashboard_data.json") as f:
    d = json.load(f)

norm_a = normalize_wing_beds(d["today"]["eg2a"], "EG2A", 16)
norm_b = normalize_wing_beds(d["today"]["eg2b"], "EG2B", 40)

print(f"Normalized EG2A count: {len(norm_a)} (Occupied: {len([p for p in norm_a if not p['isEmpty']])}, Empty: {len([p for p in norm_a if p['isEmpty']])})")
print(f"Normalized EG2B count: {len(norm_b)} (Occupied: {len([p for p in norm_b if not p['isEmpty']])}, Empty: {len([p for p in norm_b if p['isEmpty']])})")
print("Total beds:", len(norm_a) + len(norm_b))
