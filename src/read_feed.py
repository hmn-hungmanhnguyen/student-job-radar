import feedparser

FEED_URL = "https://www.uni-due.de/stellenmarkt/shk_an_der_ude.rss"

def main():
    feed = feedparser.parse(FEED_URL)

    print("Feed title:", feed.feed.get("title", "No title"))
    print("Number of entries:", len(feed.entries))
    print("=" * 80)

    for i, entry in enumerate(feed.entries, start=1):
        print(f"Job #{i}")
        print("Title:", entry.get("title", "No title"))
        print("Link:", entry.get("link", "No link"))
        print("Published:", entry.get("published", "No date"))

        summary = entry.get("summary", "")
        print("Summary:", summary[:300].replace("\n", " "))

        print("-" * 80)

if __name__ == "__main__":
    main()