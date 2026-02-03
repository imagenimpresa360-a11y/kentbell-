
import os
import imaplib
from dotenv import load_dotenv
import sys

# Force unbuffered stdout
sys.stdout.reconfigure(line_buffering=True)

print("Starting test...", flush=True)
load_dotenv()

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASS = os.getenv("GMAIL_PASS").replace(" ", "") if os.getenv("GMAIL_PASS") else None

print(f"User: {GMAIL_USER}", flush=True)
print(f"Pass leng: {len(GMAIL_PASS) if GMAIL_PASS else 0}", flush=True)

try:
    print("Connecting...", flush=True)
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    print("Logging in...", flush=True)
    mail.login(GMAIL_USER, GMAIL_PASS)
    print("Login success!", flush=True)
    
    print("Listing folders...", flush=True)
    status, folders = mail.list()
    print(f"Folders status: {status}", flush=True)
    for f in folders:
        print(f.decode(), flush=True)
    
    mail.logout()
except Exception as e:
    print(f"Error: {e}", flush=True)

print("End test.", flush=True)
