from pathlib import Path

from docling.document_converter import DocumentConverter

PDF_PATH = Path(__file__).parent.parent / "data" / "políticas_da_loja.pdf"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "generated" 


def convert_pdf(pdf_path):
    return DocumentConverter().convert(pdf_path).document


if __name__ == "__main__":
    document = convert_pdf(PDF_PATH)
    OUTPUT_DIR.mkdir(exist_ok=True)
    document.save_as_json(OUTPUT_DIR / "politicas_da_loja.json")
    document.save_as_markdown(OUTPUT_DIR / "politicas_da_loja.md")  
