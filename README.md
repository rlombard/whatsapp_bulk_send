# WhatsApp PDF Broadcast Script

This repository contains a Python script that uploads a PDF document to the **Meta WhatsApp Cloud API**, and then broadcasts it to all phone numbers listed in a CSV file (without headers). It also supports optional message templates, rate limiting, and `.env` configuration for easy setup.

---

## Features

* Uploads a PDF file to WhatsApp Cloud API, retrieves a `media_id`, and sends it as a **native document attachment** (not a public link)
* Reads recipient phone numbers from a **CSV file with no headers**
* **Comprehensive logging system** with multiple levels and optional file output
* **Detailed error handling** with specific error messages and recovery guidance
* **Failed numbers tracking** - automatically saves failed phone numbers to CSV with error details
* **Extensive configuration validation** to catch issues before sending
* **Progress tracking** with success/failure statistics and timing information
* Optional `.env` configuration file for persistent settings
* Supports:

  * `--dry-run` for testing without sending
  * `--rate` for throttling message sends
  * `--template=name:lang` to send an approved message template first
  * `--log-level` for controlling logging verbosity (DEBUG, INFO, WARNING, ERROR)
  * `--log-file` for persistent logging to files
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
| `--dry-run`            | Don't upload/send (log actions only) | False        |
| `--log-level`          | Logging level (DEBUG/INFO/WARNING/ERROR) | INFO    |
| `--log-file`           | Path to log file for persistent logging | None      |
| `--failed-csv`         | Path to CSV file for failed numbers | failed.csv   |

---

## Important Notes

* **24-hour rule:** Free-form messages (with captions) can only be sent within 24 hours of a user’s last message. Outside that window, use an approved **template** first.
* **Opt-in required:** Only message users who have consented to WhatsApp communications from you.
* **Security:** Keep your `WA_ACCESS_TOKEN` secret. Add `.env` to `.gitignore`.
* **CSV validation:** Numbers must be international format; script auto-strips non-digits.

---

## Logging and Monitoring

### Logging Levels

The script provides comprehensive logging with four levels:

* **DEBUG**: Detailed information for troubleshooting (API requests, phone number processing, etc.)
* **INFO**: General operational information (default level)
* **WARNING**: Warning messages and recoverable errors
* **ERROR**: Critical errors that prevent operation

### Console Output

By default, logs are displayed in the console with timestamps:

```bash
python send_whatsapp_upload_and_broadcast.py --env ./.env --log-level INFO
```

### File Logging

Enable persistent logging to files for audit trails and debugging:

```bash
python send_whatsapp_upload_and_broadcast.py --env ./.env --log-file ./logs/run.log
```

Or set in `.env`:
```bash
LOG_FILE=./logs/whatsapp_bulk_sender.log
```

### Debug Mode

For detailed troubleshooting, use DEBUG level:

```bash
python send_whatsapp_upload_and_broadcast.py --env ./.env --log-level DEBUG
```

This shows:
- Environment variable loading details
- Phone number validation process  
- API request/response details (with token masking for security)
- File processing information
- Rate limiting delays

### Failed Numbers Tracking

When messages fail to send, the script automatically creates a `failed.csv` file containing:

- **phone_number**: The phone number that failed
- **error_message**: Detailed error description  
- **timestamp**: When the failure occurred (ISO format)

```csv
phone_number,error_message,timestamp
27821234567,"Send failed: 403 Forbidden",2025-10-20T10:30:15.123456
27829876543,"Network timeout after 30 seconds",2025-10-20T10:31:22.789012
```

**Customize the failed CSV path:**

```bash
python send_whatsapp_upload_and_broadcast.py --env ./.env --failed-csv ./errors/failed_today.csv
```

Or in `.env`:
```bash
FAILED_CSV_PATH=./failed_numbers.csv
```

**Uses for failed numbers CSV:**
- Retry failed numbers later
- Analyze failure patterns
- Update contact database
- Generate reports for stakeholders

---

## Example Run

```bash
python send_whatsapp_upload_and_broadcast.py --env ./.env
```

**Output:**

```
2025-10-20 10:30:15 - whatsapp_bulk_sender - INFO - ============================================================
2025-10-20 10:30:15 - whatsapp_bulk_sender - INFO - WhatsApp Bulk Document Sender - Starting
2025-10-20 10:30:15 - whatsapp_bulk_sender - INFO - Version: 2.0.0
2025-10-20 10:30:15 - whatsapp_bulk_sender - INFO - Start time: 2025-10-20 10:30:15.123456
2025-10-20 10:30:15 - whatsapp_bulk_sender - INFO - ============================================================
2025-10-20 10:30:15 - whatsapp_bulk_sender - INFO - Loading environment from: .env
2025-10-20 10:30:15 - whatsapp_bulk_sender - INFO - Successfully loaded 8 environment variables from .env
2025-10-20 10:30:15 - whatsapp_bulk_sender - INFO - Configuration loaded:
2025-10-20 10:30:15 - whatsapp_bulk_sender - INFO - Configuration validation passed
2025-10-20 10:30:15 - whatsapp_bulk_sender - INFO - Loading recipient phone numbers...
2025-10-20 10:30:15 - whatsapp_bulk_sender - INFO - Successfully loaded 25 valid phone numbers from CSV
2025-10-20 10:30:15 - whatsapp_bulk_sender - INFO - Loaded 25 valid recipient numbers
2025-10-20 10:30:15 - whatsapp_bulk_sender - INFO - ========================================
2025-10-20 10:30:15 - whatsapp_bulk_sender - INFO - PHASE 1: Media Upload
2025-10-20 10:30:15 - whatsapp_bulk_sender - INFO - ========================================
2025-10-20 10:30:15 - whatsapp_bulk_sender - INFO - Uploading media file: ./Offer-Oct.pdf (2458361 bytes, application/pdf)
2025-10-20 10:30:17 - whatsapp_bulk_sender - INFO - Successfully uploaded media, ID: 908345987654321
2025-10-20 10:30:17 - whatsapp_bulk_sender - INFO - ========================================
2025-10-20 10:30:17 - whatsapp_bulk_sender - INFO - PHASE 2: Message Broadcasting
2025-10-20 10:30:17 - whatsapp_bulk_sender - INFO - ========================================
2025-10-20 10:30:17 - whatsapp_bulk_sender - INFO - Processing recipient 1/25: 27821234567
2025-10-20 10:30:17 - whatsapp_bulk_sender - INFO - Document sent successfully to 27821234567, message ID: wamid.HBgM...
2025-10-20 10:30:17 - whatsapp_bulk_sender - INFO - ✓ Success for 27821234567
...
2025-10-20 10:30:45 - whatsapp_bulk_sender - INFO - ============================================================
2025-10-20 10:30:45 - whatsapp_bulk_sender - INFO - OPERATION COMPLETE
2025-10-20 10:30:45 - whatsapp_bulk_sender - INFO - ============================================================
2025-10-20 10:30:45 - whatsapp_bulk_sender - INFO - Duration: 0:00:30.123456
2025-10-20 10:30:45 - whatsapp_bulk_sender - INFO - Total recipients: 25
2025-10-20 10:30:45 - whatsapp_bulk_sender - INFO - Successful sends: 24
2025-10-20 10:30:45 - whatsapp_bulk_sender - INFO - Failed sends: 1
2025-10-20 10:30:45 - whatsapp_bulk_sender - INFO - Success rate: 96.0%
2025-10-20 10:30:45 - whatsapp_bulk_sender - WARNING - 1 messages failed to send. Check the logs above for details.
2025-10-20 10:30:45 - whatsapp_bulk_sender - INFO - Writing 1 failed numbers to: failed.csv
2025-10-20 10:30:45 - whatsapp_bulk_sender - INFO - Successfully wrote failed numbers to: failed.csv
2025-10-20 10:30:45 - whatsapp_bulk_sender - INFO - Failed phone numbers written to: failed.csv
```

---

## Troubleshooting

### Common Issues

* **403 Permission Error:** Check your access token and that your app is in Live mode.
* **Media upload failure:** Ensure the PDF file exists, is readable, and < 16MB.
* **Message not delivered:** Verify the number is a registered WhatsApp account and the user opted in.
* **Configuration errors:** Use `--log-level DEBUG` to see detailed configuration loading.
* **CSV parsing issues:** Enable DEBUG logging to see which numbers are being skipped and why.
* **Rate limiting:** Increase the `RATE` value in your configuration to slow down sending.

### Debug Mode

For detailed troubleshooting information:

```bash
python send_whatsapp_upload_and_broadcast.py --env ./.env --log-level DEBUG --log-file debug.log
```

This will:
- Show all environment variables being loaded (with sensitive data masked)
- Display detailed phone number validation
- Log all API requests and responses
- Show file processing details
- Track rate limiting delays

### Failed Numbers Recovery

When messages fail, check the `failed.csv` file for detailed error information:

```bash
# Review failed numbers
cat failed.csv

# Count failures by error type
cut -d',' -f2 failed.csv | sort | uniq -c

# Extract just the phone numbers for retry
tail -n +2 failed.csv | cut -d',' -f1 > retry_numbers.csv
```

### Error Codes

The script uses specific exit codes:
- **0**: Success (all messages sent)
- **1**: Partial success (some messages failed) or configuration errors
- **130**: Interrupted by user (Ctrl+C)

### Log File Analysis

When using `--log-file`, you can analyze the logs:

```bash
# Show only errors
grep "ERROR" whatsapp_bulk_sender.log

# Show success/failure summary
grep -E "(✓ Success|✗ Failed)" whatsapp_bulk_sender.log

# Check configuration issues  
grep "Configuration" whatsapp_bulk_sender.log
```

---

## License

This script is provided under the MIT License.

---

**Author:** RM Lombard  
**Version:** 2.0.0  
**Date:** 2025-10-20

### What's New in v2.0.0

- **Comprehensive Logging**: Multi-level logging system with DEBUG, INFO, WARNING, ERROR levels
- **File Logging**: Optional persistent logging to files for audit trails
- **Enhanced Error Handling**: Detailed error messages with specific guidance
- **Configuration Validation**: Extensive validation with clear error reporting
- **Progress Tracking**: Real-time progress indicators and final statistics
- **Improved Documentation**: Complete function documentation with type hints
- **Security Enhancements**: Sensitive data masking in logs
- **Better CLI Support**: Additional command-line options for logging control
