from __future__ import annotations
import logging
from pathlib import Path
logger = logging.getLogger(__name__)

def extract_text(file_path: Path) -> str:
    try:
        extension = file_path.suffix.lower()
        if extension == ".pdf":
            import pdfplumber
            with pdfplumber.open(file_path) as pdf: return "\n".join(page.extract_text() or "" for page in pdf.pages).strip()
        if extension == ".docx":
            from docx import Document
            doc = Document(str(file_path)); parts = [p.text for p in doc.paragraphs]
            parts += [" | ".join(cell.text for cell in row.cells) for table in doc.tables for row in table.rows]
            return "\n".join(x for x in parts if x.strip()).strip()
        if extension == ".xlsx":
            import pandas as pd
            sheets = pd.read_excel(file_path, sheet_name=None, dtype=str, engine="openpyxl")
            return "\n".join(f"Sheet: {name}\n{frame.fillna('').to_csv(index=False)}" for name, frame in sheets.items()).strip()
        if extension in {".jpg", ".jpeg", ".png"}:
            from PIL import Image
            import pytesseract
            return pytesseract.image_to_string(Image.open(file_path)).strip()
    except Exception as exc:
        logger.warning("Text extraction failed for %s: %s", file_path, exc)
    return ""
