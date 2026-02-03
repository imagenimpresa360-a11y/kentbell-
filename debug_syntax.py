import tokenize

try:
    with open('app.py', 'rb') as f:
        for token in tokenize.tokenize(f.readline):
            pass
    print("No tokenize errors found.")
except tokenize.TokenError as e:
    print(f"Token error found: {e}")
except Exception as e:
    print(f"Other error: {e}")
