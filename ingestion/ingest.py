from pathlib import Path

from docling.document_converter import DocumentConverter

PDF_PATH = Path(__file__).parent.parent / "data" / "políticas_da_loja.pdf"


def extract_text(pdf_path):
    document = DocumentConverter().convert(pdf_path).document
    return document.export_to_markdown()


if __name__ == "__main__":
    print(extract_text(PDF_PATH))
