# parsing.py
import re
import io
from datetime import datetime, date
from typing import Dict, Optional, List

import pytesseract
from PIL import Image
import pdfplumber
from fastapi import UploadFile, HTTPException, status

# --- Rule-Based Parsing Logic ---

# A simple category mapper based on vendor name
VENDOR_CATEGORIES = {
    "zomato": "Food",
    "swiggy": "Food",
    "bescom": "Utilities",
    "reliance fresh": "Groceries",
    "more": "Groceries",
    "jio": "Internet",
    "act fibernet": "Internet",
}

# Regex patterns for common fields. Order matters for fallbacks.
PATTERNS = {
    "vendor": [
        re.compile(r'(?:from|billed by|sold by|store):\s*([^\n]+)', re.I),
        re.compile(r'^(?:[A-Z\s]+)\n', re.I), # Grabs the first line if it's all caps (common for vendor names)
        re.compile(r'^\s*([^\n]+)\n', re.I), # First non-empty line
        re.compile(r'Store[^\n]*:\s*([^\n]+)', re.I)
    ],
    "date": [
        re.compile(r'Date:\s*(\d{2}[/-]\d{2}[/-]\d{4})', re.I),
        re.compile(r'(\d{2}-\w{3}-\d{4})', re.I), # 20-Jul-2025
        re.compile(r'Billed on:\s*(\d{2}\.\d{2}\.\d{4})', re.I)
    ],
    "amount": [
        re.compile(r'Total Amount:\s+₹?([\d,]+\.\d{2})', re.I),
        re.compile(r'Total:\s*₹?([\d,]+\.\d{2})', re.I),
        re.compile(r'Grand Total:\s*₹?([\d,]+\.\d{2})', re.I),
        re.compile(r'Amount Paid:\s*₹?([\d,]+\.\d{2})', re.I),
    ]
}

def clean_amount(amount_str: str) -> float:
    """Removes currency symbols, commas and converts to float."""
    return float(amount_str.replace(",", "").replace("₹", "").strip())

def clean_date(date_str: str) -> Optional[date]:
    """Tries to parse a date string from multiple formats."""
    formats_to_try = ["%d/%m/%Y", "%d-%m-%Y", "%d-%b-%Y", "%d.%m.%Y"]
    for fmt in formats_to_try:
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    return None # Return None if no format matches

def extract_structured_data(text: str) -> List[Dict]:
    """
    Parses raw text to extract structured fields from one or more receipts in the text.
    Receipts are assumed to be separated by a line of '---' or '==='.
    """
    receipts = []
    # Split the text into chunks, assuming each chunk is one receipt
    # This is a simple heuristic and might need to be more robust
    chunks = re.split(r'\n-[-]{2,}\n|\n=[=]{2,}\n', text)

    for chunk in chunks:
        if not chunk.strip():
            continue

        extracted = {}
        
        # Try to find each field using the patterns
        for field, patterns in PATTERNS.items():
            # Special handling for vendor to prioritize all-caps title
            if field == 'vendor':
                # Check for all-caps vendor first
                all_caps_pattern = re.compile(r"^([A-Z\s&]+)$", re.MULTILINE)
                match = all_caps_pattern.search(chunk)
                if match:
                    extracted['vendor'] = match.group(1).strip()
                    # If found, we can be confident and skip other vendor patterns
                    continue 

            for pattern in patterns:
                # If vendor is already found by all-caps, don't run other vendor patterns
                if field == 'vendor' and 'vendor' in extracted:
                    break

                match = pattern.search(chunk)
                if match:
                    value = match.group(1).strip()
                    if field == "amount":
                        extracted[field] = clean_amount(value)
                    elif field == "date":
                        extracted[field] = clean_date(value)
                    else:
                        extracted[field] = value
                    break # Move to the next field once found
        
        # Basic validation: only add if essential fields are found
        if not all(k in extracted for k in ['vendor', 'date', 'amount']):
            continue

        # Map category
        vendor_lower = extracted.get("vendor", "").lower()
        for keyword, category in VENDOR_CATEGORIES.items():
            if keyword in vendor_lower:
                extracted["category"] = category
                break
        
        # Currency detection
        currency_pattern = re.compile(r"(?:\$|€|£|¥|₹|Rs\.?)\s*([\d,]+(?:\.[\d]{2})?)")
        currency_match = currency_pattern.search(chunk)
        currency = "INR"  # Default
        if currency_match:
            if "$" in currency_match.group(0):
                currency = "USD"
            elif "€" in currency_match.group(0):
                currency = "EUR"
            elif "£" in currency_match.group(0):
                currency = "GBP"
            elif "¥" in currency_match.group(0):
                currency = "JPY"
            elif "₹" in currency_match.group(0) or "Rs" in currency_match.group(0):
                currency = "INR"
        
        receipts.append({
            "vendor": extracted.get("vendor"),
            "transaction_date": extracted.get("date"),
            "total_amount": extracted.get("amount"),
            "category": extracted.get("category", "Uncategorized"),
            "currency": currency,
            "raw_text": chunk # Also include the raw text chunk for context
        })

    return receipts


async def process_file_to_text(file: UploadFile) -> str:
    """
    Processes an uploaded file to extract text.
    Supports: .txt, .jpg, .png, .pdf
    """
    # Read the file content
    contents = await file.read()
    
    # Get the file extension
    filename = file.filename
    if not filename:
        return ""
    extension = filename.split(".")[-1].lower()
    
    # Process based on extension
    if extension == "txt":
        return contents.decode("utf-8")
    elif extension in ["jpg", "jpeg", "png"]:
        # Use OCR for images
        image = Image.open(io.BytesIO(contents))
        text = pytesseract.image_to_string(image)
        return text
    elif extension == "pdf":
        # Use pdfplumber for PDFs
        text = ""
        with pdfplumber.open(io.BytesIO(contents)) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text
    else:
        # Unsupported file type
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {extension}"
        )
