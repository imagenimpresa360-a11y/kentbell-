
import pandas as pd
import os

DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads", "virtualpos")
csv_path = [os.path.join(DOWNLOAD_DIR, f) for f in os.listdir(DOWNLOAD_DIR) if f.endswith('.csv')]
if csv_path:
    csv_path = max(csv_path, key=os.path.getctime)
    
    print("--- Attempt 1: Default ---")
    df = pd.read_csv(csv_path)
    print(df.head(2))
    print(df.columns)
    
    print("\n--- Attempt 2: Quote None ---")
    try:
        df2 = pd.read_csv(csv_path, quoting=3) # QUOTE_NONE
        print(df2.head(2))
    except Exception as e:
        print(e)

    print("\n--- Attempt 3: Separator ; ---")
    try:
        df3 = pd.read_csv(csv_path, sep=';')
        print(df3.head(2))
    except:
        pass
