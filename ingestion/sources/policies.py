from pathlib import Path

from docling.chunking import HybridChunker
from docling.document_converter import DocumentConverter
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from transformers import AutoTokenizer

DATA_DIR = Path(__file__).parent.parent.parent / "data"  # sources/ -> ingestion/ -> project root
PDF_PATH = DATA_DIR / "políticas_da_loja.pdf"
OUTPUT_DIR = DATA_DIR / "generated"


def convert_pdf(pdf_path):
    return DocumentConverter().convert(pdf_path).document


def chunk_policies():
    document = convert_pdf(PDF_PATH)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    document.save_as_json(OUTPUT_DIR / "politicas_da_loja.json")  # full docling structure, for debugging
    document.save_as_markdown(OUTPUT_DIR / "politicas_da_loja.md")  # same content, for reviewing by eye

    tokenizer = HuggingFaceTokenizer(tokenizer=AutoTokenizer.from_pretrained("BAAI/bge-m3"), max_tokens=512)
    chunker = HybridChunker(tokenizer=tokenizer)

    chunks = []
    for chunk in chunker.chunk(document):
        section = " > ".join(chunk.meta.headings or [])
        if not section[:1].isdigit():
            continue  
        chunks.append({
            "section": section,
            "content": chunk.text,  
            "text": chunker.contextualize(chunk), 
        })
    return chunks


if __name__ == "__main__":
    for chunk in chunk_policies():
        print(chunk["section"])