from pathlib import Path
import csv
import re
from datetime import datetime, date


ROOT_DIR = Path(__file__).resolve().parent.parent

TEXT_DIR = ROOT_DIR / "data" / "text"
METADATA_FILE = ROOT_DIR / "data" / "job_metadata.csv"
OUTPUT_FILE = ROOT_DIR / "data" / "jobs.csv"


def read_text_file(path: Path) -> str:
    if not path.exists():
        return ""

    return path.read_text(encoding="utf-8", errors="replace")


def clean_text(text: str) -> str:
    replacements = {
        "\u00ad": "",
        "–": "-",
        "—": "-",
        "\t": " ",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # Remove debug page markers from extraction step
    text = re.sub(r"---\s*Page\s*\d+\s*---", " ", text, flags=re.IGNORECASE)

    # Collapse whitespace
    text = re.sub(r"[ ]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def extract_email(text: str) -> str:
    emails = re.findall(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        text
    )
    return emails[0] if emails else ""


def extract_deadline(text: str) -> str:
    patterns = [
        r"Bewerbungsfrist[:\s]*(\d{1,2}\.\d{1,2}\.\d{4})",
        r"bis zum\s*(\d{1,2}\.\d{1,2}\.\d{4})",
        r"bis\s*(\d{1,2}\.\d{1,2}\.\d{4})",
        r"spätestens\s*(\d{1,2}\.\d{1,2}\.\d{4})",
        r"Frist[:\s]*(\d{1,2}\.\d{1,2}\.\d{4})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)

    return ""


def parse_german_date(date_text: str):
    if not date_text:
        return None

    try:
        return datetime.strptime(date_text, "%d.%m.%Y").date()
    except ValueError:
        return None


def get_days_until_deadline(deadline: str):
    deadline_date = parse_german_date(deadline)

    if deadline_date is None:
        return ""

    return (deadline_date - date.today()).days


def get_opportunity_status(deadline: str) -> str:
    deadline_date = parse_german_date(deadline)

    if deadline_date is None:
        return "No deadline found"

    days_left = (deadline_date - date.today()).days

    if days_left < 0:
        return "Expired"
    if days_left == 0:
        return "Closing today"
    if days_left <= 3:
        return "Closing soon"

    return "Open"


def detect_job_type(text: str, rss_title: str) -> str:
    combined = f"{rss_title}\n{text}".lower()

    if "studentische hilfskraft" in combined or "shk" in combined:
        return "SHK"
    if "hiwi" in combined:
        return "HiWi"
    if "werkstudent" in combined or "werkstudentin" in combined:
        return "Werkstudent"
    if "praktikum" in combined or "internship" in combined:
        return "Internship"

    return ""


def guess_title(text: str, rss_title: str) -> str:
    if rss_title:
        return rss_title.strip()

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    lines = [line for line in lines if not line.lower().startswith("--- page")]

    for line in lines[:40]:
        lower = line.lower()
        if any(word in lower for word in ["studentische hilfskraft", "shk", "hiwi", "werkstudent"]):
            return line

    for line in lines[:20]:
        if len(line) > 10:
            return line

    return ""


def make_summary(text: str, max_length: int = 350) -> str:
    lines = []

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        if line.lower().startswith("--- page"):
            continue

        lines.append(line)

    one_line = " ".join(lines)
    one_line = re.sub(r"\s+", " ", one_line)

    return one_line[:max_length]


def make_public_note(deadline: str, email: str, text: str) -> str:
    notes = []

    if not text:
        notes.append("PDF text could not be extracted.")

    if not deadline:
        notes.append("No deadline detected; check original PDF.")

    if not email:
        notes.append("No email detected; check original PDF.")

    if not notes:
        return "Automatically extracted from PDF."

    return " ".join(notes)


def load_metadata() -> list[dict]:
    if not METADATA_FILE.exists():
        raise FileNotFoundError(
            f"Missing metadata file: {METADATA_FILE}. Run download_pdfs.py first."
        )

    with METADATA_FILE.open("r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))

def make_hyperlink(url: str, label: str) -> str:
    if not url:
        return ""

    safe_url = url.replace('"', '""')
    safe_label = label.replace('"', '""')

    return f'=HYPERLINK("{safe_url}", "{safe_label}")'

def parse_metadata_row(row: dict) -> dict:
    text_file = row.get("text_file", "")
    text_path = TEXT_DIR / text_file

    raw_text = read_text_file(text_path)
    text = clean_text(raw_text)

    rss_title = row.get("rss_title", "")
    deadline = extract_deadline(text)
    email = extract_email(text)

    return {
        "Source": row.get("source_name", ""),
        "Title": guess_title(text, rss_title),
        "Type": detect_job_type(text, rss_title),
        "Deadline": deadline,
        "Days Left": get_days_until_deadline(deadline),
        "Status": get_opportunity_status(deadline),
        "Contact": email,
        "Published": row.get("published", ""),
        "Source Page": make_hyperlink(row.get("source_page_url", ""), "Open source page"),
        "PDF": make_hyperlink(row.get("pdf_url", ""), "Open PDF"),
        "Note": make_public_note(deadline, email, text),
        "Summary": make_summary(text),
    }


def main():
    metadata_rows = load_metadata()

    if not metadata_rows:
        print("No metadata rows found.")
        return

    jobs = [parse_metadata_row(row) for row in metadata_rows]

    fieldnames = [
        "Source",
        "Title",
        "Type",
        "Deadline",
        "Days Left",
        "Status",
        "Contact",
        "Published",
        "Source Page",
        "PDF",
        "Note",
        "Summary",
    ]

    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(jobs)

    print(f"Parsed {len(jobs)} jobs.")
    print(f"Saved public job table to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()