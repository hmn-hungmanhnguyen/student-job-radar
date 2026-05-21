import re
from pathlib import Path
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup

FEED_URL = "https://www.uni-due.de/stellenmarkt/shk_an_der_ude.rss"

DATA_DIR = Path("data")
PDF_DIR = DATA_DIR / "pdfs"
PDF_DIR.mkdir(parents=True, exist_ok=True)


def safe_filename(url: str) -> str:
    name = url.rstrip("/").split("/")[-1]
    name = re.sub(r"[^a-zA-Z0-9._-]", "_", name)
    return name or "job.pdf"


def find_pdf_links(entry) -> list[str]:
    links = []

    # Check direct entry link
    entry_link = entry.get("link")
    if entry_link and entry_link.lower().endswith(".pdf"):
        links.append(entry_link)

    # Check summary/description text
    html = entry.get("summary", "") or entry.get("description", "")
    soup = BeautifulSoup(html, "html.parser")

    for a in soup.find_all("a", href=True):
        href = a["href"]
        full_url = urljoin(FEED_URL, href)
        if ".pdf" in full_url.lower():
            links.append(full_url)

    # Some RSS summaries may contain raw PDF URLs as text
    raw_urls = re.findall(r"https?://\S+?\.pdf", html)
    links.extend(raw_urls)

    # Remove duplicates while keeping order
    return list(dict.fromkeys(links))


def download_pdf(url: str) -> Path:
    filename = safe_filename(url)
    path = PDF_DIR / filename

    if path.exists():
        print(f"Already downloaded: {path}")
        return path

    print(f"Downloading: {url}")
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    path.write_bytes(response.content)
    print(f"Saved to: {path}")
    return path


def main():
    feed = feedparser.parse(FEED_URL)

    print(f"Found {len(feed.entries)} RSS entries")

    for entry in feed.entries:
        print("\n" + "=" * 80)
        print("Job:", entry.get("title", "No title"))

        pdf_links = find_pdf_links(entry)

        if not pdf_links:
            print("No PDF found.")
            continue

        for pdf_url in pdf_links:
            download_pdf(pdf_url)


if __name__ == "__main__":
    main()