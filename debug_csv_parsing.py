
import pandas as pd
import re

FILE_PATH = r"C:\Users\DELL\Desktop\Agente kent-bell\alumnos activos enero 29012026.csv"

def parse_line(line):
    # Regex to find email
    email_match = re.search(r'[\w\.-]+@[\w\.-]+', line)
    email = email_match.group(0) if email_match else None
    
    # Name is usually at the start, but might be fused with email
    # Heuristic: Split by email, take left part
    name = "Unknown"
    if email:
        parts = line.split(email)
        name_part = parts[0]
        # Clean up commas and quotes
        name = name_part.replace('"', '').replace(',', ' ').strip()
        # Remove trailing weird chars if any
        
    return name, email

def main():
    print("--- RAW LINES (First 5) ---")
    with open(FILE_PATH, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        for i, line in enumerate(lines[:5]):
            print(f"{i}: {line.strip()}")
            n, e = parse_line(line)
            print(f"   -> Extracted: Name='{n}', Email='{e}'")

if __name__ == "__main__":
    main()
