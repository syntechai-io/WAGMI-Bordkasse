"""Receipt OCR service powered by Anthropic vision.

Reads an uploaded receipt (image or PDF) and returns a structured suggestion
that the expense form can pre-fill. All fields are best-effort — the caller is
responsible for ignoring null values and never overwriting fields the user
already filled.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import re
from datetime import date, datetime
from typing import Optional

from anthropic import Anthropic

DEFAULT_MODEL_STR = "claude-sonnet-4-20250514"

logger = logging.getLogger(__name__)

SUPPORTED_CURRENCIES = ["EUR", "DKK", "SEK", "GBP"]
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_PDF_TYPE = "application/pdf"


class ReceiptOCRError(Exception):
    """Raised when the OCR call fails or returns unusable output."""


def _client() -> Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ReceiptOCRError("ANTHROPIC_API_KEY is not configured")
    return Anthropic(api_key=api_key)


def _build_prompt(category_keys: list[str]) -> str:
    cats = ", ".join(category_keys)
    today = date.today().isoformat()
    return (
        "You are an assistant that extracts structured data from a single receipt or invoice. "
        f"Today's date is {today}. "
        "Return ONLY a compact JSON object with these keys (use null when unsure): "
        '{"amount": number|null, "currency": string|null, "date": "YYYY-MM-DD"|null, '
        '"vendor": string|null, "category": string|null, "description": string|null}. '
        f"Allowed currencies: {', '.join(SUPPORTED_CURRENCIES)}. "
        f"Allowed categories (pick the closest, lowercase code): {cats}. "
        "amount must be the grand total the customer paid (including tax, after discounts). "
        "vendor is the merchant or business name, no address. "
        "description is a short label like 'Diesel 32L' or 'Groceries Lidl' (max 60 chars). "
        "Do not include any commentary, markdown, or code fences — just the JSON object."
    )


def _parse_json(text: str) -> dict:
    text = text.strip()
    # Strip code fences if the model returned them anyway
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    # Find the first {...} block defensively
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ReceiptOCRError("Model response did not contain JSON")
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise ReceiptOCRError(f"Invalid JSON from model: {exc}") from exc


def _normalise(raw: dict, category_keys: list[str]) -> dict:
    """Coerce types and drop fields that don't match our enums."""
    out: dict = {
        "amount": None,
        "currency": None,
        "date": None,
        "vendor": None,
        "category": None,
        "description": None,
    }

    amount = raw.get("amount")
    if isinstance(amount, (int, float)) and amount > 0:
        out["amount"] = round(float(amount), 2)
    elif isinstance(amount, str):
        try:
            cleaned = amount.replace(",", ".").replace(" ", "")
            val = float(cleaned)
            if val > 0:
                out["amount"] = round(val, 2)
        except ValueError:
            pass

    currency = (raw.get("currency") or "").upper().strip()
    if currency in SUPPORTED_CURRENCIES:
        out["currency"] = currency

    date_val = raw.get("date")
    if isinstance(date_val, str):
        try:
            parsed = datetime.strptime(date_val[:10], "%Y-%m-%d").date()
            # Sanity: don't accept dates more than 1 day in the future or
            # absurdly old (>10 years).
            today = date.today()
            if (today - parsed).days <= 365 * 10 and (parsed - today).days <= 1:
                out["date"] = parsed.isoformat()
        except ValueError:
            pass

    vendor = raw.get("vendor")
    if isinstance(vendor, str) and vendor.strip():
        out["vendor"] = vendor.strip()[:120]

    category = (raw.get("category") or "").lower().strip()
    if category in category_keys:
        out["category"] = category

    description = raw.get("description")
    if isinstance(description, str) and description.strip():
        out["description"] = description.strip()[:120]

    return out


def extract_receipt(
    file_bytes: bytes,
    content_type: str,
    category_keys: list[str],
    timeout_seconds: float = 25.0,
) -> dict:
    """Extract structured fields from a receipt file.

    Returns a dict with keys: amount, currency, date, vendor, category,
    description. Any value may be None. Raises ReceiptOCRError on transport
    or parsing failures so the caller can log and respond gracefully.
    """
    if not file_bytes:
        raise ReceiptOCRError("Empty file")

    is_pdf = content_type == ALLOWED_PDF_TYPE
    is_image = content_type in ALLOWED_IMAGE_TYPES
    if not (is_pdf or is_image):
        raise ReceiptOCRError(f"Unsupported content type: {content_type}")

    b64 = base64.standard_b64encode(file_bytes).decode("ascii")

    if is_pdf:
        source_block: dict = {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": b64,
            },
        }
    else:
        source_block = {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": content_type,
                "data": b64,
            },
        }

    prompt = _build_prompt(category_keys)
    client = _client().with_options(timeout=timeout_seconds)

    try:
        message = client.messages.create(
            model=DEFAULT_MODEL_STR,
            max_tokens=400,
            messages=[
                {
                    "role": "user",
                    "content": [source_block, {"type": "text", "text": prompt}],
                }
            ],
        )
    except Exception as exc:  # network, auth, timeout, etc.
        raise ReceiptOCRError(f"Anthropic call failed: {exc}") from exc

    # Concatenate any text blocks the model returned
    text_parts = [b.text for b in message.content if getattr(b, "type", None) == "text"]
    if not text_parts:
        raise ReceiptOCRError("Model returned no text content")

    raw = _parse_json("".join(text_parts))
    return _normalise(raw, category_keys)
