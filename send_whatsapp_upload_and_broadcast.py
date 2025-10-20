#!/usr/bin/env python3
"""
WhatsApp Bulk Document Sender

Upload a PDF to WhatsApp Cloud API, then broadcast it as a document message
to numbers listed in a CSV WITHOUT HEADERS (first column is the number).

This script provides comprehensive logging, error handling, and configuration
management for bulk WhatsApp messaging operations.

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
  --log-level=INFO
  --failed-csv=failed.csv

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
  LOG_LEVEL            (DEBUG, INFO, WARNING, ERROR; default INFO)
  LOG_FILE             (path to log file; optional)
  FAILED_CSV_PATH      (path for failed numbers CSV; default: failed.csv)

CSV format (no headers):
+27821234567
27829876543
002782345678

Author: RM Lombard
Version: 2.0.0
Date: 2025-10-20
License: MIT
"""

import os
import sys
import csv
import time
import re
import json
import mimetypes
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import requests

# -----------------------
# Logging Configuration
# -----------------------
def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """
    Configure comprehensive logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional path to log file for persistent logging
        
    Returns:
        Configured logger instance
        
    Raises:
        ValueError: If log_level is invalid
    """
    # Create logs directory if log_file is specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure logging format
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Get logger
    logger = logging.getLogger('whatsapp_bulk_sender')
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.info(f"Logging to file: {log_file}")
    
    logger.info(f"Logging initialized at level: {log_level}")
    return logger


# -----------------------
# Environment Configuration
# -----------------------
def load_env_file(path: str) -> Dict[str, str]:
    """
    Load environment variables from a .env file.
    
    Args:
        path: Path to the .env file
        
    Returns:
        Dictionary of environment variables loaded from the file
        
    Note:
        - Ignores comments (lines starting with #)
        - Handles quoted values
        - Skips malformed lines
    """
    vals = {}
    logger = logging.getLogger('whatsapp_bulk_sender')
    
    try:
        logger.debug(f"Loading environment file: {path}")
        with open(path, "r", encoding="utf-8") as f:
            line_num = 0
            for line in f:
                line_num += 1
                s = line.strip()
                
                # Skip empty lines and comments
                if not s or s.startswith("#"):
                    continue
                    
                # Must contain equals sign
                if "=" not in s:
                    logger.warning(f"Malformed line {line_num} in {path}: {s}")
                    continue
                    
                k, v = s.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'").strip('"')
                vals[k] = v
                logger.debug(f"Loaded env var: {k}={'*' * len(v) if 'TOKEN' in k or 'PASSWORD' in k else v}")
                
        logger.info(f"Successfully loaded {len(vals)} environment variables from {path}")
    except FileNotFoundError:
        logger.warning(f"Environment file not found: {path}")
    except Exception as e:
        logger.error(f"Error loading environment file {path}: {e}")
        
    return vals


def apply_env(vals: Dict[str, str]) -> None:
    """
    Apply environment variables to the current process.
    
    Args:
        vals: Dictionary of environment variables to apply
        
    Note:
        Only sets variables that are not already present in the environment
    """
    logger = logging.getLogger('whatsapp_bulk_sender')
    applied_count = 0
    
    for k, v in vals.items():
        # Don't clobber real env if already set
        if os.getenv(k) is None:
            os.environ[k] = v
            applied_count += 1
            logger.debug(f"Applied env var: {k}")
        else:
            logger.debug(f"Skipped env var (already set): {k}")
            
    logger.info(f"Applied {applied_count} environment variables to process")

# -----------------------
# Utility Functions
# -----------------------
def fail(msg: str, code: int = 1) -> None:
    """
    Log error message and exit the application.
    
    Args:
        msg: Error message to display
        code: Exit code (default: 1)
    """
    logger = logging.getLogger('whatsapp_bulk_sender')
    logger.critical(f"FATAL ERROR: {msg}")
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def sanitize_phone(raw: str) -> str:
    """
    Sanitize phone number to digits-only format for WhatsApp Cloud API.
    
    Args:
        raw: Raw phone number string
        
    Returns:
        Sanitized phone number containing only digits
        
    Note:
        WhatsApp Cloud API expects phone numbers in international format
        with digits only (no spaces, dashes, parentheses, etc.)
    """
    logger = logging.getLogger('whatsapp_bulk_sender')
    sanitized = re.sub(r"\D", "", raw or "")
    logger.debug(f"Sanitized phone number: '{raw}' -> '{sanitized}'")
    return sanitized


def validate_phone_number(phone: str) -> bool:
    """
    Validate if a phone number meets minimum requirements.
    
    Args:
        phone: Phone number to validate
        
    Returns:
        True if phone number is valid, False otherwise
    """
    # Basic validation: at least 8 digits for international numbers
    return len(phone) >= 8 and phone.isdigit()


def read_numbers_from_csv(path: str) -> List[str]:
    """
    Read and validate phone numbers from a CSV file.
    
    Args:
        path: Path to CSV file containing phone numbers
        
    Returns:
        List of validated phone numbers
        
    Raises:
        FileNotFoundError: If CSV file doesn't exist
        Exception: If there's an error reading the CSV file
        
    Note:
        - CSV file should have no headers
        - Phone numbers should be in the first column
        - Invalid numbers are skipped and logged
    """
    logger = logging.getLogger('whatsapp_bulk_sender')
    nums = []
    invalid_count = 0
    
    logger.info(f"Reading phone numbers from CSV: {path}")
    
    try:
        with open(path, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            row_num = 0
            
            for row in reader:
                row_num += 1
                
                if not row:
                    logger.debug(f"Skipping empty row {row_num}")
                    continue
                    
                raw = row[0].strip()
                if not raw:
                    logger.debug(f"Skipping empty phone number at row {row_num}")
                    continue
                    
                digits = sanitize_phone(raw)
                
                if not validate_phone_number(digits):
                    logger.warning(f"Invalid phone number at row {row_num}: '{raw}' -> '{digits}'")
                    invalid_count += 1
                    continue
                    
                nums.append(digits)
                logger.debug(f"Added valid phone number from row {row_num}: {digits}")
                
        logger.info(f"Successfully loaded {len(nums)} valid phone numbers from CSV")
        if invalid_count > 0:
            logger.warning(f"Skipped {invalid_count} invalid phone numbers")
            
    except FileNotFoundError:
        logger.error(f"CSV file not found: {path}")
        raise
    except Exception as e:
        logger.error(f"Error reading CSV file {path}: {e}")
        raise
        
    return nums


def write_failed_numbers_to_csv(failed_numbers: List[Dict[str, str]], output_path: str = "failed.csv") -> None:
    """
    Write failed phone numbers and error details to a CSV file.
    
    Args:
        failed_numbers: List of dictionaries containing phone number and error info
        output_path: Path to the output CSV file (default: 'failed.csv')
        
    Note:
        Creates a CSV with headers: phone_number, error_message, timestamp
        If file exists, it will be overwritten
    """
    logger = logging.getLogger('whatsapp_bulk_sender')
    
    if not failed_numbers:
        logger.info("No failed numbers to write to CSV")
        return
    
    try:
        logger.info(f"Writing {len(failed_numbers)} failed numbers to: {output_path}")
        
        # Ensure the directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow(['phone_number', 'error_message', 'timestamp'])
            
            # Write failed numbers
            for entry in failed_numbers:
                writer.writerow([
                    entry['phone_number'],
                    entry['error_message'],
                    entry['timestamp']
                ])
        
        logger.info(f"Successfully wrote failed numbers to: {output_path}")
        
    except Exception as e:
        logger.error(f"Error writing failed numbers to CSV: {e}")
        # Don't raise the exception as this is a non-critical operation


# -----------------------
# WhatsApp Cloud API Functions
# -----------------------
def upload_media(phone_number_id: str, access_token: str, file_path: str, mime_type: str, graph_ver: str) -> str:
    """
    Upload media file to WhatsApp Cloud API and get media ID.
    
    Args:
        phone_number_id: WhatsApp Business Phone Number ID
        access_token: WhatsApp Cloud API access token
        file_path: Path to the file to upload
        mime_type: MIME type of the file
        graph_ver: Graph API version to use
        
    Returns:
        Media ID string for the uploaded file
        
    Raises:
        RuntimeError: If upload fails or response is invalid
        FileNotFoundError: If file doesn't exist
        requests.RequestException: If network error occurs
    """
    logger = logging.getLogger('whatsapp_bulk_sender')
    
    # Validate file exists
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    file_size = os.path.getsize(file_path)
    logger.info(f"Uploading media file: {file_path} ({file_size} bytes, {mime_type})")
    
    url = f"https://graph.facebook.com/{graph_ver}/{phone_number_id}/media"
    headers = {"Authorization": f"Bearer {access_token[:10]}..."}  # Mask token in logs
    
    try:
        with open(file_path, "rb") as fh:
            files = {
                "file": (os.path.basename(file_path), fh, mime_type),
                "type": (None, mime_type),
            }
            
            logger.debug(f"Making upload request to: {url}")
            resp = requests.post(url, headers={"Authorization": f"Bearer {access_token}"}, 
                               files=files, timeout=60)
            
        logger.debug(f"Upload response status: {resp.status_code}")
        
        if resp.status_code >= 300:
            logger.error(f"Upload failed with status {resp.status_code}: {resp.text}")
            raise RuntimeError(f"Upload failed: {resp.status_code} {resp.text}")
            
        data = resp.json()
        logger.debug(f"Upload response data: {data}")
        
        media_id = data.get("id")
        if not media_id:
            logger.error(f"Upload response missing media ID: {data}")
            raise RuntimeError(f"Upload response missing media id: {data}")
            
        logger.info(f"Successfully uploaded media, ID: {media_id}")
        return media_id
        
    except requests.RequestException as e:
        logger.error(f"Network error during upload: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during upload: {e}")
        raise


def post_json_messages(phone_number_id: str, access_token: str, payload: dict, graph_ver: str) -> dict:
    """
    Send a JSON message payload to WhatsApp Cloud API.
    
    Args:
        phone_number_id: WhatsApp Business Phone Number ID
        access_token: WhatsApp Cloud API access token
        payload: Message payload dictionary
        graph_ver: Graph API version to use
        
    Returns:
        Response dictionary from WhatsApp API
        
    Raises:
        RuntimeError: If message sending fails
        requests.RequestException: If network error occurs
    """
    logger = logging.getLogger('whatsapp_bulk_sender')
    
    url = f"https://graph.facebook.com/{graph_ver}/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Log payload without sensitive data
    safe_payload = payload.copy()
    logger.debug(f"Sending message payload to {safe_payload.get('to', 'unknown')}: {safe_payload.get('type', 'unknown')}")
    
    try:
        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
        
        logger.debug(f"Message response status: {resp.status_code}")
        
        if resp.status_code >= 300:
            logger.error(f"Message send failed with status {resp.status_code}: {resp.text}")
            raise RuntimeError(f"Send failed: {resp.status_code} {resp.text}")
            
        response_data = resp.json()
        logger.debug(f"Message response data: {response_data}")
        return response_data
        
    except requests.RequestException as e:
        logger.error(f"Network error during message send: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during message send: {e}")
        raise


def send_template(phone_number_id: str, access_token: str, to_num: str, template_name: str, lang: str, graph_ver: str) -> str:
    """
    Send a WhatsApp message template to a recipient.
    
    Args:
        phone_number_id: WhatsApp Business Phone Number ID
        access_token: WhatsApp Cloud API access token
        to_num: Recipient phone number (digits only)
        template_name: Name of the approved message template
        lang: Language code for the template (e.g., 'en_US')
        graph_ver: Graph API version to use
        
    Returns:
        Message ID from WhatsApp API response
        
    Raises:
        RuntimeError: If template sending fails
    """
    logger = logging.getLogger('whatsapp_bulk_sender')
    
    logger.info(f"Sending template '{template_name}' ({lang}) to {to_num}")
    
    payload = {
        "messaging_product": "whatsapp",
        "to": to_num,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": lang}
        }
    }
    
    try:
        data = post_json_messages(phone_number_id, access_token, payload, graph_ver)
        message_id = (data.get("messages") or [{}])[0].get("id", "unknown")
        logger.info(f"Template sent successfully to {to_num}, message ID: {message_id}")
        return message_id
        
    except Exception as e:
        logger.error(f"Failed to send template to {to_num}: {e}")
        raise


def send_document_by_id(phone_number_id: str, access_token: str, to_num: str, media_id: str, 
                       filename: str, caption: str, graph_ver: str) -> str:
    """
    Send a document message using a previously uploaded media ID.
    
    Args:
        phone_number_id: WhatsApp Business Phone Number ID
        access_token: WhatsApp Cloud API access token
        to_num: Recipient phone number (digits only)
        media_id: Media ID from previous upload
        filename: Display filename for the document
        caption: Text caption to accompany the document
        graph_ver: Graph API version to use
        
    Returns:
        Message ID from WhatsApp API response
        
    Raises:
        RuntimeError: If document sending fails
    """
    logger = logging.getLogger('whatsapp_bulk_sender')
    
    logger.info(f"Sending document '{filename}' to {to_num} (media_id: {media_id})")
    
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
    
    try:
        data = post_json_messages(phone_number_id, access_token, payload, graph_ver)
        message_id = (data.get("messages") or [{}])[0].get("id", "unknown")
        logger.info(f"Document sent successfully to {to_num}, message ID: {message_id}")
        return message_id
        
    except Exception as e:
        logger.error(f"Failed to send document to {to_num}: {e}")
        raise

# -----------------------
# Command Line Argument Parsing
# -----------------------
def get_cli_flag(name: str, default=None):
    """
    Extract command line flag value with support for boolean and key=value formats.
    
    Args:
        name: Flag name (e.g., '--dry-run', '--rate')
        default: Default value if flag is not present
        
    Returns:
        Flag value: True for boolean flags, string for key=value pairs, default otherwise
        
    Examples:
        --dry-run         -> True
        --rate=0.5        -> "0.5"
        --csv=file.csv    -> "file.csv"
    """
    for a in sys.argv[1:]:
        if a == name:
            return True
        if a.startswith(name + "="):
            return a.split("=", 1)[1]
    return default


def validate_configuration(config: Dict[str, any]) -> Tuple[bool, List[str]]:
    """
    Validate the complete configuration for required fields and constraints.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    logger = logging.getLogger('whatsapp_bulk_sender')
    errors = []
    
    # Required fields
    required_fields = [
        ('phone_number_id', 'WA_PHONE_NUMBER_ID'),
        ('access_token', 'WA_ACCESS_TOKEN'),
        ('csv_path', 'CSV_PATH'),
        ('pdf_path', 'PDF_PATH')
    ]
    
    for field_key, env_name in required_fields:
        if not config.get(field_key):
            errors.append(f"{env_name} is required")
    
    # File existence checks
    if config.get('pdf_path') and not os.path.isfile(config['pdf_path']):
        errors.append(f"PDF file not found: {config['pdf_path']}")
        
    if config.get('csv_path') and not os.path.isfile(config['csv_path']):
        errors.append(f"CSV file not found: {config['csv_path']}")
    
    # Rate validation
    try:
        rate = float(config.get('rate', 0.5))
        if rate < 0:
            errors.append("RATE must be non-negative")
        config['rate'] = rate  # Convert to float
    except (ValueError, TypeError):
        errors.append(f"RATE must be a valid number, got: {config.get('rate')}")
    
    # Template validation
    template = config.get('template', '')
    if template and ':' not in template:
        errors.append("TEMPLATE must be in format 'name:lang' (e.g., 'hello_world:en_US')")
    
    is_valid = len(errors) == 0
    
    if is_valid:
        logger.info("Configuration validation passed")
    else:
        logger.error(f"Configuration validation failed with {len(errors)} errors")
        for error in errors:
            logger.error(f"  - {error}")
    
    return is_valid, errors

# -----------------------
# Main Application Logic
# -----------------------
def main() -> None:
    """
    Main application entry point.
    
    Orchestrates the complete workflow:
    1. Configure logging
    2. Load and validate configuration
    3. Read recipient numbers from CSV
    4. Upload media file
    5. Send messages to all recipients
    
    Raises:
        SystemExit: On fatal errors or validation failures
    """
    start_time = datetime.now()
    
    # Initialize logging first (before other operations)
    log_level = get_cli_flag("--log-level", os.getenv("LOG_LEVEL", "INFO"))
    log_file = get_cli_flag("--log-file", os.getenv("LOG_FILE"))
    logger = setup_logging(log_level, log_file)
    
    logger.info("=" * 60)
    logger.info("WhatsApp Bulk Document Sender - Starting")
    logger.info(f"Version: 2.0.0")
    logger.info(f"Start time: {start_time}")
    logger.info("=" * 60)
    
    try:
        # Load environment configuration
        env_path = get_cli_flag("--env", ".env")
        logger.info(f"Loading environment from: {env_path}")
        apply_env(load_env_file(env_path))

        # Apply CLI overrides
        cli_overrides = {}
        if get_cli_flag("--csv") is not None:
            cli_overrides["CSV_PATH"] = get_cli_flag("--csv")
        if get_cli_flag("--pdf") is not None:
            cli_overrides["PDF_PATH"] = get_cli_flag("--pdf")
        if get_cli_flag("--caption") is not None:
            cli_overrides["CAPTION"] = get_cli_flag("--caption")
        if get_cli_flag("--filename") is not None:
            cli_overrides["FILENAME"] = get_cli_flag("--filename")
        if get_cli_flag("--rate") is not None:
            cli_overrides["RATE"] = get_cli_flag("--rate")
        if get_cli_flag("--template") is not None:
            cli_overrides["TEMPLATE"] = get_cli_flag("--template")
        if get_cli_flag("--dry-run", False):
            cli_overrides["DRY_RUN"] = "true"
            
        # Apply CLI overrides to environment
        for key, value in cli_overrides.items():
            os.environ[key] = value
            logger.info(f"CLI override applied: {key}={value}")

        # Gather configuration
        config = {
            'phone_number_id': os.getenv("WA_PHONE_NUMBER_ID"),
            'access_token': os.getenv("WA_ACCESS_TOKEN"),
            'graph_ver': os.getenv("WA_GRAPH_VERSION", "v20.0"),
            'csv_path': os.getenv("CSV_PATH"),
            'pdf_path': os.getenv("PDF_PATH"),
            'caption': os.getenv("CAPTION", ""),
            'filename': os.getenv("FILENAME"),
            'rate': os.getenv("RATE", "0.5"),
            'template': os.getenv("TEMPLATE", ""),
            'dry_run': os.getenv("DRY_RUN", "false").lower() in ("1", "true", "yes")
        }
        
        # Log configuration (mask sensitive data)
        logger.info("Configuration loaded:")
        for key, value in config.items():
            if key == 'access_token' and value:
                logger.info(f"  {key}: {'*' * len(value[:10])}...")
            elif key in ['phone_number_id'] and value:
                logger.info(f"  {key}: {'*' * max(0, len(value) - 4)}{value[-4:] if len(value) >= 4 else value}")
            else:
                logger.info(f"  {key}: {value}")

        # Validate configuration
        is_valid, validation_errors = validate_configuration(config)
        if not is_valid:
            for error in validation_errors:
                logger.error(f"Configuration error: {error}")
            fail("Configuration validation failed. Please check your settings.")

        # Set defaults and normalize values
        if not config['filename']:
            config['filename'] = os.path.basename(config['pdf_path'])
            logger.info(f"Using default filename: {config['filename']}")

        # Determine and validate MIME type
        mime_type, _ = mimetypes.guess_type(config['pdf_path'])
        if not mime_type:
            mime_type = "application/pdf"
            logger.info("MIME type not detected, defaulting to application/pdf")
        elif mime_type != "application/pdf":
            logger.warning(f"Detected MIME type '{mime_type}', forcing to application/pdf")
            mime_type = "application/pdf"
        else:
            logger.info(f"MIME type detected: {mime_type}")

        # Parse template configuration
        tpl_name = tpl_lang = None
        if config['template']:
            try:
                tpl_name, tpl_lang = config['template'].split(":", 1)
                logger.info(f"Template configured: {tpl_name} ({tpl_lang})")
            except Exception:
                fail("TEMPLATE must be in format 'name:lang' (e.g., 'hello_world:en_US')")

        # Read and validate phone numbers
        logger.info("Loading recipient phone numbers...")
        numbers = read_numbers_from_csv(config['csv_path'])
        if not numbers:
            fail("No valid phone numbers found in CSV file")
        
        logger.info(f"Loaded {len(numbers)} valid recipient numbers")

        # Phase 1: Upload media
        logger.info("=" * 40)
        logger.info("PHASE 1: Media Upload")
        logger.info("=" * 40)
        
        if config['dry_run']:
            logger.info("[DRY-RUN] Simulating media upload...")
            logger.info(f"[DRY-RUN] File: {config['pdf_path']}")
            logger.info(f"[DRY-RUN] Filename: {config['filename']}")
            logger.info(f"[DRY-RUN] MIME Type: {mime_type}")
            logger.info(f"[DRY-RUN] Phone Number ID: {config['phone_number_id']}")
            logger.info(f"[DRY-RUN] Graph Version: {config['graph_ver']}")
            media_id = "DRY_RUN_MEDIA_ID"
        else:
            media_id = upload_media(
                config['phone_number_id'], 
                config['access_token'], 
                config['pdf_path'], 
                mime_type, 
                config['graph_ver']
            )

        # Phase 2: Send messages
        logger.info("=" * 40)
        logger.info("PHASE 2: Message Broadcasting")
        logger.info("=" * 40)
        
        success_count = 0
        failure_count = 0
        failed_numbers = []  # Track failed numbers with details
        
        for i, phone_number in enumerate(numbers, 1):
            logger.info(f"Processing recipient {i}/{len(numbers)}: {phone_number}")
            
            try:
                if config['dry_run']:
                    message_type = "TEMPLATE+DOCUMENT" if tpl_name else "DOCUMENT"
                    logger.info(f"[DRY-RUN] {message_type} -> {phone_number}")
                    logger.info(f"[DRY-RUN]   Filename: {config['filename']}")
                    logger.info(f"[DRY-RUN]   Caption: '{config['caption']}'")
                    logger.info(f"[DRY-RUN]   Media ID: {media_id}")
                    if tpl_name:
                        logger.info(f"[DRY-RUN]   Template: {tpl_name} ({tpl_lang})")
                else:
                    # Send template message first (if configured)
                    if tpl_name:
                        template_id = send_template(
                            config['phone_number_id'], 
                            config['access_token'], 
                            phone_number, 
                            tpl_name, 
                            tpl_lang, 
                            config['graph_ver']
                        )
                        logger.info(f"Template message sent, ID: {template_id}")
                    
                    # Send document message
                    doc_id = send_document_by_id(
                        config['phone_number_id'], 
                        config['access_token'], 
                        phone_number, 
                        media_id, 
                        config['filename'], 
                        config['caption'], 
                        config['graph_ver']
                    )
                    logger.info(f"Document message sent, ID: {doc_id}")
                
                success_count += 1
                logger.info(f"✓ Success for {phone_number}")
                
            except Exception as e:
                failure_count += 1
                logger.error(f"✗ Failed for {phone_number}: {e}")
                
                # Record failed number with details
                failed_numbers.append({
                    'phone_number': phone_number,
                    'error_message': str(e),
                    'timestamp': datetime.now().isoformat()
                })
            
            # Rate limiting delay (except for last recipient)
            if i < len(numbers):
                logger.debug(f"Rate limiting: sleeping {config['rate']} seconds...")
                time.sleep(config['rate'])

        # Final summary
        end_time = datetime.now()
        duration = end_time - start_time
        
        logger.info("=" * 60)
        logger.info("OPERATION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Start time: {start_time}")
        logger.info(f"End time: {end_time}")
        logger.info(f"Duration: {duration}")
        logger.info(f"Total recipients: {len(numbers)}")
        logger.info(f"Successful sends: {success_count}")
        logger.info(f"Failed sends: {failure_count}")
        logger.info(f"Success rate: {(success_count / len(numbers) * 100):.1f}%")
        
        if config['dry_run']:
            logger.info("NOTE: This was a dry-run - no actual messages were sent")
        
        if failure_count > 0:
            logger.warning(f"{failure_count} messages failed to send. Check the logs above for details.")
            
            # Write failed numbers to CSV file (unless dry-run)
            if not config['dry_run']:
                failed_csv_path = get_cli_flag("--failed-csv", os.getenv("FAILED_CSV_PATH", "failed.csv"))
                write_failed_numbers_to_csv(failed_numbers, failed_csv_path)
                logger.info(f"Failed phone numbers written to: {failed_csv_path}")
            else:
                logger.info("[DRY-RUN] Would write failed numbers to failed.csv")
        
        logger.info("=" * 60)
        
    except KeyboardInterrupt:
        logger.warning("Operation interrupted by user (Ctrl+C)")
        sys.exit(130)
    except Exception as e:
        logger.critical(f"Unexpected error: {e}", exc_info=True)
        fail(f"Unexpected error: {e}")
    
    logger.info("WhatsApp Bulk Document Sender - Finished")
    
    # Exit with appropriate code
    if 'failure_count' in locals() and failure_count > 0:
        sys.exit(1)  # Some failures occurred
    else:
        sys.exit(0)  # All successful

if __name__ == "__main__":
    main()
