
from bs4 import BeautifulSoup
import os

def main():
    path = "dashboard_cookie_access.html"
    if not os.path.exists(path):
        print("File not found")
        return

    with open(path, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    
    print("--- SEARCH: Campanario ---")
    # Search whole text
    if "Campanario" in html:
        print("Found 'Campanario' in raw HTML!")
        # Find containing elements
        found = soup.find_all(string=lambda t: t and "Campanario" in t)
        for t in found:
            parent = t.parent
            print(f"   Found in tag <{parent.name} class='{parent.get('class')}'>: '{t.strip()}'")
    else:
        print("Not found in HTML.")

    print("\n--- LINKS (Reportes/Alumnos) ---")
    for a in soup.find_all("a"):
        text = a.get_text(strip=True)
        href = a.get("href")
        if text and any(x in text for x in ["Reporte", "Informe", "Alumnos", "Usuarios", "Sedes"]):
            print(f"   Link: '{text}' -> {href}")

    print("\n--- BUTTONS (Profile Switch?) ---")
    for btn in soup.find_all("button"):
        text = btn.get_text(strip=True)
        # Check text or attributes for clue
        attrs = str(btn.attrs)
        if any(x in text for x in ["Sede", "Cambiar", "Profile", "Campanario"]) or "campanario" in attrs.lower():
            print(f"   Button: '{text}' Attrs: {btn.attrs}")

if __name__ == "__main__":
    main()
