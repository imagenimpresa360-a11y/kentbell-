
import re

with open("reports_pagos_real.html", "r", encoding="utf-8") as f:
    html = f.read()

# surrounding of filtrar
btn = re.search(r'(.{0,150}filtrar.{0,150})', html, re.IGNORECASE)
if btn:
    print("Filtrar context:", btn.group(1))
    
# check inputs
inputs = re.findall(r'<input[^>]+>', html, re.IGNORECASE)
for i in inputs:
    print("Input:", i)
