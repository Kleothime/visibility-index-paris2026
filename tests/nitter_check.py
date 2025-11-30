"""
Test de scraping Twitter via Nitter (frontend alternatif)
"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import sys

# Instances Nitter publiques (certaines peuvent être down)
NITTER_INSTANCES = [
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
    "https://nitter.woodland.cafe",
]


def count_tweets_nitter(query: str, instance: str = None) -> dict:
    """Compte approximatif des tweets via Nitter"""

    instances_to_try = [instance] if instance else NITTER_INSTANCES

    for inst in instances_to_try:
        try:
            search_url = f"{inst}/search?f=tweets&q={quote_plus(query)}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            response = requests.get(search_url, headers=headers, timeout=15, verify=True)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Compter les tweets sur la première page
                tweets = soup.find_all('div', class_='timeline-item')

                # Extraire quelques infos
                tweet_data = []
                for tweet in tweets[:10]:
                    content = tweet.find('div', class_='tweet-content')
                    if content:
                        tweet_data.append(content.get_text(strip=True)[:100])

                return {
                    "success": True,
                    "instance": inst,
                    "count_page1": len(tweets),
                    "sample_tweets": tweet_data,
                    "search_url": search_url
                }

        except Exception as e:
            print(f"Instance {inst} failed: {e}")
            continue

    return {"success": False, "error": "Toutes les instances Nitter ont échoué"}


def main():
    queries = [
        "Sarah Knafo",
        "Rachida Dati",
        "Emmanuel Grégoire",
        "Ian Brossat",
        "David Belliard"
    ]

    print("=" * 60)
    print("TEST SCRAPING TWITTER VIA NITTER")
    print("=" * 60)

    for query in queries:
        print(f"\n>> {query}")
        result = count_tweets_nitter(query)

        if result["success"]:
            print(f"   Instance: {result['instance']}")
            print(f"   Tweets (page 1): {result['count_page1']}")
            print(f"   URL: {result['search_url']}")
        else:
            print(f"   ERREUR: {result.get('error', 'Unknown')}")


if __name__ == "__main__":
    main()
