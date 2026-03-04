
import pandas as pd
import io

def test_parse():
    path = 'downloads/virtualpos/VirtualPos-transacciones-1769252778.csv'
    with open(path, 'r', encoding='utf-8-sig', errors='ignore') as f:
        lines = f.readlines()
    
    # Strip potential leading/trailing quotes and newlines
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if line.startswith('"') and line.endswith('"'):
            line = line[1:-1]
        cleaned_lines.append(line.replace('""', '"')) # Handle double-quotes inside
    
    csv_data = "\n".join(cleaned_lines)
    df = pd.read_csv(io.StringIO(csv_data), sep=",", quotechar='"', engine="python")
    print("Columns:", df.columns.tolist())
    print("Rows:", len(df))
    if 'fecha' in df.columns:
        df['fecha_dt'] = pd.to_datetime(df['fecha'], errors='coerce')
        jan_2026 = df[df['fecha_dt'].dt.strftime('%Y-%m') == '2026-01']
        print(f"January 2026 records: {len(jan_2026)}")
    else:
        # Check if column names are messy
        print("Mangled columns suspected:", df.iloc[0].to_dict())

if __name__ == "__main__":
    test_parse()
