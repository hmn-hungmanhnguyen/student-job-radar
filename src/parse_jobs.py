from pathlib import Path
import csv
import re
from datetime import datetime, date


TEXT_DIR = Path("data/text")
OUTPUT_FILE = Path("data/jobs.csv")


def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def clean_text(text: str) -> str:
    replacements = {
        "\u00ad": "",      # soft hyphen
        "–": "-",
        "—": "-",
        "\t": " ",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # Remove page markers created by extract_pdf_text.py
    text = re.sub(r"---\s*Page\s*\d+\s*---", " ", text, flags=re.IGNORECASE)

    # Collapse excessive whitespace
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


def make_public_note(deadline: str, email: str) -> str:
    notes = []

    if not deadline:
        notes.append("No deadline detected; check original PDF.")

    if not email:
        notes.append("No email detected; check original PDF.")

    if not notes:
        return "Automatically extracted from PDF."

    return " ".join(notes)


def guess_title(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    lines = [line for line in lines if not line.startswith("--- Page")]

    title_keywords = [
        "studentische hilfskraft",
        "studentische hilfskraft",
        "shk",
        "hiwi",
        "werkstudent",
        "werkstudentin",
    ]

    for line in lines[:40]:
        lower = line.lower()
        if any(keyword in lower for keyword in title_keywords):
            return line

    for line in lines[:20]:
        if len(line) > 10:
            return line

    return ""


def detect_job_type(text: str) -> str:
    lower = text.lower()

    if "studentische hilfskraft" in lower or "shk" in lower:
        return "SHK"
    if "hiwi" in lower:
        return "HiWi"
    if "werkstudent" in lower or "werkstudentin" in lower:
        return "Werkstudent"
    if "praktikum" in lower or "internship" in lower:
        return "Internship"

    return ""


def make_preview(text: str, max_length: int = 350) -> str:
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


def parse_file(path: Path) -> dict:
    raw_text = read_text_file(path)
    text = clean_text(raw_text)

    deadline = extract_deadline(text)
    email = extract_email(text)

    return {
        "title": guess_title(text),
        "job_type": detect_job_type(text),
        "deadline": deadline,
        "days_until_deadline": get_days_until_deadline(deadline),
        "opportunity_status": get_opportunity_status(deadline),
        "email": email,
        "source_file": path.name,
        "public_note": make_public_note(deadline, email),
        "summary": make_preview(text),
    }


def main():
    text_files = sorted(TEXT_DIR.glob("*.txt"))

    if not text_files:
        print("No text files found in data/text.")
        return

    jobs = [parse_file(path) for path in text_files]

    fieldnames = [
        "title",
        "job_type",
        "deadline",
        "days_until_deadline",
        "opportunity_status",
        "email",
        "source_file",
        "public_note",
        "preview",
    ]

    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(jobs)

    print(f"Parsed {len(jobs)} jobs.")
    print(f"Saved public job table to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()