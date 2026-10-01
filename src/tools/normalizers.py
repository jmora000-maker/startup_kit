"""Artifact normalization utilities for snapshot testing and comparison (QA-03)."""

import re
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import docx
import openpyxl

DATE_REGEX = re.compile(r'\b\d{4}-\d{2}-\d{2}\b')
GENERATED_DATE_REGEX = re.compile(r'Generated\s+\d{4}-\d{2}-\d{2}', re.IGNORECASE)
DRAFTED_DATE_REGEX = re.compile(r'Drafted\s*:\s*\d{4}-\d{2}-\d{2}', re.IGNORECASE)


def normalize_text_excluding_dates(text: Optional[str]) -> str:
    """Normalize text by stripping dynamic dates/timestamps and standardizing whitespace."""
    if not text:
        return ""
    cleaned = str(text)
    cleaned = GENERATED_DATE_REGEX.sub("Generated <DATE>", cleaned)
    cleaned = DRAFTED_DATE_REGEX.sub("Drafted: <DATE>", cleaned)
    # Standardize whitespace
    cleaned = re.sub(r'[ \t]+', ' ', cleaned).strip()
    return cleaned


def normalize_docx_tables(docx_path: Path) -> List[Dict[str, Any]]:
    """Extract and normalize all tables from a .docx file into structured JSON."""
    if not docx_path.exists():
        return []
    doc = docx.Document(str(docx_path))
    tables_data = []

    for t_idx, table in enumerate(doc.tables):
        rows_data = []
        for r_idx, row in enumerate(table.rows):
            cells_data = [normalize_text_excluding_dates(cell.text) for cell in row.cells]
            # De-duplicate consecutive identical cells if merged
            rows_data.append(cells_data)
        tables_data.append({
            "table_index": t_idx,
            "rows_count": len(rows_data),
            "rows": rows_data
        })

    return tables_data


def normalize_xlsx_workbook(xlsx_path: Path) -> Dict[str, List[List[Any]]]:
    """Extract and normalize sheets and rows from a .xlsx file into structured JSON."""
    if not xlsx_path.exists():
        return {}
    wb = openpyxl.load_workbook(str(xlsx_path), data_only=False)
    sheets_data: Dict[str, List[List[Any]]] = {}

    for sheet_name in wb.sheetnames:
        if sheet_name.startswith("_"):
            continue  # Skip internal list sheets like _Lists
        sheet = wb[sheet_name]
        sheet_rows: List[List[Any]] = []
        for row in sheet.iter_rows(values_only=True):
            # Check if row has any non-empty cell
            if not any(row):
                continue
            normalized_row = []
            for cell_val in row:
                if cell_val is None:
                    normalized_row.append("")
                elif hasattr(cell_val, "strftime"):
                    normalized_row.append("<DATE>")
                else:
                    norm_val = normalize_text_excluding_dates(str(cell_val))
                    normalized_row.append(norm_val)
            sheet_rows.append(normalized_row)
        sheets_data[sheet_name] = sheet_rows

    return sheets_data


def normalize_artifacts(
    kit_path: Optional[Path] = None,
    checklist_path: Optional[Path] = None,
    workbook_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Normalize Kit tables, Checklist tables, and Workbook sheets into a single JSON-serializable dictionary."""
    result: Dict[str, Any] = {}
    if kit_path and kit_path.exists():
        result["kit_tables"] = normalize_docx_tables(kit_path)
    if checklist_path and checklist_path.exists():
        result["checklist_tables"] = normalize_docx_tables(checklist_path)
    if workbook_path and workbook_path.exists():
        result["workbook_sheets"] = normalize_xlsx_workbook(workbook_path)
    return result
