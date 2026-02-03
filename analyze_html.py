
from bs4 import BeautifulSoup

file_path = 'debug_login_page.html'

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    soup = BeautifulSoup(content, 'html.parser')
    
    print("--- BUTTONS ---")
    buttons = soup.find_all('button')
    for btn in buttons:
        print(f"Button: {btn}")
        print(f"  Parent: {btn.parent.name} class={btn.parent.get('class')}")

    print("\n--- INPUTS ---")
    inputs = soup.find_all('input')
    for inp in inputs:
        print(f"Input: {inp.get('name')} | Type: {inp.get('type')} | ID: {inp.get('id')} | Class: {inp.get('class')}")

    print("\n--- DIVS with 'Ingresar' ---")
    divs = soup.find_all(lambda tag: tag.name == 'div' and 'Ingresar' in tag.text)
    for d in divs:
        # Only print leaf nodes or close to leaf
        if len(d.find_all()) < 2:
            print(f"Div: {d} | Class: {d.get('class')}")

except Exception as e:
    print(f"Error: {e}")
