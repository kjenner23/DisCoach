from pathlib import Path
import requests

API_URL = "http://127.0.0.1:8000/process"
# Adapte le nom si ton fichier s'appelle autrement
INPUT_PATH = Path("..") / "data" / "Scraped output.txt"


def load_articles() -> list[str]:
    raw = INPUT_PATH.read_text(encoding="utf-8", errors="replace")

    # on coupe sur le séparateur, puis on remet "===ARTICLE===\n" devant chaque bloc
    chunks = [c.strip() for c in raw.split("===ARTICLE===") if c.strip()]
    articles = ["===ARTICLE===\n" + c for c in chunks]
    return articles

def main():
    articles = load_articles()
    print(f"Found {len(articles)} article(s) in {INPUT_PATH}")

    for idx, article in enumerate(articles, start=1):
        article_id = f"article-{idx:04d}"
        payload = {
            "article_id": article_id,
            "text": article,
        }
        resp = requests.post(API_URL, json=payload)
        try:
            data = resp.json()
        except Exception:
            data = {"raw_response": resp.text}

        print(f"[{idx}] status={resp.status_code}, api_status={data.get('status')}")

if __name__ == "__main__":
    main()
