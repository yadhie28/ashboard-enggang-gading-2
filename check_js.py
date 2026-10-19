with open("app.js") as f:
    text = f.read()
print("app.js length:", len(text), "characters, lines:", len(text.splitlines()))
# Look for potential bad tokens or syntax
import re
print("Functions defined:", len(re.findall(r"function\s+([A-Za-z0-9_]+)", text)))
for fn in re.findall(r"function\s+([A-Za-z0-9_]+)", text):
    print("  -", fn)
