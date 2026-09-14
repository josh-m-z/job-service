from pypdf import PdfReader

from backend.db import get_document, save_document_result

# using regex to extract basic data, it's more of a way to recognize local tet patterns, expected
import re


def extract_document_data(text):

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    title = lines[0] if lines else None

    dates = re.findall(
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        text
    )

    money_amounts = re.findall(
        r"\$\s?\d+(?:,\d{3})*(?:\.\d{2})?",
        text
    )

    organizations = re.findall(
    r"(?m)^[A-Z][A-Za-z0-9 &.'-]+(?:LLC|Inc\.?|Corp\.?|Corporation|Ltd\.?)$",
    text
)

    lowered_text = text.lower()

    if "invoice" in lowered_text:
        document_type = "invoice"

    elif "resume" in lowered_text or "experience" in lowered_text:
        document_type = "resume"

    elif "receipt" in lowered_text:
        document_type = "receipt"

    else:
        document_type = "unknown"

    return {
        "document_type": document_type,
        "title": title,
        "dates": dates,
        "money_amounts": money_amounts,
        "organizations": organizations
    }


def process_document(payload):
    document_id = payload["document_id"]

    document = get_document(document_id) # gets document contents

    if document is None:
        raise ValueError("Document not found")

    document_id, filename, content_type, file_path, created_at = document

    reader = PdfReader(file_path)

    text = ""

    for page in reader.pages:
        text += page.extract_text() or "" # the or is in case there is no extectable text in the pdf
        extracted_data = extract_document_data(text)

    page_count = len(reader.pages)
    word_count = len(text.split())
    character_count = len(text)

    save_document_result(
        document_id,
        text,
        page_count,
        word_count,
        character_count,
        extracted_data
    )

    # reutrns a dic of the data
    result = {
        "document_id": str(document_id),
        "filename": filename,
        "page_count": page_count,
        "word_count": word_count,
        "character_count": character_count,
        "text": text,
    }

    return result
