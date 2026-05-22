
import re

with open("reports_index.html", "r", encoding="utf-8") as f:
    html = f.read()

# Grab the "Ver Sección" links
links = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>.*?Ver\s*Sección.*?</a>', html, re.IGNORECASE | re.DOTALL)
print(f"Links found: {len(links)}")
for l in links:
    print(l)

