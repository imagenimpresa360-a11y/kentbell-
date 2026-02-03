
import os
import imaplib
import email
from email.header import decode_header
import datetime
from dotenv import load_dotenv
import sys

# Force unbuffered IO
sys.stdout.reconfigure(line_buffering=True)

load_dotenv()

# Configuración desde .env
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASS = os.getenv("GMAIL_PASS").replace(" ", "") if os.getenv("GMAIL_PASS") else None
DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads", "virtualpos")

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def get_imap_date():
    today = datetime.date.today()
    # 2 days lookback
    target_date = today - datetime.timedelta(days=2) 
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return f"{target_date.day}-{months[target_date.month-1]}-{target_date.year}"

def download_report():
    print("=" * 60)
    print("GMAIL DOWNLOADER v2")
    print("=" * 60)

    try:
        print(f"Connecting to {GMAIL_USER}...")
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_PASS)
        print("Login OK.")

        date_str = get_imap_date()
        criteria = f'SINCE "{date_str}"'

        print(f"Search criteria: {criteria}")

        # Folders to check: Todos covers everything (Inbox, Promotions, etc.)
        folders = ["INBOX", "[Gmail]/Todos"]
        
        found_files = []

        for folder in folders:
            print(f"\nChecking folder: {folder}")
            try:
                # Select folder
                res, _ = mail.select(f'"{folder}"' if " " in folder else folder)
                if res != "OK":
                    print(f"  Warning: Could not select {folder}")
                    continue
                
                # Search
                status, messages = mail.search(None, criteria)
                if status != "OK" or not messages[0]:
                    print("  No matching emails found.")
                    continue
                
                mail_ids = messages[0].split()
                print(f"  Found {len(mail_ids)} email(s). Processing...")

                for m_id in mail_ids:
                    res, msg_data = mail.fetch(m_id, "(RFC822)")
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            subj, enc = decode_header(msg["Subject"])[0]
                            if isinstance(subj, bytes):
                                subj = subj.decode(enc if enc else "utf-8")
                            
                            print(f"    Subject: {subj}")
                            with open(os.path.join(DOWNLOAD_DIR, "email_subjects.txt"), "a", encoding="utf-8") as log:
                                log.write(f"{subj}\n")
                            
                            has_attachment = False
                            # Check attachments
                            for part in msg.walk():
                                if part.get_content_maintype() == "multipart": continue
                                if part.get("Content-Disposition") is None: continue
                                
                                fname = part.get_filename()
                                if fname:
                                    f_dec, f_enc = decode_header(fname)[0]
                                    if isinstance(f_dec, bytes):
                                        f_dec = f_dec.decode(f_enc if f_enc else "utf-8")
                                    
                                    print(f"      Attachment: {f_dec}")
                                    
                                    # Save if it looks like a report
                                    if any(ext in f_dec.lower() for ext in ['.csv', '.xls', '.xlsx']):
                                        has_attachment = True
                                        print(f"      ★ ADJUNTO ENCONTRADO: {f_dec}")
                                        save_path = os.path.join(DOWNLOAD_DIR, f_dec)
                                        with open(save_path, "wb") as f:
                                            f.write(part.get_payload(decode=True))
                                        found_files.append(save_path)

                            if not has_attachment:
                                # Extract body to check for links
                                body = ""
                                if msg.is_multipart():
                                    for part in msg.walk():
                                        if part.get_content_type() == "text/plain":
                                            body = part.get_payload(decode=True).decode(errors='ignore')
                                            break
                                else:
                                    body = msg.get_payload(decode=True).decode(errors='ignore')
                                
                                # Print first 200 chars of body
                                print(f"      [No attachment] Body snippet: {body[:200]}...")
                                if "http" in body:
                                    print("      ⚠ Link found in body!")

            except Exception as e_folder:
                print(f"  Error processing folder {folder}: {e_folder}")

        mail.logout()
        
        if not found_files:
            print("\n❌ No report files found in recent emails.")
        else:
            print(f"\n✅ SUCCESS: Downloaded {len(found_files)} files.")

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    download_report()
