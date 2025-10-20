#!/usr/bin/env python3
"""
Upload a PDF to WhatsApp Cloud API, then broadcast it as a document message
to numbers listed in a CSV WITHOUT HEADERS (first column is the number).

Priority order for config:
CLI args  >  .env file (via --env or ./.env)  >  real environment

Usage (typical):
  python send_whatsapp_upload_and_broadcast.py \
    --env ./.env

Optional CLI overrides:
  --csv=path/to/numbers.csv
  --pdf=path/to/file.pdf
  --caption="Message caption here"
  --filename=Offer.pdf
  --rate=0.75
  --template=name:lang
  --dry-run

Required values (from .env or env or CLI):
  WA_PHONE_NUMBER_ID   (digits)
  WA_ACCESS_TOKEN      (permanent token)
  CSV_PATH             (path to CSV without headers)
  PDF_PATH             (path to PDF)
  CAPTION              (caption text, allowed empty but recommended)

Optional:
  WA_GRAPH_VERSION     (default: v20.0)
  FILENAME             (defaults to PDF file name)
  RATE                 (default: 0.5 seconds between sends)
  TEMPLATE             (format: name:lang, e.g., my_template:en_US)
  DRY_RUN              (true/false; default false)

CSV format (no headers):
+27821234567
27829876543
002782345678
"""

import os, sys, csv, time, re, json, mimetypes
import requests
from typing import List, Dict

# -----------------------
# Simple .env loader (no deps)
# -----------------------
def load_env_file(path: str) -> Dict[str, str]:
    vals = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                if "=" not in s:
                    continue
                k, v = s.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'").strip('"')
                vals[k] = v
    except FileNotFoundError:
        pass
    return vals

def apply_env(vals: Dict[str, str]):
    for k, v in vals.items():
        # don't clobber real env if already set
        if os.getenv(k) is None:
            os.environ[k] = v

# -----------------------
# Helpers
# -----------------------
def fail(msg, code=1):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)

def sanitize_phone(raw: str) -> str:
    # WhatsApp Cloud expects digits only in international format
    return re.sub(r"\D", "", raw or "")

def read_numbers_from_csv(path: str) -> List[str]:
    nums = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            raw = row[0].strip()
            digits = sanitize_phone(raw)
            if len(digits) < 8:
                print(f"SKIP invalid: {raw}", file=sys.stderr)
                continue
            nums.append(digits)
    return nums

def upload_media(phone_number_id: str, access_token: str, file_path: str, mime_type: str, graph_ver: str) -> str:
    url = f"https://graph.facebook.com/{graph_ver}/{phone_number_id}/media"
    headers = {"Authorization": f"Bearer {access_token}"}
    with open(file_path, "rb") as fh:
        files = {
            "file": (os.path.basename(file_path), fh, mime_type),
            "type": (None, mime_type),
        }
        resp = requests.post(url, headers=headers, files=files, timeout=60)
    if resp.status_code >= 300:
        raise RuntimeError(f"Upload failed: {resp.status_code} {resp.text}")
    data = resp.json()
    media_id = data.get("id")
    if not media_id:
        raise RuntimeError(f"Upload response missing media id: {data}")
    return media_id

def post_json_messages(phone_number_id: str, access_token: str, payload: dict, graph_ver: str) -> dict:
    url = f"https://graph.facebook.com/{graph_ver}/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
    if resp.status_code >= 300:
        raise RuntimeError(f"Send failed: {resp.status_code} {resp.text}")
    return resp.json()

def send_template(phone_number_id: str, access_token: str, to_num: str, template_name: str, lang: str, graph_ver: str) -> str:
    payload = {
        "messaging_product": "whatsapp",
        "to": to_num,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": lang}
        }
    }
    data = post_json_messages(phone_number_id, access_token, payload, graph_ver)
    return (data.get("messages") or [{}])[0].get("id", "?")

def send_document_by_id(phone_number_id: str, access_token: str, to_num: str, media_id: str, filename: str, caption: str, graph_ver: str) -> str:
    payload = {
        "messaging_product": "whatsapp",
        "to": to_num,
        "type": "document",
        "document": {
            "id": media_id,
            "filename": filename,
            "caption": caption
        }
    }
    data = post_json_messages(phone_number_id, access_token, payload, graph_ver)
    return (data.get("messages") or [{}])[0].get("id", "?")

def get_cli_flag(name: str, default=None):
    # supports --key=value or --key (boolean True)
    for a in sys.argv[1:]:
        if a == name:
            return True
        if a.startswith(name + "="):
            return a.split("=", 1)[1]
    return default

def main():
    # Load .env (explicit or ./ .env)
    env_path = get_cli_flag("--env", ".env")
    apply_env(load_env_file(env_path))

    # CLI overrides
    if get_cli_flag("--csv") is not None:
        os.environ["CSV_PATH"] = get_cli_flag("--csv")
    if get_cli_flag("--pdf") is not None:
        os.environ["PDF_PATH"] = get_cli_flag("--pdf")
    if get_cli_flag("--caption") is not None:
        os.environ["CAPTION"] = get_cli_flag("--caption")
    if get_cli_flag("--filename") is not None:
        os.environ["FILENAME"] = get_cli_flag("--filename")
    if get_cli_flag("--rate") is not None:
        os.environ["RATE"] = get_cli_flag("--rate")
    if get_cli_flag("--template") is not None:
        os.environ["TEMPLATE"] = get_cli_flag("--template")
    if get_cli_flag("--dry-run", False):
        os.environ["DRY_RUN"] = "true"

    # Gather config
    phone_number_id = os.getenv("WA_PHONE_NUMBER_ID")
    access_token    = os.getenv("WA_ACCESS_TOKEN")
    graph_ver       = os.getenv("WA_GRAPH_VERSION", "v20.0")

    csv_path = os.getenv("CSV_PATH")
    pdf_path = os.getenv("PDF_PATH")
    caption  = os.getenv("CAPTION", "")

    filename = os.getenv("FILENAME")
    rate_str = os.getenv("RATE", "0.5")
    template = os.getenv("TEMPLATE", "")
    dry_run  = os.getenv("DRY_RUN", "false").lower() in ("1", "true", "yes")

    # Validate required
    if not phone_number_id or not access_token:
        fail("WA_PHONE_NUMBER_ID and WA_ACCESS_TOKEN are required (set in .env or environment).")
    if not csv_path or not pdf_path:
        fail("CSV_PATH and PDF_PATH are required (set in .env or via CLI).")

    # Defaults/normalization
    try:
        rate = float(rate_str)
    except ValueError:
        fail(f"RATE must be a float, got: {rate_str}")

    if not os.path.isfile(pdf_path):
        fail(f"PDF not found: {pdf_path}")
    if not os.path.isfile(csv_path):
        fail(f"CSV not found: {csv_path}")

    if not filename:
        filename = os.path.basename(pdf_path)

    mime_type, _ = mimetypes.guess_type(pdf_path)
    if not mime_type:
        mime_type = "application/pdf"
    if mime_type != "application/pdf":
        print(f"WARNING: Detected MIME '{mime_type}', forcing application/pdf.", file=sys.stderr)
        mime_type = "application/pdf"

    # Parse template
    tpl_name = tpl_lang = None
    if template:
        try:
            tpl_name, tpl_lang = template.split(":", 1)
        except Exception:
            fail("TEMPLATE must be 'name:lang' (e.g., hello_world:en_US)")

    # Read numbers
    numbers = read_numbers_from_csv(csv_path)
    if not numbers:
        fail("No valid numbers found in CSV (first column, no headers).")

    # 1) Upload
    if dry_run:
        print(f"[DRY-RUN] Would upload '{pdf_path}' as '{filename}' (MIME={mime_type}) "
              f"to WA phone_number_id={phone_number_id}, graph={graph_ver}")
        media_id = "DRY_RUN_MEDIA_ID"
    else:
        print(f"Uploading '{pdf_path}' ...")
        media_id = upload_media(phone_number_id, access_token, pdf_path, mime_type, graph_ver)
        print(f"Uploaded. media_id={media_id}")

    # 2) Send to each number
    for n in numbers:
        try:
            if dry_run:
                act = "TEMPLATE+DOC" if tpl_name else "DOC"
                print(f"[DRY-RUN] {act} -> {n}: filename={filename} caption='{caption}' media_id={media_id}")
            else:
                if tpl_name:
                    tid = send_template(phone_number_id, access_token, n, tpl_name, tpl_lang, graph_ver)
                    print(f"Template sent to {n}: id={tid}")
                mid = send_document_by_id(phone_number_id, access_token, n, media_id, filename, caption, graph_ver)
                print(f"Document sent to {n}: id={mid}")
        except Exception as e:
            print(f"FAILED for {n}: {e}", file=sys.stderr)
        time.sleep(rate)

if __name__ == "__main__":
    main()
