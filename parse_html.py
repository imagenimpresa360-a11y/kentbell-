
import re

with open("lioren_boletas_html.txt", "r", encoding="utf-8") as f:
    html = f.read()

# find all anchor tags and print their text and href
anchors = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.IGNORECASE | re.DOTALL)
for href, text in anchors:
    # clean tags from text
    text = re.sub(r'<[^>]+>', '', text).strip()
    if text:
        print(f"L: {text} -> {href}")

