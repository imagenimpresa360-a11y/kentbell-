
from bs4 import BeautifulSoup
import os

KEYWORDS = ["ingresar", "entrar", "login", "sign", "acceder", "iniciar"]

def main():
    path = os.path.join("downloads", "boxmagic_debug", "dashboard_v2.html")
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return

    with open(path, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    
    print("--- INPUTS ---")
    inputs = soup.find_all("input")
    for i, inp in enumerate(inputs):
        print(f"Input {i}: {inp.attrs}")

    print("\n--- BUTTONS ---")
    buttons = soup.find_all("button")
    for i, btn in enumerate(buttons):
        text = btn.get_text(strip=True)
        print(f"Button {i}: text='{text}', attrs={btn.attrs}")

    print("\n--- LINKS (A tags) that might be buttons ---")
    links = soup.find_all("a")
    for i, a in enumerate(links):
        text = a.get_text(strip=True).lower()
        if any(k in text for k in KEYWORDS):
            print(f"Link {i}: text='{text}', attrs={a.attrs}")

    print("\n--- DIVs acting as buttons? ---")
    # Sometimes buttons are divs
    divs = soup.find_all("div", role="button")
    for i, d in enumerate(divs):
        text = d.get_text(strip=True)
        print(f"DivButton {i}: text='{text}', attrs={d.attrs}")

if __name__ == "__main__":
    main()
