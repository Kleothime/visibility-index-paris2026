import argparse
import datetime as dt
import sys

import snscrape.modules.twitter as sntwitter


def count_tweets(query: str, days: int = 1, limit: int | None = 500):
    since = (dt.datetime.utcnow() - dt.timedelta(days=days)).strftime('%Y-%m-%d')
    search_query = f'"{query}" since:{since} lang:fr -is:retweet'

    total = 0
    for i, _ in enumerate(sntwitter.TwitterSearchScraper(search_query).get_items(), 1):
        total = i
        if limit and i >= limit:
            break
    return total, search_query


def main():
    parser = argparse.ArgumentParser(description="Compte les tweets pour un mot-clé via snscrape")
    parser.add_argument("--query", required=True, help="Mot-clé à chercher")
    parser.add_argument("--days", type=int, default=1, help="Fenêtre glissante en jours (UTC)")
    parser.add_argument("--limit", type=int, default=500, help="Limite de tweets à parcourir (0 pour illimité)")
    args = parser.parse_args()

    limit = None if args.limit == 0 else args.limit
    try:
        total, q = count_tweets(args.query, args.days, limit)
    except Exception as err:
        print(f"Erreur lors du scraping: {err}")
        sys.exit(1)

    print(f"Requête: {q}")
    print(f"Tweets comptés: {total}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
