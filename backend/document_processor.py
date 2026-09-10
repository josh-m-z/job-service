from pypdf import PdfReader

from backend.db import get_document, save_document_result


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

    page_count = len(reader.pages)
    word_count = len(text.split())
    character_count = len(text)

    save_document_result(
        document_id,
        text,
        page_count,
        word_count,
        character_count
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
