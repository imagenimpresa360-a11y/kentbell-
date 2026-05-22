
import re

with open("reports_pagos.html", "r", encoding="utf-8") as f:
    html = f.read()

# Look for export buttons or links
exports = re.findall(r'<[^>]*export[^>]*>', html, re.IGNORECASE)
print(f"Elements with 'export': {len(exports)}")
for e in exports[:10]:
    print("- ", e)

excels = re.findall(r'<[^>]*excel[^>]*>', html, re.IGNORECASE)
print(f"Elements with 'excel': {len(excels)}")
for e in excels[:10]:
    print("- ", e)

# Look for down buttons
descargar = re.findall(r'<[^>]*descargar[^>]*>', html, re.IGNORECASE)
print(f"Elements with 'descargar': {len(descargar)}")
for d in descargar[:10]:
    print("- ", d)

# maybe we just need to scroll down and screenshot
