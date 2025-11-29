"""
Baromètre de visibilité médiatique - Municipales Paris 2026
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import requests
import json
import re
import math
from typing import Optional, Dict, List
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET

# =============================================================================
# CONFIG
# =============================================================================

st.set_page_config(
    page_title="Baromètre Visibilité Médiatique - Paris 2026",
    page_icon="BVM",
    layout="wide"
)

# Clé API YouTube (utilisée automatiquement)
YOUTUBE_API_KEY = "AIzaSyCu27YMexJiCrzagkCnawkECG7WA1_wzDI"

# =============================================================================
# CANDIDATS
# =============================================================================

CANDIDATES = {
    "rachida_dati": {
        "name": "Rachida Dati",
        "party": "LR / Renaissance",
        "role": "Ministre de la Culture",
        "color": "#0066CC",
        "wikipedia": "Rachida_Dati",
        "search_terms": ["Rachida Dati", "Dati ministre", "Dati Paris"],
    },
    "emmanuel_gregoire": {
        "name": "Emmanuel Grégoire",
        "party": "PS",
        "role": "1er adjoint Mairie de Paris",
        "color": "#FF69B4",
        "wikipedia": "Emmanuel_Grégoire",
        "search_terms": ["Emmanuel Grégoire", "Grégoire adjoint Paris", "Grégoire PS"],
    },
    "pierre_yves_bournazel": {
        "name": "Pierre-Yves Bournazel",
        "party": "Horizons",
        "role": "Conseiller de Paris",
        "color": "#FF6B35",
        "wikipedia": "Pierre-Yves_Bournazel",
        "search_terms": ["Pierre-Yves Bournazel", "Bournazel Paris", "Bournazel Horizons"],
    },
    "ian_brossat": {
        "name": "Ian Brossat",
        "party": "PCF",
        "role": "Sénateur de Paris",
        "color": "#DD0000",
        "wikipedia": "Ian_Brossat",
        "search_terms": ["Ian Brossat", "Brossat PCF", "Brossat Paris"],
    },
    "david_belliard": {
        "name": "David Belliard",
        "party": "EELV",
        "role": "Adjoint transports",
        "color": "#00A86B",
        "wikipedia": "David_Belliard",
        "search_terms": ["David Belliard", "Belliard EELV", "Belliard Paris"],
    },
    "sophia_chikirou": {
        "name": "Sophia Chikirou",
        "party": "LFI",
        "role": "Députée de Paris",
        "color": "#C9462C",
        "wikipedia": "Sophia_Chikirou",
        "search_terms": ["Sophia Chikirou", "Chikirou LFI", "Chikirou Paris"],
    },
    "thierry_mariani": {
        "name": "Thierry Mariani",
        "party": "RN",
        "role": "Député européen",
        "color": "#0D2C54",
        "wikipedia": "Thierry_Mariani",
        "search_terms": ["Thierry Mariani", "Mariani RN"],
    }
}

# =============================================================================
# SONDAGES OFFICIELS - Instituts reconnus uniquement
# =============================================================================

SONDAGES = [
    {
        "date": "2024-11-04",
        "institut": "IFOP-Fiducial",
        "commanditaire": "Le Figaro / Sud Radio",
        "echantillon": 1037,
        "methode": "Questionnaire auto-administré en ligne",
        "hypothese": "Hypothèse avec Pierre-Yves Bournazel candidat",
        "url": "https://www.ifop.com/publication/intentions-de-vote-municipales-paris-2026/",
        "scores": {
            "Rachida Dati": 27,
            "Emmanuel Grégoire": 18,
            "David Belliard": 17,
            "Pierre-Yves Bournazel": 15,
            "Sophia Chikirou": 12,
            "Thierry Mariani": 7,
            "Ian Brossat": 4,
        }
    },
    {
        "date": "2024-06-21",
        "institut": "ELABE",
        "commanditaire": "La Tribune Dimanche / BFMTV",
        "echantillon": 1097,
        "methode": "Questionnaire auto-administré en ligne",
        "hypothese": "Avec P-Y Bournazel, E. Grégoire candidat PS",
        "url": "https://elabe.fr/municipales-paris-2026/",
        "scores": {
            "Rachida Dati": 28,
            "David Belliard": 22,
            "Emmanuel Grégoire": 19,
            "Sophia Chikirou": 14,
            "Pierre-Yves Bournazel": 8,
            "Thierry Mariani": 7,
        }
    },
]

def get_latest_sondage():
    """Retourne le sondage le plus récent"""
    if not SONDAGES:
        return None
    return max(SONDAGES, key=lambda x: x["date"])

def get_candidate_sondage_score(candidate_name: str) -> Optional[int]:
    """Retourne le score du candidat dans le dernier sondage"""
    latest = get_latest_sondage()
    if latest and candidate_name in latest["scores"]:
        return latest["scores"][candidate_name]
    return None

# Médias TV et Radio français principaux
MEDIAS_TV_RADIO = [
    "BFM", "BFMTV", "LCI", "CNews", "TF1", "France 2", "France 3",
    "France Inter", "RTL", "Europe 1", "RMC", "France Info", "France 24",
    "Arte", "Public Sénat", "LCP", "C8", "TMC", "Sud Radio"
]

# =============================================================================
# PERSISTANCE CLOUD (JSONBin.io)
# =============================================================================

JSONBIN_API_URL = "https://api.jsonbin.io/v3/b"

def load_history_cloud(bin_id: str, api_key: str) -> List[Dict]:
    """Charge l'historique depuis JSONBin.io"""
    if not bin_id or not api_key:
        return []

    try:
        headers = {"X-Master-Key": api_key}
        response = requests.get(
            f"{JSONBIN_API_URL}/{bin_id}/latest",
            headers=headers,
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            record = data.get("record", [])
            if isinstance(record, list):
                return record
            return []
    except Exception as e:
        pass

    return []

def save_history_cloud(history: List[Dict], bin_id: str, api_key: str) -> bool:
    """Sauvegarde l'historique sur JSONBin.io"""
    if not bin_id or not api_key:
        return False

    try:
        cutoff = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
        history = [h for h in history if h.get("date", "") >= cutoff]

        headers = {
            "X-Master-Key": api_key,
            "Content-Type": "application/json"
        }
        response = requests.put(
            f"{JSONBIN_API_URL}/{bin_id}",
            headers=headers,
            json=history,
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        return False

def get_cloud_config():
    """Récupère la config cloud depuis secrets ou session"""
    bin_id = None
    api_key = None

    try:
        bin_id = st.secrets.get("JSONBIN_BIN_ID", None)
        api_key = st.secrets.get("JSONBIN_API_KEY", None)
    except:
        pass

    if not bin_id:
        bin_id = st.session_state.get("jsonbin_bin_id", "")
    if not api_key:
        api_key = st.session_state.get("jsonbin_api_key", "")

    return bin_id, api_key

def is_cloud_configured() -> bool:
    """Vérifie si la persistance cloud est configurée"""
    bin_id, api_key = get_cloud_config()
    return bool(bin_id and api_key)

# =============================================================================
# HISTORIQUE (avec fallback local)
# =============================================================================

HISTORY_FILE = "visibility_history.json"

def load_history() -> List[Dict]:
    """Charge l'historique (cloud prioritaire, sinon local)"""
    bin_id, api_key = get_cloud_config()

    if bin_id and api_key:
        cloud_history = load_history_cloud(bin_id, api_key)
        if cloud_history:
            return cloud_history

    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_history(history: List[Dict]) -> bool:
    """Sauvegarde l'historique (cloud + local)"""
    bin_id, api_key = get_cloud_config()

    cloud_ok = False
    if bin_id and api_key:
        cloud_ok = save_history_cloud(history, bin_id, api_key)

    try:
        cutoff = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
        history = [h for h in history if h.get("date", "") >= cutoff]
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except:
        pass

    return cloud_ok

def add_to_history(data: Dict, period_label: str) -> List[Dict]:
    """Ajoute les données actuelles à l'historique"""
    history = load_history()

    today = datetime.now().strftime("%Y-%m-%d")

    history = [h for h in history if not (h.get("date") == today and h.get("period") == period_label)]

    entry = {
        "date": today,
        "timestamp": datetime.now().isoformat(),
        "period": period_label,
        "scores": {}
    }

    for cid, d in data.items():
        entry["scores"][d["info"]["name"]] = {
            "total": d["score"]["total"],
            "trends": d["trends_score"],
            "press": d["press"]["count"],
            "wiki": d["wikipedia"]["views"],
            "youtube": d["youtube"].get("total_views", 0) if d["youtube"].get("available") else 0
        }

    history.append(entry)
    save_history(history)

    return history

def get_historical_comparison(candidate_name: str, current_score: float) -> Dict:
    """Compare le score actuel avec l'historique"""
    history = load_history()

    if not history:
        return {"available": False}

    past_scores = []
    for entry in history:
        if candidate_name in entry.get("scores", {}):
            past_scores.append({
                "date": entry["date"],
                "score": entry["scores"][candidate_name]["total"]
            })

    if not past_scores:
        return {"available": False}

    past_scores.sort(key=lambda x: x["date"])

    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    week_score = None
    month_score = None

    for ps in past_scores:
        if ps["date"] <= week_ago:
            week_score = ps["score"]
        if ps["date"] <= month_ago:
            month_score = ps["score"]

    return {
        "available": True,
        "history": past_scores[-30:],
        "week_change": round(current_score - week_score, 1) if week_score else None,
        "month_change": round(current_score - month_score, 1) if month_score else None
    }

# =============================================================================
# UTILITAIRES DE FORMATAGE
# =============================================================================

def format_number(n: int) -> str:
    """Formate un nombre avec des espaces entre les milliers (format français)"""
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M".replace(".", ",")
    elif n >= 1_000:
        return f"{n:,}".replace(",", " ")
    return str(n)

def format_number_short(n: int) -> str:
    """Formate un nombre en version courte pour graphiques"""
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M".replace(".", ",")
    elif n >= 1_000:
        return f"{n/1_000:.0f}k".replace(".", ",")
    return str(n)

# =============================================================================
# FONCTIONS DE COLLECTE
# =============================================================================

@st.cache_data(ttl=1800, show_spinner=False)
def get_wikipedia_views(page_title: str, start_date: date, end_date: date) -> Dict:
    """Récupère les statistiques de vues Wikipedia"""
    try:
        days_in_period = (end_date - start_date).days + 1
        ref_end = start_date - timedelta(days=1)
        ref_start = ref_end - timedelta(days=days_in_period - 1)

        url = (
            f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
            f"fr.wikipedia/all-access/user/{quote_plus(page_title)}/daily/"
            f"{ref_start.strftime('%Y%m%d')}/{end_date.strftime('%Y%m%d')}"
        )

        response = requests.get(url, headers={"User-Agent": "VisibilityIndex/8.0"}, timeout=15)

        if response.status_code != 200:
            return {"views": 0, "variation": 0, "daily": {}, "avg_daily": 0,
                    "ref_views": 0, "ref_avg": 0, "error": f"Erreur HTTP {response.status_code}"}

        items = response.json().get("items", [])

        period_views = 0
        reference_views = 0
        daily = {}

        for item in items:
            ts = item.get("timestamp", "")[:8]
            views = item.get("views", 0)

            try:
                item_date = datetime.strptime(ts, "%Y%m%d").date()

                if start_date <= item_date <= end_date:
                    period_views += views
                    daily[item_date.strftime("%Y-%m-%d")] = views
                elif ref_start <= item_date <= ref_end:
                    reference_views += views
            except:
                continue

        avg_period = period_views / max(days_in_period, 1)
        avg_ref = reference_views / max(days_in_period, 1)

        variation = 0
        if avg_ref > 0:
            variation = ((avg_period - avg_ref) / avg_ref) * 100

        return {
            "views": period_views,
            "variation": round(variation, 1),
            "daily": daily,
            "avg_daily": round(avg_period, 1),
            "ref_views": reference_views,
            "ref_avg": round(avg_ref, 1),
            "days_compared": days_in_period,
            "error": None
        }

    except Exception as e:
        return {"views": 0, "variation": 0, "daily": {}, "avg_daily": 0,
                "ref_views": 0, "ref_avg": 0, "error": str(e)[:50]}


@st.cache_data(ttl=1800, show_spinner=False)
def get_gdelt_articles(search_term: str, start_date: date, end_date: date) -> List[Dict]:
    """Récupère les articles de presse via GDELT"""
    articles = []

    try:
        url = "https://api.gdeltproject.org/api/v2/doc/doc"
        params = {
            "query": f'"{search_term}"',
            "mode": "ArtList",
            "format": "json",
            "maxrecords": 250,
            "startdatetime": start_date.strftime("%Y%m%d000000"),
            "enddatetime": end_date.strftime("%Y%m%d235959"),
            "sourcelang": "french"
        }

        response = requests.get(url, params=params, timeout=30)

        if response.status_code == 200 and response.text.strip():
            data = json.loads(response.text)
            for art in data.get("articles", []):
                articles.append({
                    "title": art.get("title", ""),
                    "url": art.get("url", ""),
                    "domain": art.get("domain", ""),
                    "date": art.get("seendate", "")[:10] if art.get("seendate") else "",
                    "source": "GDELT"
                })
    except:
        pass

    return articles


@st.cache_data(ttl=1800, show_spinner=False)
def get_google_news_articles(search_term: str) -> List[Dict]:
    """Récupère les articles via Google News RSS"""
    articles = []

    try:
        url = f"https://news.google.com/rss/search?q={quote_plus(search_term)}&hl=fr&gl=FR&ceid=FR:fr"
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)

        if response.status_code == 200:
            root = ET.fromstring(response.content)

            for item in root.findall(".//item"):
                title = item.find("title")
                link = item.find("link")
                pubdate = item.find("pubDate")
                source = item.find("source")

                date_str = ""
                if pubdate is not None and pubdate.text:
                    try:
                        dt = datetime.strptime(pubdate.text[:25], "%a, %d %b %Y %H:%M:%S")
                        date_str = dt.strftime("%Y-%m-%d")
                    except:
                        pass

                articles.append({
                    "title": title.text if title is not None else "",
                    "url": link.text if link is not None else "",
                    "domain": source.text if source is not None else "",
                    "date": date_str,
                    "source": "Google News"
                })
    except:
        pass

    return articles


def get_all_press_coverage(candidate_name: str, search_terms: List[str], start_date: date, end_date: date) -> Dict:
    """Récupère tous les articles pour un candidat avec déduplication"""
    all_articles = []
    seen_urls = set()

    for term in search_terms:
        gdelt_arts = get_gdelt_articles(term, start_date, end_date)
        for art in gdelt_arts:
            if art["url"] not in seen_urls:
                seen_urls.add(art["url"])
                all_articles.append(art)

        gnews_arts = get_google_news_articles(term)
        for art in gnews_arts:
            if art["url"] not in seen_urls:
                seen_urls.add(art["url"])
                all_articles.append(art)

    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    date_filtered = []
    for art in all_articles:
        art_date = art.get("date", "")
        if art_date and start_str <= art_date <= end_str:
            date_filtered.append(art)

    name_parts = candidate_name.lower().split()
    last_name = name_parts[-1] if name_parts else ""

    filtered = []
    for art in date_filtered:
        title_lower = art["title"].lower()
        if last_name and last_name in title_lower:
            filtered.append(art)

    seen_titles = set()
    unique = []
    for art in filtered:
        title_norm = re.sub(r'[^\w\s]', '', art["title"].lower())[:60]
        if title_norm and title_norm not in seen_titles:
            seen_titles.add(title_norm)
            unique.append(art)

    unique.sort(key=lambda x: x.get("date", ""), reverse=True)
    domains = set(art["domain"] for art in unique if art["domain"])

    return {
        "articles": unique,
        "count": len(unique),
        "domains": len(domains),
        "raw_count": len(all_articles),
        "date_filtered_count": len(date_filtered)
    }


@st.cache_data(ttl=7200, show_spinner=False)
def get_google_trends(keywords: List[str], start_date: date, end_date: date) -> Dict:
    """Récupère les données Google Trends avec fiabilité améliorée"""
    try:
        from pytrends.request import TrendReq
        import time
        import random

        if not keywords:
            return {"success": False, "scores": {}, "errors": ["Aucun mot-clé fourni"]}

        timeframe = f"{start_date.strftime('%Y-%m-%d')} {end_date.strftime('%Y-%m-%d')}"
        scores = {}
        errors = []

        keywords_limited = keywords[:5]

        max_retries = 3
        for attempt in range(max_retries):
            try:
                time.sleep(2 + random.uniform(0, 2))
                pytrends = TrendReq(hl="fr-FR", tz=60)
                pytrends.build_payload(keywords_limited, timeframe=timeframe, geo="FR")
                time.sleep(1 + random.uniform(0, 1))
                df = pytrends.interest_over_time()

                if df is not None and not df.empty:
                    if "isPartial" in df.columns:
                        df = df.drop(columns=["isPartial"])

                    for kw in keywords_limited:
                        if kw in df.columns:
                            scores[kw] = round(float(df[kw].mean()), 1)
                        else:
                            scores[kw] = 0.0
                    break
                else:
                    if attempt < max_retries - 1:
                        time.sleep(5 * (attempt + 1))
                    else:
                        errors.append("Données vides retournées par Google Trends")

            except Exception as e:
                err_str = str(e)
                if "429" in err_str:
                    if attempt < max_retries - 1:
                        time.sleep(10 * (attempt + 1) + random.uniform(0, 5))
                    else:
                        errors.append("Limite de requêtes Google atteinte (429)")
                else:
                    errors.append(f"Erreur: {err_str[:50]}")
                    break

        if len(keywords) > 5 and scores:
            avg_score = sum(scores.values()) / len(scores) if scores else 0
            for kw in keywords[5:]:
                scores[kw] = round(avg_score * 0.5, 1)

        for kw in keywords:
            if kw not in scores:
                scores[kw] = 0.0

        return {
            "success": any(v > 0 for v in scores.values()),
            "scores": scores,
            "errors": errors if errors else None
        }

    except ImportError:
        return {"success": False, "scores": {kw: 0.0 for kw in keywords}, "error": "Module pytrends non installé"}
    except Exception as e:
        return {"success": False, "scores": {kw: 0.0 for kw in keywords}, "error": str(e)[:100]}


def _is_short(duration: str) -> bool:
    """Détermine si une vidéo est un YouTube Short (< 60 secondes)"""
    if not duration:
        return False
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if not match:
        return False
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return (hours * 3600 + minutes * 60 + seconds) < 60


@st.cache_data(ttl=1800, show_spinner=False)
def get_youtube_data(search_term: str, api_key: str, start_date: date, end_date: date) -> Dict:
    """Récupère les données YouTube via l'API officielle"""
    if not api_key or not api_key.strip():
        return {"available": False, "videos": [], "total_views": 0, "error": "Clé API manquante"}

    search_url = "https://www.googleapis.com/youtube/v3/search"
    all_videos = []
    seen_ids = set()

    published_after = start_date.strftime("%Y-%m-%dT00:00:00Z")
    published_before = (end_date + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")

    params = {
        "part": "snippet",
        "q": search_term,
        "type": "video",
        "order": "relevance",
        "maxResults": 50,
        "regionCode": "FR",
        "relevanceLanguage": "fr",
        "publishedAfter": published_after,
        "publishedBefore": published_before,
        "key": api_key
    }

    error_msg = None

    try:
        response = requests.get(search_url, params=params, timeout=15)

        if response.status_code == 200:
            for item in response.json().get("items", []):
                vid_id = item.get("id", {}).get("videoId", "")
                if vid_id and vid_id not in seen_ids:
                    seen_ids.add(vid_id)
                    all_videos.append({
                        "id": vid_id,
                        "title": item.get("snippet", {}).get("title", ""),
                        "channel": item.get("snippet", {}).get("channelTitle", ""),
                        "published": item.get("snippet", {}).get("publishedAt", "")[:10]
                    })
        else:
            try:
                err_data = response.json()
                error_msg = err_data.get("error", {}).get("message", f"Erreur HTTP {response.status_code}")
            except:
                error_msg = f"Erreur HTTP {response.status_code}"

    except Exception as e:
        error_msg = str(e)[:50]

    if error_msg and not all_videos:
        return {"available": False, "videos": [], "total_views": 0, "error": error_msg}

    if not all_videos:
        return {"available": False, "videos": [], "total_views": 0, "error": "Aucune vidéo trouvée"}

    name_parts = search_term.lower().split()
    filtered_videos = []
    video_ids = []

    for v in all_videos:
        title_lower = v["title"].lower()
        if any(part in title_lower for part in name_parts if len(part) >= 3):
            video_ids.append(v["id"])
            filtered_videos.append({
                "id": v["id"],
                "title": v["title"],
                "channel": v["channel"],
                "published": v["published"],
                "url": f"https://www.youtube.com/watch?v={v['id']}"
            })

    if not filtered_videos:
        return {"available": False, "videos": [], "total_views": 0, "error": "Aucune vidéo pertinente"}

    total_views = 0
    if video_ids:
        try:
            stats_url = "https://www.googleapis.com/youtube/v3/videos"
            stats_params = {
                "part": "statistics,contentDetails",
                "id": ",".join(video_ids[:50]),
                "key": api_key
            }

            stats_response = requests.get(stats_url, params=stats_params, timeout=10)

            if stats_response.status_code == 200:
                stats_map = {item["id"]: item for item in stats_response.json().get("items", [])}

                for v in filtered_videos:
                    if v["id"] in stats_map:
                        item = stats_map[v["id"]]
                        views = int(item.get("statistics", {}).get("viewCount", 0))
                        duration = item.get("contentDetails", {}).get("duration", "")
                        v["views"] = views
                        v["duration"] = duration
                        v["is_short"] = _is_short(duration)
                        total_views += views
        except:
            pass

    filtered_videos.sort(key=lambda x: x.get("views", 0), reverse=True)

    return {
        "available": True,
        "videos": filtered_videos,
        "total_views": total_views,
        "count": len(filtered_videos),
        "shorts_count": sum(1 for v in filtered_videos if v.get("is_short", False)),
        "long_count": sum(1 for v in filtered_videos if not v.get("is_short", False))
    }


@st.cache_data(ttl=1800, show_spinner=False)
def get_tv_radio_mentions(candidate_name: str, start_date: date, end_date: date) -> Dict:
    """Recherche les mentions TV/Radio via Google News avec détails complets"""
    mentions = []
    media_counts = {}

    last_name = candidate_name.split()[-1].lower()
    media_query = " OR ".join(MEDIAS_TV_RADIO[:6])
    search_query = f"{candidate_name} ({media_query})"

    try:
        rss_url = f"https://news.google.com/rss/search?q={quote_plus(search_query)}&hl=fr&gl=FR&ceid=FR:fr"
        response = requests.get(rss_url, timeout=15)

        if response.status_code == 200:
            root = ET.fromstring(response.content)

            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")

            for item in root.findall(".//item"):
                title = item.findtext("title", "")
                source = item.findtext("source", "")
                link = item.findtext("link", "")
                pub_date_raw = item.findtext("pubDate", "")

                art_date = ""
                if pub_date_raw:
                    try:
                        from email.utils import parsedate_to_datetime
                        dt = parsedate_to_datetime(pub_date_raw)
                        art_date = dt.strftime("%Y-%m-%d")
                    except:
                        pass

                if art_date and not (start_str <= art_date <= end_str):
                    continue

                if last_name not in title.lower():
                    continue

                detected_media = None
                for media in MEDIAS_TV_RADIO:
                    if media.lower() in source.lower() or media.lower() in title.lower():
                        detected_media = media
                        break

                if detected_media:
                    mentions.append({
                        "title": title,
                        "source": source,
                        "media": detected_media,
                        "date": art_date,
                        "url": link
                    })
                    media_counts[detected_media] = media_counts.get(detected_media, 0) + 1
    except:
        pass

    return {
        "count": len(mentions),
        "mentions": mentions,
        "media_counts": media_counts,
        "top_media": sorted(media_counts.items(), key=lambda x: x[1], reverse=True)
    }


# =============================================================================
# CALCUL DU SCORE
# =============================================================================

def calculate_score(wiki_views: int, press_count: int, press_domains: int,
                    trends_score: float, youtube_views: int, youtube_available: bool) -> Dict:
    """Calcule le score de visibilité
    Pondération: Presse 40%, Trends 35%, Wikipedia 15%, YouTube 10%
    """

    wiki_score = min((math.log10(wiki_views) / 4.7) * 100, 100) if wiki_views > 0 else 0

    press_base = min((press_count / 50) * 80, 80)
    diversity_bonus = min((press_domains / 20) * 20, 20)
    press_score = min(press_base + diversity_bonus, 100)

    trends_norm = min(max(trends_score, 0), 100)

    yt_score = 0
    if youtube_available and youtube_views > 0:
        yt_score = min((math.log10(youtube_views) / 6) * 100, 100)

    total = trends_norm * 0.35 + press_score * 0.40 + wiki_score * 0.15 + yt_score * 0.10
    total = min(max(total, 0), 100)

    return {
        "total": round(total, 1),
        "trends": round(trends_norm, 1),
        "press": round(press_score, 1),
        "wiki": round(wiki_score, 1),
        "youtube": round(yt_score, 1),
        "contrib_trends": round(trends_norm * 0.35, 1),
        "contrib_press": round(press_score * 0.40, 1),
        "contrib_wiki": round(wiki_score * 0.15, 1),
        "contrib_youtube": round(yt_score * 0.10, 1),
    }


# =============================================================================
# COLLECTE PRINCIPALE
# =============================================================================

def collect_data(candidate_ids: List[str], start_date: date, end_date: date, youtube_key: Optional[str]) -> Dict:
    """Collecte toutes les données pour les candidats sélectionnés"""
    results = {}

    progress = st.progress(0)
    status = st.empty()

    status.text("Chargement des données Google Trends...")
    names = [CANDIDATES[cid]["name"] for cid in candidate_ids]
    trends = get_google_trends(names, start_date, end_date)

    if not trends["success"]:
        err = trends.get("error") or trends.get("errors")
        if err:
            st.warning(f"Attention : Google Trends indisponible - {err}")

    progress.progress(0.1)

    total = len(candidate_ids)

    for i, cid in enumerate(candidate_ids):
        c = CANDIDATES[cid]
        name = c["name"]

        status.text(f"Analyse de {name}...")

        wiki = get_wikipedia_views(c["wikipedia"], start_date, end_date)
        press = get_all_press_coverage(name, c["search_terms"], start_date, end_date)
        tv_radio = get_tv_radio_mentions(name, start_date, end_date)

        yt_start = date.today() - timedelta(days=30)
        yt_end = date.today()

        if youtube_key:
            youtube = get_youtube_data(name, youtube_key, yt_start, yt_end)
        else:
            youtube = {"available": False, "total_views": 0, "videos": []}

        trends_score = trends["scores"].get(name, 0)

        score = calculate_score(
            wiki_views=wiki["views"],
            press_count=press["count"],
            press_domains=press["domains"],
            trends_score=trends_score,
            youtube_views=youtube.get("total_views", 0),
            youtube_available=youtube.get("available", False)
        )

        results[cid] = {
            "info": c,
            "wikipedia": wiki,
            "press": press,
            "tv_radio": tv_radio,
            "youtube": youtube,
            "trends_score": trends_score,
            "trends_success": trends["success"],
            "trends_error": trends.get("error") or trends.get("errors"),
            "score": score
        }

        progress.progress((i + 1) / total)

    progress.empty()
    status.empty()

    return results


# =============================================================================
# INTERFACE PRINCIPALE
# =============================================================================

def main():
    st.markdown("# Baromètre de visibilité médiatique")
    st.markdown("**Élections municipales Paris 2026**")

    with st.sidebar:
        st.markdown("## Configuration")

        # Période
        st.markdown("### Période d'analyse")

        period_type = st.radio("Type de période", ["Prédéfinie", "Personnalisée"], horizontal=True)

        if period_type == "Prédéfinie":
            period_options = {"7 jours": 7, "14 jours": 14, "30 jours": 30}
            period_label = st.selectbox("Durée", list(period_options.keys()))
            period_days = period_options[period_label]
            end_date = date.today()
            start_date = end_date - timedelta(days=period_days - 1)
        else:
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Début", value=date.today() - timedelta(days=7))
            with col2:
                end_date = st.date_input("Fin", value=date.today(), max_value=date.today())

            if start_date > end_date:
                st.error("La date de début doit être antérieure à la date de fin")
                return

        st.caption(f"{start_date.strftime('%d/%m/%Y')} → {end_date.strftime('%d/%m/%Y')}")

        # Candidats
        st.markdown("### Candidats")
        selected = st.multiselect(
            "Sélection",
            list(CANDIDATES.keys()),
            default=list(CANDIDATES.keys()),
            format_func=lambda x: CANDIDATES[x]["name"]
        )

        # Persistance cloud
        st.markdown("### Persistance historique")

        cloud_configured = is_cloud_configured()
        if cloud_configured:
            st.success("Sauvegarde cloud activée")
        else:
            with st.expander("Configurer la sauvegarde cloud"):
                st.markdown("""
                **Pour conserver l'historique :**
                1. Créer un compte sur [jsonbin.io](https://jsonbin.io)
                2. Copier la clé principale (Master Key)
                3. Créer un bin avec contenu initial : `[]`
                4. Copier l'identifiant du bin
                """)

                bin_id = st.text_input("ID du bin", value=st.session_state.get("jsonbin_bin_id", ""))
                api_key = st.text_input("Clé principale", value=st.session_state.get("jsonbin_api_key", ""), type="password")

                if bin_id:
                    st.session_state["jsonbin_bin_id"] = bin_id
                if api_key:
                    st.session_state["jsonbin_api_key"] = api_key

                if bin_id and api_key:
                    if st.button("Tester la connexion"):
                        test = load_history_cloud(bin_id, api_key)
                        if test is not None:
                            st.success(f"Connexion réussie ({len(test)} entrées)")
                        else:
                            st.error("Échec de la connexion")

        st.markdown("---")

        if st.button("Rafraîchir les données", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")
        st.markdown("### Pondération du score")
        st.caption("Presse 40% · Trends 35% · Wikipedia 15% · YouTube 10%")

    if not selected:
        st.warning("Veuillez sélectionner au moins un candidat")
        return

    data = collect_data(selected, start_date, end_date, YOUTUBE_API_KEY)
    sorted_data = sorted(data.items(), key=lambda x: x[1]["score"]["total"], reverse=True)

    # === CLASSEMENT ===
    st.markdown("---")
    st.markdown("## Classement général")

    youtube_enabled = any(d["youtube"].get("available", False) for _, d in sorted_data)

    rows = []
    for rank, (cid, d) in enumerate(sorted_data, 1):
        row = {
            "Rang": rank,
            "Candidat": d["info"]["name"],
            "Parti": d["info"]["party"],
            "Score": d["score"]["total"],
            "Wikipedia": format_number(d["wikipedia"]["views"]),
            "Articles": d["press"]["count"],
            "Trends": d["trends_score"],
        }
        if youtube_enabled:
            row["Vues YouTube"] = format_number(d["youtube"].get("total_views", 0))
        rows.append(row)

    df = pd.DataFrame(rows)

    col_config = {
        "Rang": st.column_config.NumberColumn("Rang", format="%d"),
        "Score": st.column_config.ProgressColumn("Score / 100", min_value=0, max_value=100, format="%.1f"),
        "Wikipedia": st.column_config.TextColumn("Wikipedia"),
        "Articles": st.column_config.NumberColumn("Articles", format="%d"),
        "Trends": st.column_config.NumberColumn("Trends", format="%.0f"),
    }
    if youtube_enabled:
        col_config["Vues YouTube"] = st.column_config.TextColumn("Vues YouTube")

    st.dataframe(df, column_config=col_config, hide_index=True, use_container_width=True)

    # Métriques
    leader = sorted_data[0][1]
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Leader", leader["info"]["name"])
    with col2:
        st.metric("Score", f"{leader['score']['total']:.1f} / 100")
    with col3:
        total_articles = sum(d["press"]["count"] for _, d in sorted_data)
        st.metric("Total articles", format_number(total_articles))
    with col4:
        total_wiki = sum(d["wikipedia"]["views"] for _, d in sorted_data)
        st.metric("Total Wikipedia", format_number(total_wiki))

    # === ONGLETS ===
    st.markdown("---")
    st.markdown("## Visualisations détaillées")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        ["Scores", "Sondages", "TV / Radio", "Historique", "Wikipedia", "Presse"]
    )

    names = [d["info"]["name"] for _, d in sorted_data]
    colors = [d["info"]["color"] for _, d in sorted_data]

    # TAB 1: SCORES
    with tab1:
        col1, col2 = st.columns(2)

        with col1:
            scores = [d["score"]["total"] for _, d in sorted_data]
            fig = px.bar(x=names, y=scores, color=names, color_discrete_sequence=colors,
                        title="Score de visibilité")
            fig.update_layout(
                showlegend=False,
                yaxis_range=[0, 100],
                yaxis_title="Score",
                xaxis_title=""
            )
            fig.update_traces(
                hovertemplate='<b>%{x}</b><br>Score: %{y:.1f}<extra></extra>'
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            decomp_data = []
            for _, d in sorted_data:
                s = d["score"]
                decomp_data.append({
                    "Candidat": d["info"]["name"],
                    "Presse (40%)": s["contrib_press"],
                    "Trends (35%)": s["contrib_trends"],
                    "Wikipedia (15%)": s["contrib_wiki"],
                    "YouTube (10%)": s["contrib_youtube"],
                })

            df_decomp = pd.DataFrame(decomp_data)
            fig = px.bar(df_decomp, x="Candidat",
                        y=["Presse (40%)", "Trends (35%)", "Wikipedia (15%)", "YouTube (10%)"],
                        barmode="stack", title="Décomposition du score",
                        color_discrete_map={
                            "Presse (40%)": "#2563eb",
                            "Trends (35%)": "#16a34a",
                            "Wikipedia (15%)": "#eab308",
                            "YouTube (10%)": "#dc2626"
                        })
            fig.update_layout(
                yaxis_range=[0, 100],
                yaxis_title="Points",
                xaxis_title="",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            fig.update_traces(
                hovertemplate='%{y:.1f}<extra></extra>'
            )
            st.plotly_chart(fig, use_container_width=True)

    # TAB 2: SONDAGES
    with tab2:
        st.markdown("### Sondages d'intentions de vote")

        if SONDAGES:
            for sondage in sorted(SONDAGES, key=lambda x: x["date"], reverse=True):
                with st.expander(f"{sondage['institut']} - {sondage['date']}", expanded=(sondage == get_latest_sondage())):
                    st.markdown(f"**Commanditaire :** {sondage['commanditaire']}")
                    st.markdown(f"**Échantillon :** {sondage['echantillon']} personnes")
                    st.markdown(f"**Méthode :** {sondage['methode']}")
                    st.markdown(f"**Hypothèse :** {sondage['hypothese']}")
                    if sondage.get("url"):
                        st.markdown(f"[Voir le sondage complet]({sondage['url']})")

                    sondage_rows = []
                    for name, score in sorted(sondage["scores"].items(), key=lambda x: x[1], reverse=True):
                        party = next((c["party"] for c in CANDIDATES.values() if c["name"] == name), "-")
                        sondage_rows.append({
                            "Candidat": name,
                            "Parti": party,
                            "Intentions": f"{score} %"
                        })

                    st.dataframe(pd.DataFrame(sondage_rows), use_container_width=True, hide_index=True)

                    sondage_colors = [
                        next((c["color"] for c in CANDIDATES.values() if c["name"] == r["Candidat"]), "#888")
                        for r in sondage_rows
                    ]

                    fig = px.bar(
                        x=[r["Candidat"] for r in sondage_rows],
                        y=[int(r["Intentions"].replace(" %", "")) for r in sondage_rows],
                        color=[r["Candidat"] for r in sondage_rows],
                        color_discrete_sequence=sondage_colors,
                        title=f"Intentions de vote - {sondage['institut']}"
                    )
                    fig.update_layout(
                        showlegend=False,
                        yaxis_title="Pourcentage (%)",
                        yaxis_range=[0, 40],
                        xaxis_title=""
                    )
                    fig.update_traces(
                        hovertemplate='<b>%{x}</b><br>%{y} %<extra></extra>'
                    )
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucun sondage disponible")

    # TAB 3: TV/RADIO
    with tab3:
        st.markdown("### Passages TV / Radio détectés")

        tv_data = []
        for _, d in sorted_data:
            tv = d.get("tv_radio", {})
            mentions = tv.get("mentions", [])
            top_media = tv.get("top_media", [])

            top_media_html = ""
            if top_media:
                links = []
                for media_name, count in top_media[:3]:
                    media_mentions = [m for m in mentions if m["media"] == media_name]
                    if media_mentions:
                        if len(media_mentions) == 1:
                            url = media_mentions[0]["url"]
                            links.append(f'<a href="{url}" target="_blank">{media_name}</a>')
                        else:
                            sub_links = []
                            for idx, m in enumerate(media_mentions[:5], 1):
                                sub_links.append(f'<a href="{m["url"]}" target="_blank">{idx}</a>')
                            links.append(f"{media_name} ({', '.join(sub_links)})")
                    else:
                        links.append(f"{media_name} ({count})")
                top_media_html = " · ".join(links)

            tv_data.append({
                "Candidat": d["info"]["name"],
                "Mentions": tv.get("count", 0),
                "Top médias": top_media_html if top_media_html else "-"
            })

        st.markdown(pd.DataFrame(tv_data).to_html(escape=False, index=False), unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### Détails des mentions")

        for _, d in sorted_data:
            tv = d.get("tv_radio", {})
            mentions = tv.get("mentions", [])

            if mentions:
                with st.expander(f"{d['info']['name']} - {len(mentions)} mention(s)"):
                    for i, mention in enumerate(mentions[:20], 1):
                        st.markdown(f"**{i}.** [{mention['title']}]({mention['url']})")
                        st.caption(f"{mention['date']} · {mention['source']} · {mention['media']}")

                    if len(mentions) > 20:
                        st.info(f"+ {len(mentions) - 20} autres mentions")

        if sum(d["Mentions"] for d in tv_data) > 0:
            st.markdown("---")
            fig = px.bar(
                x=[d["Candidat"] for d in tv_data],
                y=[d["Mentions"] for d in tv_data],
                color=[d["Candidat"] for d in tv_data],
                color_discrete_sequence=colors,
                title="Nombre de mentions TV / Radio"
            )
            fig.update_layout(
                showlegend=False,
                yaxis_title="Mentions",
                xaxis_title=""
            )
            fig.update_traces(
                hovertemplate='<b>%{x}</b><br>%{y} mentions<extra></extra>'
            )
            st.plotly_chart(fig, use_container_width=True)

    # TAB 4: HISTORIQUE
    with tab4:
        st.markdown("### Évolution des scores de visibilité")

        period_label_hist = f"{start_date} à {end_date}"
        history = add_to_history(data, period_label_hist)

        if is_cloud_configured():
            st.success(f"Sauvegarde cloud : {len(history)} entrée(s)")
        else:
            st.warning(f"Sauvegarde locale : {len(history)} entrée(s) - Données perdues au redémarrage")

        if history:
            history_df_data = []
            for entry in sorted(history, key=lambda x: x["date"]):
                for name, scores in entry.get("scores", {}).items():
                    history_df_data.append({
                        "Date": entry["date"],
                        "Candidat": name,
                        "Score": scores["total"]
                    })

            if history_df_data:
                df_hist = pd.DataFrame(history_df_data)
                color_map = {c["name"]: c["color"] for c in CANDIDATES.values()}

                unique_dates = df_hist["Date"].nunique()

                if unique_dates == 1:
                    st.info("Une seule date enregistrée. L'évolution apparaîtra dès la prochaine analyse.")

                fig = px.line(df_hist, x="Date", y="Score", color="Candidat",
                             markers=True, color_discrete_map=color_map,
                             title="Évolution des scores de visibilité")
                fig.update_layout(
                    yaxis_range=[0, 100],
                    yaxis_title="Score",
                    xaxis_title="Date",
                    xaxis=dict(type='category'),
                    legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5),
                    height=500,
                    margin=dict(b=100)
                )
                fig.update_traces(
                    hovertemplate='<b>%{fullData.name}</b><br>%{x}<br>Score: %{y:.1f}<extra></extra>'
                )
                st.plotly_chart(fig, use_container_width=True)

                if unique_dates > 1:
                    st.markdown("### Variations")
                    var_rows = []
                    for _, d in sorted_data:
                        name = d["info"]["name"]
                        current = d["score"]["total"]
                        hist = get_historical_comparison(name, current)

                        row = {"Candidat": name, "Actuel": current}
                        row["vs 7 jours"] = f"{hist['week_change']:+.1f}" if hist.get("week_change") is not None else "-"
                        row["vs 30 jours"] = f"{hist['month_change']:+.1f}" if hist.get("month_change") is not None else "-"
                        var_rows.append(row)

                    st.dataframe(pd.DataFrame(var_rows), use_container_width=True, hide_index=True)
        else:
            st.info("Aucun historique disponible")

    # TAB 5: WIKIPEDIA
    with tab5:
        days_in_period = (end_date - start_date).days + 1

        col1, col2 = st.columns(2)

        with col1:
            wiki_views = [d["wikipedia"]["views"] for _, d in sorted_data]
            fig = px.bar(
                x=names,
                y=wiki_views,
                color=names,
                color_discrete_sequence=colors,
                title="Vues Wikipedia"
            )
            fig.update_layout(
                showlegend=False,
                yaxis_title="Vues",
                xaxis_title=""
            )
            fig.update_traces(
                hovertemplate='<b>%{x}</b><br>%{y} vues<extra></extra>'
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            variations = [max(min(d["wikipedia"]["variation"], 100), -100) for _, d in sorted_data]
            fig = px.bar(
                x=names,
                y=variations,
                color=variations,
                color_continuous_scale=["#dc2626", "#6b7280", "#16a34a"],
                range_color=[-100, 100],
                title=f"Variation vs {days_in_period} jours précédents"
            )
            fig.update_layout(
                yaxis_range=[-100, 100],
                yaxis_title="Variation (%)",
                xaxis_title=""
            )
            fig.update_traces(
                hovertemplate='<b>%{x}</b><br>%{y:+.1f} %<extra></extra>'
            )
            st.plotly_chart(fig, use_container_width=True)

    # TAB 6: PRESSE
    with tab6:
        col1, col2 = st.columns(2)

        with col1:
            articles = [d["press"]["count"] for _, d in sorted_data]
            fig = px.bar(
                x=names,
                y=articles,
                color=names,
                color_discrete_sequence=colors,
                title="Nombre d'articles de presse"
            )
            fig.update_layout(
                showlegend=False,
                yaxis_title="Articles",
                xaxis_title=""
            )
            fig.update_traces(
                hovertemplate='<b>%{x}</b><br>%{y} articles<extra></extra>'
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.pie(
                names=names,
                values=articles,
                color=names,
                color_discrete_sequence=colors,
                title="Part de voix médiatique"
            )
            fig.update_traces(
                hovertemplate='<b>%{label}</b><br>%{value} articles<br>%{percent}<extra></extra>'
            )
            st.plotly_chart(fig, use_container_width=True)

    # === ARTICLES ===
    st.markdown("---")
    st.markdown("## Articles de presse")

    for rank, (cid, d) in enumerate(sorted_data, 1):
        arts = d["press"]["articles"]
        with st.expander(f"{rank}. {d['info']['name']} — {len(arts)} article(s)"):
            if arts:
                for i, a in enumerate(arts[:15], 1):
                    st.markdown(f"**{i}.** [{a['title']}]({a['url']})")
                    st.caption(f"{a['date']} · {a['domain']}")
                if len(arts) > 15:
                    st.info(f"+ {len(arts) - 15} autres articles")
            else:
                st.info("Aucun article trouvé")

    # === YOUTUBE ===
    st.markdown("---")
    st.markdown("## Vidéos YouTube les mentionnant")

    if not any(d["youtube"].get("available") for _, d in sorted_data):
        st.info("Aucune vidéo YouTube trouvée pour la période sélectionnée")
    else:
        for rank, (cid, d) in enumerate(sorted_data, 1):
            yt = d["youtube"]
            if yt.get("available") and yt.get("videos"):
                with st.expander(f"{rank}. {d['info']['name']} — {format_number(yt['total_views'])} vues"):
                    for i, v in enumerate(yt["videos"][:10], 1):
                        views = v.get("views", 0)
                        st.markdown(f"**{i}.** [{v['title']}]({v['url']}) — {format_number(views)} vues")
                        st.caption(f"{v.get('published', '')} · {v.get('channel', '')}")

                    if len(yt["videos"]) > 10:
                        st.info(f"+ {len(yt['videos']) - 10} autres vidéos")


if __name__ == "__main__":
    main()
