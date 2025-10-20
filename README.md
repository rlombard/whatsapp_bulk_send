# WhatsApp PDF Broadcast Script

This repository contains a Python script that uploads a PDF document to the **Meta WhatsApp Cloud API**, and then broadcasts it to all phone numbers listed in a CSV file (without headers). It also supports optional message templates, rate limiting, and `.env` configuration for easy setup.

---

## Features

* Uploads a PDF file to WhatsApp Cloud API, retrieves a `media_id`, and sends it as a **native document attachment** (not a public link)
* Reads recipient phone numbers from a **CSV file with no headers**
* Optional `.env` configuration file for persistent settings
* Supports:

  * `--dry-run` for testing without sending
  * `--rate` for throttling message sends
  * `--template=name:lang` to send an approved message template first
  * CLI overrides for all `.env` values

---

## Prerequisites

1. A **WhatsApp Cloud API** account configured in [Meta for Developers](https://developers.facebook.com/)
2. A **Phone Number ID** and **Permanent Access Token**
3. Python 3.8+
4. The `requests` library (usually pre-installed; if not, install via `pip install requests`)
5. A publicly reachable **PDF file** or a local one to upload

---

## Python environment & dependencies

Set up an isolated Python environment and install dependencies:

### 1) Create & activate a virtual environment

**macOS/Linux (bash/zsh):**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell):**

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
```

> To exit later: `deactivate`

### 2) Install requirements

Create a `requirements.txt` (or use the one in this repo) and install:

`requirements.txt`

```
requests>=2.31.0
```

Install:

```bash
pip install -r requirements.txt
```

> If `pip` is missing, try `python -m pip install -r requirements.txt` (or `py -3 -m pip ...` on Windows).

---

## Folder Structure

```
.
├── send_whatsapp_upload_and_broadcast.py
├── .env.example
├── README.md
├── requirements.txt
└── numbers.csv
```

> The virtual environment folder (e.g., `.venv/`) is **not** shown above and should be excluded via `.gitignore`. Add lines like:

```
.venv/
.env
```

---

## Setup

1. **Create a `.env` file** in the same directory as the script:

```bash
cp .env.example .env
```

2. **Edit `.env`** with your own configuration:

```ini
# WhatsApp Cloud API
WA_PHONE_NUMBER_ID=123456789012345
WA_ACCESS_TOKEN=EAAB...your_permanent_token...
WA_GRAPH_VERSION=v20.0

# File paths
CSV_PATH=./numbers.csv
PDF_PATH=./Offer-Oct.pdf

# Message
CAPTION=Hi — here’s your PDF from Longbeard.

# Optional
FILENAME=Offer-Oct.pdf
RATE=0.75
# TEMPLATE=my_marketing_template:en_US
# DRY_RUN=true
```

3. **Prepare your CSV file** (`numbers.csv`):

Each line should contain a single phone number in international format (no headers):

```
+27821234567
27829876543
002782345678
```

---

## Usage

Run the script with:

```bash
python send_whatsapp_upload_and_broadcast.py --env ./.env
```

### CLI Overrides

CLI arguments override `.env` values. Examples:

```bash
python send_whatsapp_upload_and_broadcast.py --env ./.env --rate=0.3 --dry-run
```

You can also specify paths and message inline:

```bash
python send_whatsapp_upload_and_broadcast.py \
  --env ./.env \
  --csv=./numbers.csv \
  --pdf=./docs/Invoice.pdf \
  --caption="Here’s your October invoice." \
  --filename=Invoice-Oct.pdf
```

---

## Options Summary

| Option                 | Description                          | Default      |
| ---------------------- | ------------------------------------ | ------------ |
| `--env`                | Path to `.env` file                  | `./.env`     |
| `--csv`                | Path to CSV file (no headers)        | From `.env`  |
| `--pdf`                | Path to PDF file                     | From `.env`  |
| `--caption`            | Text caption for message             | From `.env`  |
| `--filename`           | Filename shown in WhatsApp           | PDF filename |
| `--rate`               | Delay between sends (seconds)        | `0.5`        |
| `--template=name:lang` | Approved template to send first      | None         |
| `--dry-run`            | Don’t upload/send (log actions only) | False        |

---

## Important Notes

* **24-hour rule:** Free-form messages (with captions) can only be sent within 24 hours of a user’s last message. Outside that window, use an approved **template** first.
* **Opt-in required:** Only message users who have consented to WhatsApp communications from you.
* **Security:** Keep your `WA_ACCESS_TOKEN` secret. Add `.env` to `.gitignore`.
* **CSV validation:** Numbers must be international format; script auto-strips non-digits.

---

## Example Run

```bash
python send_whatsapp_upload_and_broadcast.py --env ./.env
```

**Output:**

```
Uploading './Offer-Oct.pdf' ...
Uploaded. media_id=908345987654321
Document sent to 27821234567: id=wamid.HBgMNTUxMjM0NTY3ODk1FQIAEhggE....
Document sent to 27829876543: id=wamid.HBgMNTUxMjM0NTY3ODk1FQIAEhggE....
```

---

## Troubleshooting

* **403 Permission Error:** Check your access token and that your app is in Live mode.
* **Media upload failure:** Ensure the PDF file exists, is readable, and < 16MB.
* **Message not delivered:** Verify the number is a registered WhatsApp account and the user opted in.

---

## License

This script is provided under the MIT License.

---

**Author:** RM Lombard
**Version:** 1.0.0
**Date:** 2025-10-20
