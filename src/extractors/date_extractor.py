"""Extractor for explicit award and start date statements from ingested documents (VAL-11)."""

import re
import logging
from datetime import date, datetime
from typing import List, Optional, Tuple, Sequence
from src.core.models import ExtractedDocument

logger = logging.getLogger(__name__)

PREAMBLE_DATE_REGEX = re.compile(
    r'(?:This\s+SOW|This\s+Statement\s+of\s+Work)\s+(?:becomes\s+effective|is\s+made\s+and\s+entered\s+into|is\s+entered\s+into)\s+(?:on|as\s+of)\s+([A-Za-z]+\s+\d{1,2},?\s*\d{4}|\d{4}-\d{2}-\d{2})',
    re.IGNORECASE
)

EFFECTIVE_DATE_LABEL_REGEX = re.compile(
    r'\b(?:SOW\s+Effective\s+Date|Contract\s+Effective\s+Date|Execution\s+Date|Award\s+Date)[:\s]+([A-Za-z]+\s+\d{1,2},?\s*\d{4}|\d{4}-\d{2}-\d{2})',
    re.IGNORECASE
)

START_DATE_STMT_REGEX = re.compile(
    r'\b(?:Estimated\s+Start\s+Date|Project\s+Start\s+Date|Start\s+Date)[:\s]+([A-Za-z]+\s+\d{1,2},?\s*\d{4}|\d{4}-\d{2}-\d{2})',
    re.IGNORECASE
)


def parse_date_string(date_str: str) -> Optional[date]:
    """Parse date from string normalized from statement match."""
    cleaned = re.sub(r'\s+', ' ', date_str).strip()
    formats = [
        "%B %d, %Y",
        "%B %d %Y",
        "%b %d, %Y",
        "%b %d %Y",
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            pass
    return None


def extract_stated_award_date(
    documents: Sequence[ExtractedDocument],
) -> Tuple[Optional[date], Optional[str]]:
    """Extract explicit award/start date from ingested documents per VAL-11.

    Returns (extracted_date, warning_message_if_conflict).
    """
    preamble_dates: List[Tuple[date, str, str]] = []
    start_dates: List[Tuple[date, str, str]] = []

    for doc in documents:
        text = doc.text_content or ""
        for m in PREAMBLE_DATE_REGEX.finditer(text):
            d = parse_date_string(m.group(1))
            if d:
                preamble_dates.append((d, m.group(0), doc.file_name))
        for m in EFFECTIVE_DATE_LABEL_REGEX.finditer(text):
            d = parse_date_string(m.group(1))
            if d:
                preamble_dates.append((d, m.group(0), doc.file_name))
        for m in START_DATE_STMT_REGEX.finditer(text):
            d = parse_date_string(m.group(1))
            if d:
                start_dates.append((d, m.group(0), doc.file_name))

    # Determine date according to VAL-11 precedence
    warning_msg: Optional[str] = None
    selected_date: Optional[date] = None

    if preamble_dates:
        selected_date = preamble_dates[0][0]
        if start_dates and start_dates[0][0] != selected_date:
            warning_msg = (
                f"SOW preamble effective date ({selected_date.isoformat()} from '{preamble_dates[0][1]}') "
                f"differs from estimated start date ({start_dates[0][0].isoformat()} from '{start_dates[0][1]}'). "
                f"Governing preamble effective date selected per VAL-11."
            )
            logger.warning(warning_msg)
    elif start_dates:
        selected_date = start_dates[0][0]
        if len(start_dates) > 1 and any(sd[0] != selected_date for sd in start_dates):
            diff_sd = next(sd for sd in start_dates if sd[0] != selected_date)
            warning_msg = (
                f"Multiple start date statements found with differing dates: "
                f"'{start_dates[0][1]}' ({selected_date.isoformat()}) vs '{diff_sd[1]}' ({diff_sd[0].isoformat()}). "
                f"Preferred earlier/primary statement per VAL-11."
            )
            logger.warning(warning_msg)

    return selected_date, warning_msg
