import zipfile
import time
from parse_sheets import parse_shared_strings, get_sheets_info
from test_sheet_parse import parse_worksheet

t0 = time.time()
with zipfile.ZipFile("EG2B.xlsx", "r") as z:
    ss = parse_shared_strings(z)
    sheets = get_sheets_info(z)
    print(f"Loaded strings in {time.time()-t0:.2f}s. Parsing 50 sheets...")
    t1 = time.time()
    for s in sheets[-50:]:
        rows = parse_worksheet(z, s["filename"], ss)
    print(f"Parsed 50 sheets in {time.time()-t1:.2f}s (avg {(time.time()-t1)/50:.4f}s per sheet)")
