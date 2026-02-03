from bs4 import BeautifulSoup

def main():
    try:
        with open('debug_reports_v2.html', 'r', encoding='utf-8') as f:
            html = f.read()
    except FileNotFoundError:
        print("File debug_reports_v2.html not found.")
        return
    
    soup = BeautifulSoup(html, 'html.parser')
    
    print("--- Searching for Export Buttons/Links ---")
    keywords = ["CSV", "Excel", "Exportar", "Descargar"]
    
    elements = soup.find_all(['button', 'a', 'span', 'input'])
    
    for el in elements:
        text = el.get_text(strip=True)
        if any(kw in text for kw in keywords) or any(kw in str(el.get('value')) for kw in keywords):
            print(f"[{el.name}] Text: '{text[:50]}' | Class: {el.get('class')} | ID: {el.get('id')} | Type: {el.get('type')}")

if __name__ == "__main__":
    main()
