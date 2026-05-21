from pathlib import Path

import pdfplumber

PDF_DIR = Path("data/pdfs")
TEXT_DIR = Path("data/text")
TEXT_DIR.mkdir(parents=True, exist_ok=True)


def extract_text_from_pdf(pdf_path: Path) -> str:
    text_parts = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text() or ""

            text_parts.append(f"\n--- Page {page_number} ---\n")
            text_parts.append(page_text)

    return "\n".join(text_parts)


def main():
    pdf_files = list(PDF_DIR.glob("*.pdf"))

    if not pdf_files:
        print("No PDFs found in data/pdfs.")
        return

    print(f"Found {len(pdf_files)} PDF files.")

    for pdf_path in pdf_files:
        print(f"Extracting text from: {pdf_path.name}")

        text = extract_text_from_pdf(pdf_path)

        output_path = TEXT_DIR / f"{pdf_path.stem}.txt"
        output_path.write_text(text, encoding="utf-8")

        print(f"Saved extracted text to: {output_path}")

    print("\nDone. Text files are in data/text.")


if __name__ == "__main__":
    main()