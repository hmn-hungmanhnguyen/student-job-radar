from pathlib import Path
from urllib.parse import urljoin
import csv
import json
import re

import feedparser
import requests
from bs4 import BeautifulSoup


ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT_DIR / "config" / "sources.json"

DATA_DIR = ROOT_DIR / "data"
PDF_DIR = DATA_DIR / "pdfs"
METADATA_FILE = DATA_DIR / "job_metadata.csv"

PDF_DIR.mkdir(parents=True, exist_ok=True)


def load_sources() -> list[dict]:
    with CONFIG_FILE.open("r", encoding="utf-8") as file:
        config = json.load(file)

    return [
        source for source in config.get("sources", [])
        if source.get("enabled", False)
    ]


def safe_filename(url: str) -> str:
    name = url.rstrip("/").split("/")[-1]
    name = re.sub(r"[^a-zA-Z0-9._-]", "_", name)
    return name or "job.pdf"


def find_pdf_links(entry, feed_url: str) -> list[str]:
    links = []

    entry_link = entry.get("link")
    if entry_link and entry_link.lower().endswith(".pdf"):
        links.append(entry_link)

    html = entry.get("summary", "") or entry.get("description", "")
    soup = BeautifulSoup(html, "html.parser")

    for a in soup.find_all("a", href=True):
        href = a["href"]
        full_url = urljoin(feed_url, href)
        if ".pdf" in full_url.lower():
            links.append(full_url)

    raw_urls = re.findall(r"https?://\S+?\.pdf", html)
    links.extend(raw_urls)

    return list(dict.fromkeys(links))


def download_pdf(url: str) -> Path:
    filename = safe_filename(url)
    path = PDF_DIR / filename

    if path.exists():
        print(f"Already downloaded: {path.name}")
        return path

    print(f"Downloading: {url}")
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    path.write_bytes(response.content)
    print(f"Saved to: {path}")
    return path


def write_metadata(rows: list[dict]) -> None:
    fieldnames = [
        "source_name",
        "rss_title",
        "source_url",
        "pdf_url",
        "published",
        "pdf_file",
        "text_file",
    ]

    with METADATA_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved metadata to: {METADATA_FILE}")


def main():
    sources = load_sources()
    metadata_rows = []

    for source in sources:
        source_name = source["name"]
        feed_url = source["url"]

        print("=" * 80)
        print(f"Reading source: {source_name}")
        print(f"Feed URL: {feed_url}")
        print("=" * 80)

        feed = feedparser.parse(feed_url)
        print(f"Found {len(feed.entries)} entries")

        for entry in feed.entries:
            rss_title = entry.get("title", "")
            source_url = entry.get("link", "")
            published = entry.get("published", "")

            print("\nJob:", rss_title)

            pdf_links = find_pdf_links(entry, feed_url)

            if not pdf_links:
                print("No PDF found.")
                continue

            for pdf_url in pdf_links:
                pdf_path = download_pdf(pdf_url)
                text_file = f"{pdf_path.stem}.txt"

                metadata_rows.append(
                    {
                        "source_name": source_name,
                        "rss_title": rss_title,
                        "source_url": source_url,
                        "pdf_url": pdf_url,
                        "published": published,
                        "pdf_file": pdf_path.name,
                        "text_file": text_file,
                    }
                )

    write_metadata(metadata_rows)


if __name__ == "__main__":
    main()