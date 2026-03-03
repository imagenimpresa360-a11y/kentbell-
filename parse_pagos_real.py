
import re

with open("reports_pagos_real.html", "r", encoding="utf-8") as f:
    html = f.read()

# Let's find how to interact with the date picker
dates = re.findall(r'<input[^>]*date[^>]*>', html, re.IGNORECASE)
for d in dates:
    print(d)
    
prints = re.findall(r'<button[^>]*>.*?CSV.*?</button>|<a[^>]*>.*?CSV.*?</a>', html, re.IGNORECASE)
for p in prints:
    print(p)

exports = re.findall(r'<button[^>]*>.*?Exportar.*?</button>|<a[^>]*>.*?Exportar.*?</a>', html, re.IGNORECASE)
for e in exports:
    print(e)
    
