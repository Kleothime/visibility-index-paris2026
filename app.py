"""
VISIBILITY INDEX v7.1 - Municipales Paris 2026
Avec persistance cloud (JSONBin.io)
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
    page_title="Visibility Index - Paris 2026",
    page_icon="🗳️",
    layout="wide"
)

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
        "search_terms": ["Rachida Dati", "Dati ministre"],
    },
    "emmanuel_gregoire": {
        "name": "Emmanuel Grégoire",
        "party": "PS",
        "role": "1er adjoint Mairie de Paris",
        "color": "#FF69B4",
        "wikipedia": "Emmanuel_Grégoire",
        "search_terms": ["Emmanuel Grégoire", "Grégoire adjoint Paris"],
    },
    "pierre_yves_bournazel": {
        "name": "Pierre-Yves Bournazel",
        "party": "Horizons",
        "role": "Conseiller de Paris",
        "color": "#FF6B35",
        "wikipedia": "Pierre-Yves_Bournazel",
        "search_terms": ["Pierre-Yves Bournazel", "Bournazel Paris"],
    },
    "ian_brossat": {
        "name": "Ian Brossat",
        "party": "PCF",
        "role": "Sénateur de Paris",
        "color": "#DD0000",
        "wikipedia": "Ian_Brossat",
        "search_terms": ["Ian Brossat"],
    },
    "david_belliard": {
        "name": "David Belliard",
        "party": "EELV",
        "role": "Adjoint transports",
        "color": "#00A86B",
        "wikipedia": "David_Belliard",
        "search_terms": ["David Belliard"],
    },
    "sophia_chikirou": {
        "name": "Sophia Chikirou",
        "party": "LFI",
        "role": "Députée de Paris",
        "color": "#C9462C",
        "wikipedia": "Sophia_Chikirou",
        "search_terms": ["Sophia Chikirou"],
    },
    "thierry_mariani": {
        "name": "Thierry Mariani",
        "party": "RN",
        "role": "Député européen",
        "color": "#0D2C54",
        "wikipedia": "Thierry_Mariani",
        "search_terms": ["Thierry Mariani"],
    }
}

# =============================================================================
# SONDAGES OFFICIELS
# =============================================================================

SONDAGES = [
    {
        "date": "2025-06-21",
        "institut": "ELABE",
        "media": "La Tribune Dimanche / BFMTV",
        "sample": 1097,
        "hypothese": "Avec P-Y Bournazel, E. Grégoire candidat PS",
        "scores": {
            "Rachida Dati": 28,
            "David Belliard": 22,
            "Emmanuel Grégoire": 19,
            "Sophia Chikirou": 14,
            "Pierre-Yves Bournazel": 8,
            "Thierry Mariani": 7,
        }
    },
    {
        "date": "2025-11-04",
        "institut": "IFOP-Fiducial",
        "media": "Le Figaro / Sud Radio",
        "sample": 1037,
        "hypothese": "Hypothèse avec Bournazel candidat",
        "scores": {
            "Rachida Dati": 27,
            "Emmanuel Grégoire": 18,
            "David Belliard": 17,
            "Pierre-Yves Bournazel": 15,
            "Sophia Chikirou": 12,
            "Thierry Mariani": 7,
        }
    },
]

def get_latest_sondage():
    if not SONDAGES:
        return None
    return max(SONDAGES, key=lambda x: x["date"])

def get_candidate_sondage_score(candidate_name: str) -> Optional[int]:
    latest = get_latest_sondage()
    if latest and candidate_name in latest["scores"]:
        return latest["scores"][candidate_name]
    return None

MEDIAS_TV_RADIO = [
    "BFM", "BFMTV", "LCI", "CNews", "TF1", "France 2", "France 3",
    "France Inter", "RTL", "Europe 1", "RMC", "France Info", "France 24",
    "Arte", "Public Sénat", "LCP", "C8", "TMC"
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
        with open(HISTORY_FILE, "r") as f:
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
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)
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
# FONCTIONS DE COLLECTE
# =============================================================================

@st.cache_data(ttl=1800, show_spinner=False)
def get_wikipedia_views(page_title: str, start_date: date, end_date: date) -> Dict:
    """Wikipedia API"""
    try:
        days_in_period = (end_date - start_date).days + 1
        ref_end = start_date - timedelta(days=1)
        ref_start = ref_end - timedelta(days=days_in_period - 1)
        
        url = (
            f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
            f"fr.wikipedia/all-access/user/{quote_plus(page_title)}/daily/"
            f"{ref_start.strftime('%Y%m%d')}/{end_date.strftime('%Y%m%d')}"
        )
        
        response = requests.get(url, headers={"User-Agent": "VisibilityIndex/7.1"}, timeout=15)
        
        if response.status_code != 200:
            return {"views": 0, "variation": 0, "daily": {}, "avg_daily": 0, 
                    "ref_views": 0, "ref_avg": 0, "error": f"HTTP {response.status_code}"}
        
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
    """GDELT API"""
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
    """Google News RSS"""
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
    """Récupère tous les articles pour un candidat"""
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
    """Google Trends via pytrends"""
    try:
        from pytrends.request import TrendReq
        import time
        import random

        if not keywords:
            return {"success": False, "scores": {}, "errors": ["keywords vides"]}

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
                        errors.append("DataFrame vide")
                        
            except Exception as e:
                err_str = str(e)
                if "429" in err_str:
                    if attempt < max_retries - 1:
                        time.sleep(10 * (attempt + 1) + random.uniform(0, 5))
                    else:
                        errors.append("Rate limit Google (429)")
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
        return {"success": False, "scores": {kw: 0.0 for kw in keywords}, "error": "pytrends non installé"}
    except Exception as e:
        return {"success": False, "scores": {kw: 0.0 for kw in keywords}, "error": str(e)[:100]}


def _is_short(duration: str) -> bool:
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
    """YouTube Data API v3"""
    if not api_key or not api_key.strip():
        return {"available": False, "videos": [], "total_views": 0, "error": "Pas de clé API"}
    
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
                error_msg = err_data.get("error", {}).get("message", f"HTTP {response.status_code}")
            except:
                error_msg = f"HTTP {response.status_code}"
                
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
    """Recherche les mentions TV/Radio via Google News"""
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
        "mentions": mentions[:20],
        "media_counts": media_counts,
        "top_media": sorted(media_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    }


# =============================================================================
# CALCUL DU SCORE
# =============================================================================

def calculate_score(wiki_views: int, press_count: int, press_domains: int, 
                    trends_score: float, youtube_views: int, youtube_available: bool) -> Dict:
    """Pondération: Trends 35%, Presse 40%, Wikipedia 15%, YouTube 10%"""
    
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
    """Collecte toutes les données"""
    results = {}
    
    progress = st.progress(0)
    status = st.empty()
    
    status.text("Chargement Google Trends...")
    names = [CANDIDATES[cid]["name"] for cid in candidate_ids]
    trends = get_google_trends(names, start_date, end_date)
    
    if not trends["success"]:
        err = trends.get("error") or trends.get("errors")
        if err:
            st.warning(f"⚠️ Google Trends indisponible : {err}")
    
    progress.progress(0.1)
    
    total = len(candidate_ids)
    
    for i, cid in enumerate(candidate_ids):
        c = CANDIDATES[cid]
        name = c["name"]
        
        status.text(f"Analyse : {name}...")
        
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
# UTILITAIRES
# =============================================================================

def format_num(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n/1_000:.1f}k"
    return str(n)


def _format_duration(duration: str) -> str:
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if not match:
        return ""
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


# =============================================================================
# INTERFACE
# =============================================================================

def main():
    st.markdown("# Visibility Index v7.1")
    st.markdown("**Municipales Paris 2026** — Analyse de visibilité médiatique")
    
    with st.sidebar:
        st.markdown("## Configuration")
        
        # Période
        st.markdown("### Période d'analyse")
        
        period_type = st.radio("Type de période", ["Prédéfinie", "Personnalisée"], horizontal=True)
        
        if period_type == "Prédéfinie":
            period_options = {"48 heures": 2, "7 jours": 7, "14 jours": 14, "30 jours": 30}
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
                st.error("Date début > date fin")
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
        
        # YouTube
        st.markdown("### YouTube API")
        st.code("AIzaSyCu27YMexJiCrzagkCnawkECG7WA1_wzDI", language=None)
        yt_key = st.text_input("Clé API", value="", placeholder="Coller la clé ci-dessus")
        
        if yt_key and yt_key.strip().startswith("AIza"):
            st.success("✓ YouTube activé")
        
        # Persistance cloud
        st.markdown("### 💾 Persistance historique")
        
        cloud_configured = is_cloud_configured()
        if cloud_configured:
            st.success("✓ Cloud configuré")
        else:
            with st.expander("Configurer (optionnel)"):
                st.markdown("""
                **Pour conserver l'historique :**
                1. Créer un compte sur [jsonbin.io](https://jsonbin.io)
                2. Copier la **Master Key**
                3. Créer un bin avec `[]`
                4. Copier l'**ID du bin**
                """)
                
                bin_id = st.text_input("Bin ID", value=st.session_state.get("jsonbin_bin_id", ""))
                api_key = st.text_input("Master Key", value=st.session_state.get("jsonbin_api_key", ""), type="password")
                
                if bin_id:
                    st.session_state["jsonbin_bin_id"] = bin_id
                if api_key:
                    st.session_state["jsonbin_api_key"] = api_key
                
                if bin_id and api_key:
                    if st.button("Tester connexion"):
                        test = load_history_cloud(bin_id, api_key)
                        if test is not None:
                            st.success(f"✓ OK ({len(test)} entrées)")
                        else:
                            st.error("Échec")
        
        st.markdown("---")
        
        if st.button("🔄 Rafraîchir", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        st.markdown("---")
        st.markdown("### Pondération")
        st.caption("Presse 40% · Trends 35% · Wiki 15% · YT 10%")
    
    if not selected:
        st.warning("Sélectionnez au moins un candidat")
        return
    
    youtube_key = yt_key.strip() if yt_key and yt_key.strip().startswith("AIza") else None
    
    data = collect_data(selected, start_date, end_date, youtube_key)
    sorted_data = sorted(data.items(), key=lambda x: x[1]["score"]["total"], reverse=True)
    
    # === CLASSEMENT ===
    st.markdown("---")
    st.markdown("## Classement")
    
    youtube_enabled = any(d["youtube"].get("available", False) for _, d in sorted_data)
    
    rows = []
    for rank, (cid, d) in enumerate(sorted_data, 1):
        row = {
            "Rang": rank,
            "Candidat": d["info"]["name"],
            "Parti": d["info"]["party"],
            "Score": d["score"]["total"],
            "Wikipedia": d["wikipedia"]["views"],
            "Articles": d["press"]["count"],
            "Trends": d["trends_score"],
        }
        if youtube_enabled:
            row["YouTube"] = d["youtube"].get("total_views", 0)
        rows.append(row)
    
    df = pd.DataFrame(rows)
    
    col_config = {
        "Rang": st.column_config.NumberColumn("Rang", format="%d"),
        "Score": st.column_config.ProgressColumn("Score /100", min_value=0, max_value=100, format="%.1f"),
        "Wikipedia": st.column_config.NumberColumn("Wiki", format="%d"),
        "Articles": st.column_config.NumberColumn("Presse", format="%d"),
        "Trends": st.column_config.NumberColumn("Trends", format="%.0f"),
    }
    if youtube_enabled:
        col_config["YouTube"] = st.column_config.NumberColumn("YT", format="%d")
    
    st.dataframe(df, column_config=col_config, hide_index=True, use_container_width=True)
    
    # Métriques
    leader = sorted_data[0][1]
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Leader", leader["info"]["name"])
    with col2:
        st.metric("Score", f"{leader['score']['total']:.1f}/100")
    with col3:
        st.metric("Articles", sum(d["press"]["count"] for _, d in sorted_data))
    with col4:
        st.metric("Wikipedia", format_num(sum(d["wikipedia"]["views"] for _, d in sorted_data)))
    
    # === ONGLETS ===
    st.markdown("---")
    st.markdown("## Visualisations")
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
        ["Scores", "Sondages", "TV/Radio", "Historique", "Wikipedia", "Presse", "Debug"]
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
            fig.update_layout(showlegend=False, yaxis_range=[0, 100])
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
            fig.update_layout(yaxis_range=[0, 100], yaxis_title="Points",
                             legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True)
    
    # TAB 2: SONDAGES
    with tab2:
        latest = get_latest_sondage()
        
        if latest:
            st.markdown(f"### Dernier sondage : {latest['institut']}")
            st.caption(f"📅 {latest['date']} · {latest['media']} · {latest['sample']} pers.")
            
            sondage_rows = []
            for name, score in sorted(latest["scores"].items(), key=lambda x: x[1], reverse=True):
                party = next((c["party"] for c in CANDIDATES.values() if c["name"] == name), "-")
                sondage_rows.append({"Candidat": name, "Parti": party, "Intentions": f"{score}%"})
            
            st.dataframe(pd.DataFrame(sondage_rows), use_container_width=True, hide_index=True)
            
            sondage_colors = [next((c["color"] for c in CANDIDATES.values() if c["name"] == r["Candidat"]), "#888") 
                            for r in sondage_rows]
            
            fig = px.bar(x=[r["Candidat"] for r in sondage_rows],
                        y=[int(r["Intentions"].replace("%", "")) for r in sondage_rows],
                        color=[r["Candidat"] for r in sondage_rows],
                        color_discrete_sequence=sondage_colors,
                        title=f"Intentions de vote ({latest['institut']})")
            fig.update_layout(showlegend=False, yaxis_title="%", yaxis_range=[0, 40])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucun sondage disponible")
    
    # TAB 3: TV/RADIO
    with tab3:
        st.markdown("### Passages TV/Radio détectés")
        
        tv_data = []
        for _, d in sorted_data:
            tv = d.get("tv_radio", {})
            tv_data.append({
                "Candidat": d["info"]["name"],
                "Mentions": tv.get("count", 0),
                "Top médias": ", ".join([f"{m[0]} ({m[1]})" for m in tv.get("top_media", [])[:3]]) or "-"
            })
        
        st.dataframe(pd.DataFrame(tv_data), use_container_width=True, hide_index=True)
        
        if sum(d["Mentions"] for d in tv_data) > 0:
            fig = px.bar(x=[d["Candidat"] for d in tv_data], y=[d["Mentions"] for d in tv_data],
                        color=[d["Candidat"] for d in tv_data], color_discrete_sequence=colors,
                        title="Mentions TV/Radio")
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    
    # TAB 4: HISTORIQUE
    with tab4:
        st.markdown("### Évolution des scores de visibilité")
        
        period_label_hist = f"{start_date} to {end_date}"
        history = add_to_history(data, period_label_hist)
        
        if is_cloud_configured():
            st.success(f"☁️ Cloud : {len(history)} entrée(s)")
        else:
            st.warning(f"💾 Local : {len(history)} entrée(s) — perdu au redémarrage")
        
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
                    st.info("📊 Une seule date enregistrée. L'évolution apparaîtra dès demain !")
                
                # Toujours afficher un graphique en ligne
                fig = px.line(df_hist, x="Date", y="Score", color="Candidat",
                             markers=True, color_discrete_map=color_map,
                             title="Évolution des scores de visibilité")
                fig.update_layout(
                    yaxis_range=[0, 100],
                    yaxis_title="Score",
                    xaxis_title="Date",
                    xaxis=dict(type='category'),  # Force l'affichage correct des dates
                    legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5),
                    height=500,
                    margin=dict(b=100)
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Tableau des variations (si plusieurs dates)
                if unique_dates > 1:
                    st.markdown("### Variations")
                    var_rows = []
                    for _, d in sorted_data:
                        name = d["info"]["name"]
                        current = d["score"]["total"]
                        hist = get_historical_comparison(name, current)
                        
                        row = {"Candidat": name, "Actuel": current}
                        row["vs 7j"] = f"{hist['week_change']:+.1f}" if hist.get("week_change") is not None else "-"
                        row["vs 30j"] = f"{hist['month_change']:+.1f}" if hist.get("month_change") is not None else "-"
                        var_rows.append(row)
                    
                    st.dataframe(pd.DataFrame(var_rows), use_container_width=True, hide_index=True)
        else:
            st.info("Aucun historique")
    
    # TAB 5: WIKIPEDIA
    with tab5:
        days_in_period = (end_date - start_date).days + 1
        
        if end_date >= date.today() - timedelta(days=1):
            st.warning("⚠️ Wikipedia a un délai de 24-48h")
        
        col1, col2 = st.columns(2)
        
        with col1:
            wiki_views = [d["wikipedia"]["views"] for _, d in sorted_data]
            fig = px.bar(x=names, y=wiki_views, color=names, color_discrete_sequence=colors,
                        title="Vues Wikipedia")
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            variations = [max(min(d["wikipedia"]["variation"], 100), -100) for _, d in sorted_data]
            fig = px.bar(x=names, y=variations, color=variations,
                        color_continuous_scale=["#dc2626", "#6b7280", "#16a34a"],
                        range_color=[-100, 100],
                        title=f"Variation vs {days_in_period}j précédents")
            fig.update_layout(yaxis_range=[-100, 100])
            st.plotly_chart(fig, use_container_width=True)
    
    # TAB 6: PRESSE
    with tab6:
        col1, col2 = st.columns(2)
        
        with col1:
            articles = [d["press"]["count"] for _, d in sorted_data]
            fig = px.bar(x=names, y=articles, color=names, color_discrete_sequence=colors,
                        title="Nombre d'articles")
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.pie(names=names, values=articles, color=names, color_discrete_sequence=colors,
                        title="Part de voix")
            st.plotly_chart(fig, use_container_width=True)
    
    # TAB 7: DEBUG
    with tab7:
        debug_rows = []
        for rank, (cid, d) in enumerate(sorted_data, 1):
            yt = d["youtube"]
            yt_info = "-"
            if yt.get("available"):
                yt_info = f"{yt.get('total_views', 0)} ({yt.get('count', 0)} vidéos)"
            elif yt.get("error"):
                yt_info = "Erreur" if "quota" not in yt.get("error", "").lower() else "Quota"
            
            debug_rows.append({
                "Rang": rank,
                "Candidat": d["info"]["name"],
                "Wiki": d["wikipedia"]["views"],
                "Presse": d["press"]["count"],
                "TV": d.get("tv_radio", {}).get("count", 0),
                "Trends": d["trends_score"],
                "YT": yt_info,
                "Score": d["score"]["total"]
            })
        
        st.dataframe(pd.DataFrame(debug_rows), use_container_width=True, hide_index=True)
    
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
                    st.info(f"+ {len(arts) - 15} autres")
            else:
                st.info("Aucun article")
    
    # === YOUTUBE ===
    st.markdown("---")
    st.markdown("## Vidéos YouTube")
    
    if not any(d["youtube"].get("available") for _, d in sorted_data):
        if youtube_key:
            st.warning("Aucune vidéo ou quota dépassé")
        else:
            st.info("Clé API YouTube requise")
    else:
        for rank, (cid, d) in enumerate(sorted_data, 1):
            yt = d["youtube"]
            if yt.get("available") and yt.get("videos"):
                with st.expander(f"{rank}. {d['info']['name']} — {format_num(yt['total_views'])} vues"):
                    for i, v in enumerate(yt["videos"][:10], 1):
                        views = v.get("views", 0)
                        st.markdown(f"**{i}.** [{v['title']}]({v['url']}) — {format_num(views)} vues")
                        st.caption(f"{v.get('published', '')} · {v.get('channel', '')}")
    
    # Footer
    st.markdown("---")
    st.caption(f"Visibility Index v7.1 · {datetime.now().strftime('%d/%m/%Y %H:%M')}")


if __name__ == "__main__":
    main()
