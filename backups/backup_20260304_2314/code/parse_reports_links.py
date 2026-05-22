
import re

with open("dashboard_source_full.html", "r", encoding="utf-8") as f:
    html = f.read()

reports_links = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>.*?Reportes.*?</a>', html, re.IGNORECASE | re.DOTALL)
for l in reports_links:
    print("Found Reportes link:", l)
