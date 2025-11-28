"""
VISIBILITY INDEX v7.0 - Municipales Paris 2026
Nouvelles fonctionnalités: Sondages, TV/Radio, Historique
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

# Derniers sondages publiés (source: instituts de sondage)
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
        "hypothese": "Hypothèse principale",
        "scores": {
            "Rachida Dati": 27,
            "Emmanuel Grégoire": 18,
            "David Belliard": 17,
            "Pierre-Yves Bournazel": 15,
            "Sophia Chikirou": 12,
            "Thierry Mariani": 7,
        }
    },
    {
        "date": "2025-11-21",
        "institut": "Verian",
        "media": "Renaissance",
        "sample": 1000,
        "hypothese": "Hypothèse principale",
        "scores": {
            "Emmanuel Grégoire": 22,
            "Rachida Dati": 21,
            "David Belliard": 16,
            "Sophia Chikirou": 14,
            "Pierre-Yves Bournazel": 12,
            "Thierry Mariani": 8,
        }
    },
]

def get_latest_sondage():
    """Retourne le dernier sondage disponible"""
    if not SONDAGES:
        return None
    return max(SONDAGES, key=lambda x: x["date"])

def get_candidate_sondage_score(candidate_name: str) -> Optional[int]:
    """Retourne le score du dernier sondage pour un candidat"""
    latest = get_latest_sondage()
    if latest and candidate_name in latest["scores"]:
        return latest["scores"][candidate_name]
    return None

# Médias audiovisuels à rechercher
MEDIAS_TV_RADIO = [
    "BFM", "BFMTV", "LCI", "CNews", "TF1", "France 2", "France 3",
    "France Inter", "RTL", "Europe 1", "RMC", "France Info", "France 24",
    "Arte", "Public Sénat", "LCP", "C8", "TMC"
]

# =============================================================================
# FONCTIONS DE COLLECTE
# =============================================================================

@st.cache_data(ttl=1800, show_spinner=False)
def get_wikipedia_views(page_title: str, start_date: date, end_date: date) -> Dict:
    """Wikipedia API - Calcul rigoureux des vues et variations"""
    try:
        # Période de référence : même durée que la période analysée, juste avant
        days_in_period = (end_date - start_date).days + 1
        
        # Référence = même durée, juste avant la période
        ref_end = start_date - timedelta(days=1)
        ref_start = ref_end - timedelta(days=days_in_period - 1)
        
        # Récupérer les données depuis le début de la référence
        url = (
            f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
            f"fr.wikipedia/all-access/user/{quote_plus(page_title)}/daily/"
            f"{ref_start.strftime('%Y%m%d')}/{end_date.strftime('%Y%m%d')}"
        )
        
        response = requests.get(url, headers={"User-Agent": "VisibilityIndex/7.0"}, timeout=15)
        
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
        
        # Moyennes journalières
        avg_period = period_views / max(days_in_period, 1)
        avg_ref = reference_views / max(days_in_period, 1)
        
        # Variation en pourcentage
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
    """Récupère tous les articles pour un candidat, filtrés par période"""
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
    
    # Filtrage par DATE - ne garder que les articles dans la période
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    date_filtered = []
    for art in all_articles:
        art_date = art.get("date", "")
        if art_date:
            # Garder seulement si la date est dans la période
            if start_str <= art_date <= end_str:
                date_filtered.append(art)
        # Si pas de date, on ne garde pas l'article (on ne peut pas vérifier)
    
    # Filtrage par NOM - nom de famille dans le titre
    name_parts = candidate_name.lower().split()
    last_name = name_parts[-1] if name_parts else ""
    
    filtered = []
    for art in date_filtered:
        title_lower = art["title"].lower()
        if last_name and last_name in title_lower:
            filtered.append(art)
    
    # Dédupliquer par titre
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


@st.cache_data(ttl=3600, show_spinner=False)
def get_google_trends(keywords: List[str]) -> Dict:
    """Google Trends via pytrends"""
    try:
        from pytrends.request import TrendReq
        
        pytrends = TrendReq(hl='fr-FR', tz=60, timeout=(10, 25))
        pytrends.build_payload(keywords[:5], timeframe='today 1-m', geo='FR')
        df = pytrends.interest_over_time()
        
        if df.empty:
            return {"success": False, "scores": {}}
        
        if 'isPartial' in df.columns:
            df = df.drop(columns=['isPartial'])
        
        scores = {}
        for kw in keywords[:5]:
            if kw in df.columns:
                vals = df[kw].tolist()
                recent = vals[-7:] if len(vals) >= 7 else vals
                scores[kw] = round(sum(recent) / len(recent), 1) if recent else 0
        
        return {"success": True, "scores": scores}
    
    except Exception as e:
        return {"success": False, "scores": {}, "error": str(e)}


def _is_short(duration: str) -> bool:
    """Vérifie si une vidéo est un short (< 60 secondes) basé sur la durée ISO 8601"""
    if not duration:
        return False
    # Format: PT1M30S, PT45S, PT1H2M3S
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if not match:
        return False
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    total_seconds = hours * 3600 + minutes * 60 + seconds
    return total_seconds < 60


@st.cache_data(ttl=1800, show_spinner=False)
def get_youtube_data(search_term: str, api_key: str, start_date: date, end_date: date) -> Dict:
    """YouTube Data API v3 - Récupère vidéos longues ET shorts dans la période"""
    if not api_key or not api_key.strip():
        return {"available": False, "videos": [], "total_views": 0, "error": "Pas de clé API"}
    
    search_url = "https://www.googleapis.com/youtube/v3/search"
    all_videos = []
    seen_ids = set()
    
    # Dates pour le filtre
    published_after = start_date.strftime("%Y-%m-%dT00:00:00Z")
    published_before = (end_date + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
    
    # Recherche 1 : Par pertinence
    params_relevance = {
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
    
    response1 = None
    error_msg = None
    
    try:
        response1 = requests.get(search_url, params=params_relevance, timeout=15)
        
        if response1.status_code == 200:
            data = response1.json()
            for item in data.get("items", []):
                vid_id = item.get("id", {}).get("videoId", "")
                if vid_id and vid_id not in seen_ids:
                    seen_ids.add(vid_id)
                    pub_date = item.get("snippet", {}).get("publishedAt", "")[:10]
                    all_videos.append({
                        "id": vid_id,
                        "title": item.get("snippet", {}).get("title", ""),
                        "channel": item.get("snippet", {}).get("channelTitle", ""),
                        "published": pub_date
                    })
        else:
            # Erreur API - récupérer le message
            try:
                err_data = response1.json()
                err_detail = err_data.get("error", {})
                error_msg = err_detail.get("message", "")
                if not error_msg:
                    errors = err_detail.get("errors", [])
                    if errors:
                        error_msg = errors[0].get("reason", f"HTTP {response1.status_code}")
                    else:
                        error_msg = f"HTTP {response1.status_code}"
            except:
                error_msg = f"HTTP {response1.status_code}"
                
    except requests.exceptions.Timeout:
        error_msg = "Timeout (15s)"
    except requests.exceptions.ConnectionError as e:
        error_msg = f"Connexion refusée: {str(e)[:50]}"
    except Exception as e:
        error_msg = f"Exception: {str(e)[:50]}"
    
    # Si erreur sur la première requête, retourner immédiatement avec l'erreur
    if error_msg and not all_videos:
        return {"available": False, "videos": [], "total_views": 0, "error": error_msg}
    
    # Recherche 2 : Par nombre de vues (seulement si la première a réussi)
    if response1 and response1.status_code == 200:
        params_views = {
            "part": "snippet",
            "q": search_term,
            "type": "video",
            "order": "viewCount",
            "maxResults": 25,
            "regionCode": "FR",
            "relevanceLanguage": "fr",
            "publishedAfter": published_after,
            "publishedBefore": published_before,
            "key": api_key
        }
        
        try:
            response2 = requests.get(search_url, params=params_views, timeout=15)
            
            if response2.status_code == 200:
                for item in response2.json().get("items", []):
                    vid_id = item.get("id", {}).get("videoId", "")
                    if vid_id and vid_id not in seen_ids:
                        seen_ids.add(vid_id)
                        pub_date = item.get("snippet", {}).get("publishedAt", "")[:10]
                        all_videos.append({
                            "id": vid_id,
                            "title": item.get("snippet", {}).get("title", ""),
                            "channel": item.get("snippet", {}).get("channelTitle", ""),
                            "published": pub_date
                        })
        except:
            pass  # Ignorer les erreurs de la 2ème requête
    
    if not all_videos:
        return {"available": False, "videos": [], "total_views": 0, "error": error_msg or "Aucune vidéo trouvée"}
    
    # Filtrer par nom dans le titre
    name_parts = search_term.lower().split()
    filtered_videos = []
    video_ids = []
    
    for v in all_videos:
        title_lower = v["title"].lower()
        # Garder si au moins une partie du nom (>= 3 chars) est dans le titre
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
        return {"available": False, "videos": [], "total_views": 0, "error": "Aucune vidéo avec le nom dans le titre"}
    
    # Récupérer les stats (vues, durée)
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
                stats_items = stats_response.json().get("items", [])
                stats_map = {item["id"]: item for item in stats_items}
                
                for v in filtered_videos:
                    if v["id"] in stats_map:
                        item = stats_map[v["id"]]
                        views = int(item.get("statistics", {}).get("viewCount", 0))
                        duration = item.get("contentDetails", {}).get("duration", "")
                        
                        v["views"] = views
                        v["duration"] = duration
                        v["is_short"] = _is_short(duration)
                        total_views += views
        except Exception:
            pass  # Continuer sans les stats
    
    # Trier par vues
    filtered_videos.sort(key=lambda x: x.get("views", 0), reverse=True)
    
    # Stats
    shorts_count = sum(1 for v in filtered_videos if v.get("is_short", False))
    long_count = len(filtered_videos) - shorts_count
    
    return {
        "available": True,
        "videos": filtered_videos,
        "total_views": total_views,
        "count": len(filtered_videos),
        "shorts_count": shorts_count,
        "long_count": long_count
    }


# =============================================================================
# PASSAGES TV/RADIO
# =============================================================================

@st.cache_data(ttl=1800, show_spinner=False)
def get_tv_radio_mentions(candidate_name: str, start_date: date, end_date: date) -> Dict:
    """Recherche les mentions TV/Radio via Google News"""
    
    mentions = []
    media_counts = {}
    
    # Rechercher pour chaque média
    last_name = candidate_name.split()[-1].lower()
    
    # Construire une requête avec les médias principaux
    media_query = " OR ".join(MEDIAS_TV_RADIO[:6])  # Top 6 médias
    search_query = f"{candidate_name} ({media_query})"
    
    try:
        # Google News RSS
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
                
                # Parser la date
                art_date = ""
                if pub_date_raw:
                    try:
                        from email.utils import parsedate_to_datetime
                        dt = parsedate_to_datetime(pub_date_raw)
                        art_date = dt.strftime("%Y-%m-%d")
                    except:
                        pass
                
                # Filtrer par date
                if art_date and not (start_str <= art_date <= end_str):
                    continue
                
                # Vérifier si c'est un média TV/Radio
                title_lower = title.lower()
                source_lower = source.lower()
                
                # Vérifier que le nom est dans le titre
                if last_name not in title_lower:
                    continue
                
                # Identifier le média
                detected_media = None
                for media in MEDIAS_TV_RADIO:
                    if media.lower() in source_lower or media.lower() in title_lower:
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
    
    except Exception as e:
        pass
    
    return {
        "count": len(mentions),
        "mentions": mentions[:20],  # Limiter à 20
        "media_counts": media_counts,
        "top_media": sorted(media_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    }


# =============================================================================
# HISTORIQUE
# =============================================================================

HISTORY_FILE = "visibility_history.json"

def load_history() -> List[Dict]:
    """Charge l'historique depuis le fichier JSON"""
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_history(history: List[Dict]):
    """Sauvegarde l'historique dans le fichier JSON"""
    try:
        # Garder seulement les 30 derniers jours
        cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        history = [h for h in history if h.get("date", "") >= cutoff]
        
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)
    except:
        pass

def add_to_history(data: Dict, period_label: str):
    """Ajoute les données actuelles à l'historique"""
    history = load_history()
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Éviter les doublons pour aujourd'hui
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
    
    # Trouver les scores passés pour ce candidat
    past_scores = []
    for entry in history:
        if candidate_name in entry.get("scores", {}):
            past_scores.append({
                "date": entry["date"],
                "score": entry["scores"][candidate_name]["total"]
            })
    
    if not past_scores:
        return {"available": False}
    
    # Trier par date
    past_scores.sort(key=lambda x: x["date"])
    
    # Calculer les variations
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
        "history": past_scores[-14:],  # 2 dernières semaines
        "week_change": round(current_score - week_score, 1) if week_score else None,
        "month_change": round(current_score - month_score, 1) if month_score else None
    }


# =============================================================================
# CALCUL DU SCORE
# =============================================================================

def calculate_score(wiki_views: int, press_count: int, press_domains: int, trends_score: float, youtube_views: int, youtube_available: bool) -> Dict:
    """
    Pondération :
    - Google Trends : 35%
    - Presse : 40%
    - Wikipedia : 15%
    - YouTube : 10%
    """
    
    # Wikipedia (log scale, 15%) - 50k vues = score max
    wiki_score = 0
    if wiki_views > 0:
        wiki_score = min((math.log10(wiki_views) / 4.7) * 100, 100)
    
    # Presse (40%) - 50 articles = 80 points, +20 diversité
    press_base = min((press_count / 50) * 80, 80)
    diversity_bonus = min((press_domains / 20) * 20, 20)
    press_score = min(press_base + diversity_bonus, 100)
    
    # Google Trends (35%) - déjà 0-100
    trends_norm = min(max(trends_score, 0), 100)
    
    # YouTube (10%) - log scale
    yt_score = 0
    if youtube_available and youtube_views > 0:
        yt_score = min((math.log10(youtube_views) / 6) * 100, 100)
    
    # Score final
    total = (
        trends_norm * 0.35 +
        press_score * 0.40 +
        wiki_score * 0.15 +
        yt_score * 0.10
    )
    
    total = min(max(total, 0), 100)
    
    return {
        "total": round(total, 1),
        "trends": round(trends_norm, 1),
        "press": round(press_score, 1),
        "wiki": round(wiki_score, 1),
        "youtube": round(yt_score, 1),
        # Contributions
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
    trends = get_google_trends(names)
    progress.progress(0.1)
    
    total = len(candidate_ids)
    
    for i, cid in enumerate(candidate_ids):
        c = CANDIDATES[cid]
        name = c["name"]
        
        status.text(f"Analyse : {name}...")
        
        wiki = get_wikipedia_views(c["wikipedia"], start_date, end_date)
        press = get_all_press_coverage(name, c["search_terms"], start_date, end_date)
        
        # Passages TV/Radio
        tv_radio = get_tv_radio_mentions(name, start_date, end_date)
        
        # YouTube : toujours 30 jours pour avoir des vidéos
        yt_start = date.today() - timedelta(days=30)
        yt_end = date.today()
        
        if youtube_key:
            youtube = get_youtube_data(name, youtube_key, yt_start, yt_end)
        else:
            youtube = {"available": False, "total_views": 0, "videos": []}
        
        trends_score = trends["scores"].get(name, 0) if trends["success"] else 0
        
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
    """Convertit PT1H2M3S en 1:02:03"""
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if not match:
        return ""
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"


# =============================================================================
# INTERFACE
# =============================================================================

def main():
    st.markdown("# Visibility Index v7.0")
    st.markdown("**Municipales Paris 2026** — Analyse de visibilité médiatique")
    
    # Sidebar
    with st.sidebar:
        st.markdown("## Configuration")
        
        # Période
        st.markdown("### Période d'analyse")
        
        period_type = st.radio(
            "Type de période",
            ["Prédéfinie", "Personnalisée"],
            horizontal=True
        )
        
        if period_type == "Prédéfinie":
            period_options = {
                "48 heures": 2,
                "7 jours": 7,
                "14 jours": 14,
                "30 jours": 30
            }
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
                st.error("La date de début doit être avant la date de fin")
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
        
        # Clé affichée pour copier-coller
        st.code("AIzaSyCu27YMexJiCrzagkCnawkECG7WA1_wzDI", language=None)
        
        yt_key = st.text_input("Clé API", value="", placeholder="Coller la clé ci-dessus")
        
        if yt_key and yt_key.strip().startswith("AIza"):
            st.success("Clé YouTube activée")
        elif yt_key:
            st.warning("Clé invalide (doit commencer par AIza)")
        else:
            st.caption("Sans clé = données YouTube indisponibles")
        
        st.markdown("---")
        
        if st.button("Rafraîchir les données", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        # Pondération
        st.markdown("---")
        st.markdown("### Pondération")
        st.caption("Presse : 40%")
        st.caption("Google Trends : 35%")
        st.caption("Wikipedia : 15%")
        st.caption("Vues YouTube : 10%")
    
    if not selected:
        st.warning("Sélectionnez au moins un candidat")
        return
    
    # Collecte
    # Valider la clé YouTube (doit commencer par AIza)
    youtube_key = None
    if yt_key and yt_key.strip().startswith("AIza"):
        youtube_key = yt_key.strip()
    
    data = collect_data(selected, start_date, end_date, youtube_key)
    
    # Tri par score
    sorted_data = sorted(data.items(), key=lambda x: x[1]["score"]["total"], reverse=True)
    
    # === CLASSEMENT ===
    st.markdown("---")
    st.markdown("## Classement")
    
    # Vérifier si YouTube est disponible pour au moins un candidat
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
            "Google Trends": d["trends_score"],
        }
        if youtube_enabled:
            row["Vues YouTube"] = d["youtube"].get("total_views", 0) if d["youtube"].get("available") else 0
        rows.append(row)
    
    df = pd.DataFrame(rows)
    
    col_config = {
        "Rang": st.column_config.NumberColumn("Rang", format="%d"),
        "Score": st.column_config.ProgressColumn("Score /100", min_value=0, max_value=100, format="%.1f"),
        "Wikipedia": st.column_config.NumberColumn("Wikipedia", format="%d"),
        "Articles": st.column_config.NumberColumn("Presse", format="%d"),
        "Google Trends": st.column_config.NumberColumn("Google Trends", format="%.0f"),
    }
    
    if youtube_enabled:
        col_config["Vues YouTube"] = st.column_config.NumberColumn("Vues YouTube", format="%d")
    
    st.dataframe(df, column_config=col_config, hide_index=True, use_container_width=True)
    
    # === MÉTRIQUES LEADER ===
    leader = sorted_data[0][1]
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Leader", leader["info"]["name"])
    with col2:
        st.metric("Score", f"{leader['score']['total']:.1f}/100")
    with col3:
        total_articles = sum(d["press"]["count"] for _, d in sorted_data)
        st.metric("Total articles", total_articles)
    with col4:
        total_wiki = sum(d["wikipedia"]["views"] for _, d in sorted_data)
        st.metric("Total Wikipedia", format_num(total_wiki))
    
    # === GRAPHIQUES ===
    st.markdown("---")
    st.markdown("## Visualisations")
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["Scores", "Sondages", "TV/Radio", "Historique", "Wikipedia", "Presse", "Données brutes"])
    
    names = [d["info"]["name"] for _, d in sorted_data]
    colors = [d["info"]["color"] for _, d in sorted_data]
    
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
                    "Google Trends (35%)": s["contrib_trends"],
                    "Wikipedia (15%)": s["contrib_wiki"],
                    "YouTube (10%)": s["contrib_youtube"],
                    "Score total": s["total"]
                })
            
            df_decomp = pd.DataFrame(decomp_data)
            fig = px.bar(df_decomp, x="Candidat", 
                        y=["Presse (40%)", "Google Trends (35%)", "Wikipedia (15%)", "YouTube (10%)"],
                        barmode="stack", 
                        title="Décomposition du score",
                        color_discrete_map={
                            "Presse (40%)": "#2563eb",
                            "Google Trends (35%)": "#16a34a",
                            "Wikipedia (15%)": "#eab308",
                            "YouTube (10%)": "#dc2626"
                        })
            fig.update_layout(
                yaxis_range=[0, 100],
                yaxis_title="Points",
                legend_title="Source",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # === TAB 2: SONDAGES ===
    with tab2:
        latest = get_latest_sondage()
        
        if latest:
            st.markdown(f"### Dernier sondage : {latest['institut']}")
            st.caption(f"📅 {latest['date']} · {latest['media']} · {latest['sample']} personnes interrogées")
            if latest.get("hypothese"):
                st.caption(f"📊 Hypothèse : {latest['hypothese']}")
            
            # Tableau du dernier sondage
            sondage_rows = []
            for name, score in sorted(latest["scores"].items(), key=lambda x: x[1], reverse=True):
                # Trouver le parti
                party = "-"
                for cid, c in CANDIDATES.items():
                    if c["name"] == name:
                        party = c["party"]
                        break
                sondage_rows.append({
                    "Rang": len(sondage_rows) + 1,
                    "Candidat": name,
                    "Parti": party,
                    "Intentions de vote": f"{score}%"
                })
            
            st.dataframe(pd.DataFrame(sondage_rows), use_container_width=True, hide_index=True)
            
            # Graphique
            sondage_names = [r["Candidat"] for r in sondage_rows]
            sondage_values = [int(r["Intentions de vote"].replace("%", "")) for r in sondage_rows]
            
            # Couleurs par candidat
            sondage_colors = []
            for name in sondage_names:
                color = "#888888"
                for cid, c in CANDIDATES.items():
                    if c["name"] == name:
                        color = c["color"]
                        break
                sondage_colors.append(color)
            
            fig = px.bar(x=sondage_names, y=sondage_values, color=sondage_names,
                        color_discrete_sequence=sondage_colors,
                        title=f"Intentions de vote - 1er tour ({latest['institut']})")
            fig.update_layout(showlegend=False, yaxis_title="%", yaxis_range=[0, 40])
            st.plotly_chart(fig, use_container_width=True)
            
            # Historique des sondages
            if len(SONDAGES) > 1:
                st.markdown("---")
                st.markdown("### Historique des sondages")
                
                for s in reversed(SONDAGES):
                    with st.expander(f"{s['date']} — {s['institut']} ({s['media']})"):
                        st.caption(f"Échantillon : {s['sample']} personnes")
                        if s.get("hypothese"):
                            st.caption(f"Hypothèse : {s['hypothese']}")
                        
                        for name, score in sorted(s["scores"].items(), key=lambda x: x[1], reverse=True):
                            st.write(f"• **{name}** : {score}%")
                
                # Graphique d'évolution
                st.markdown("### Évolution dans les sondages")
                evolution_data = []
                for s in SONDAGES:
                    for name, score in s["scores"].items():
                        evolution_data.append({
                            "Date": s["date"],
                            "Candidat": name,
                            "Score": score
                        })
                
                if evolution_data:
                    df_evol = pd.DataFrame(evolution_data)
                    fig = px.line(df_evol, x="Date", y="Score", color="Candidat",
                                 markers=True, title="Évolution des intentions de vote")
                    fig.update_layout(yaxis_title="%", yaxis_range=[0, 40])
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucun sondage disponible")
    
    # === TAB 3: TV/RADIO ===
    with tab3:
        st.markdown("### Passages TV/Radio détectés")
        st.caption("Mentions dans les médias audiovisuels (via Google News)")
        
        tv_data = []
        for _, d in sorted_data:
            tv = d.get("tv_radio", {})
            tv_data.append({
                "Candidat": d["info"]["name"],
                "Mentions": tv.get("count", 0),
                "Top médias": ", ".join([f"{m[0]} ({m[1]})" for m in tv.get("top_media", [])[:3]]) or "-"
            })
        
        st.dataframe(pd.DataFrame(tv_data), use_container_width=True, hide_index=True)
        
        # Graphique
        tv_names = [d["Candidat"] for d in tv_data]
        tv_counts = [d["Mentions"] for d in tv_data]
        
        if sum(tv_counts) > 0:
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.bar(x=tv_names, y=tv_counts, color=tv_names, color_discrete_sequence=colors,
                            title="Mentions TV/Radio")
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Agrégation par média
                all_media = {}
                for _, d in sorted_data:
                    for media, count in d.get("tv_radio", {}).get("media_counts", {}).items():
                        all_media[media] = all_media.get(media, 0) + count
                
                if all_media:
                    media_sorted = sorted(all_media.items(), key=lambda x: x[1], reverse=True)[:10]
                    fig = px.bar(x=[m[0] for m in media_sorted], y=[m[1] for m in media_sorted],
                                title="Médias les plus actifs")
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucune mention TV/Radio détectée sur cette période")
        
        # Détails par candidat
        for _, d in sorted_data:
            tv = d.get("tv_radio", {})
            if tv.get("mentions"):
                with st.expander(f"{d['info']['name']} — {tv['count']} mention(s)"):
                    for m in tv["mentions"][:10]:
                        st.markdown(f"**{m.get('media', '')}** · {m.get('date', '')}")
                        st.markdown(f"[{m['title']}]({m.get('url', '#')})")
                        st.caption(f"Source: {m.get('source', '')}")
    
    # === TAB 4: HISTORIQUE ===
    with tab4:
        st.markdown("### Évolution des scores de visibilité")
        st.caption("💡 L'historique se construit automatiquement à chaque analyse")
        
        # Sauvegarder les données actuelles
        period_label_for_history = f"{start_date} to {end_date}"
        history = add_to_history(data, period_label_for_history)
        
        if len(history) > 1:
            # Construire les données pour le graphique
            history_df_data = []
            for entry in history:
                for name, scores in entry.get("scores", {}).items():
                    history_df_data.append({
                        "Date": entry["date"],
                        "Candidat": name,
                        "Score": scores["total"]
                    })
            
            if history_df_data:
                df_hist = pd.DataFrame(history_df_data)
                
                # Couleurs par candidat
                color_map = {c["name"]: c["color"] for c in CANDIDATES.values()}
                
                # Graphique d'évolution
                fig = px.line(df_hist, x="Date", y="Score", color="Candidat",
                             markers=True,
                             color_discrete_map=color_map)
                fig.update_layout(
                    yaxis_range=[0, 100],
                    yaxis_title="Score de visibilité",
                    xaxis_title="Date",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    height=450
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Tableau des variations
                st.markdown("### Variations par rapport aux analyses précédentes")
                var_rows = []
                for _, d in sorted_data:
                    name = d["info"]["name"]
                    current = d["score"]["total"]
                    hist = get_historical_comparison(name, current)
                    
                    row = {
                        "Candidat": name,
                        "Score actuel": current,
                    }
                    
                    if hist.get("week_change") is not None:
                        change = hist["week_change"]
                        row["vs 7j"] = f"{change:+.1f}" if change != 0 else "="
                    else:
                        row["vs 7j"] = "-"
                    
                    if hist.get("month_change") is not None:
                        change = hist["month_change"]
                        row["vs 30j"] = f"{change:+.1f}" if change != 0 else "="
                    else:
                        row["vs 30j"] = "-"
                    
                    var_rows.append(row)
                
                st.dataframe(pd.DataFrame(var_rows), use_container_width=True, hide_index=True)
                
                # Nombre d'entrées dans l'historique
                st.caption(f"📊 {len(history)} analyse(s) enregistrée(s)")
        else:
            st.info("Première analyse ! L'historique se construira au fil de vos prochaines analyses.")
            st.caption("Les données sont sauvegardées dans visibility_history.json")
    
    # === TAB 5: WIKIPEDIA ===
    with tab5:
        # Calculer la durée de la période pour l'explication
        days_in_period = (end_date - start_date).days + 1
        
        st.caption(f"📊 Comparaison : période analysée ({days_in_period}j) vs période précédente équivalente ({days_in_period}j)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            wiki_views = [d["wikipedia"]["views"] for _, d in sorted_data]
            fig = px.bar(x=names, y=wiki_views, color=names, color_discrete_sequence=colors,
                        title=f"Vues Wikipedia ({start_date.strftime('%d/%m')} - {end_date.strftime('%d/%m')})")
            fig.update_layout(showlegend=False, yaxis_title="Vues totales")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            variations = []
            for _, d in sorted_data:
                v = d["wikipedia"]["variation"]
                v = max(min(v, 100), -100)
                variations.append(v)
            
            fig = px.bar(x=names, y=variations, color=variations,
                        color_continuous_scale=["#dc2626", "#6b7280", "#16a34a"],
                        range_color=[-100, 100],
                        title=f"Variation vs {days_in_period}j précédents (%)")
            fig.update_layout(yaxis_range=[-100, 100], yaxis_title="Variation (%)")
            st.plotly_chart(fig, use_container_width=True)
        
        # Tableau détaillé
        st.markdown("### Détails Wikipedia")
        wiki_rows = []
        for _, d in sorted_data:
            w = d["wikipedia"]
            wiki_rows.append({
                "Candidat": d["info"]["name"],
                "Vues (période)": w["views"],
                "Moy/jour": w.get("avg_daily", round(w["views"] / max(days_in_period, 1), 1)),
                "Vues (réf.)": w.get("ref_views", "-"),
                "Moy/jour (réf.)": w.get("ref_avg", "-"),
                "Variation": f"{w['variation']:+.1f}%" if w['variation'] != 0 else "="
            })
        st.dataframe(pd.DataFrame(wiki_rows), use_container_width=True, hide_index=True)
    
    # === TAB 6: PRESSE ===
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
                        title="Part de voix médiatique")
            st.plotly_chart(fig, use_container_width=True)
    
    # === TAB 7: DONNÉES BRUTES ===
    with tab7:
        debug_rows = []
        for rank, (cid, d) in enumerate(sorted_data, 1):
            yt = d["youtube"]
            yt_info = "-"
            if yt.get("available"):
                yt_info = f"{yt.get('total_views', 0)} ({yt.get('count', 0)} vidéos)"
            elif yt.get("error"):
                err = yt.get('error', '')
                if "quota" in err.lower():
                    yt_info = "Quota dépassé"
                else:
                    yt_info = f"Erreur"
            
            tv = d.get("tv_radio", {})
            
            row = {
                "Rang": rank,
                "Candidat": d["info"]["name"],
                "Wikipedia (vues)": d["wikipedia"]["views"],
                "Variation (%)": f"{max(min(d['wikipedia']['variation'], 100), -100):+.0f}%",
                "Articles presse": d["press"]["count"],
                "Mentions TV/Radio": tv.get("count", 0),
                "Google Trends": d["trends_score"],
                "YouTube": yt_info,
                "Score": d["score"]["total"]
            }
            
            if d["wikipedia"].get("error"):
                row["Erreur Wiki"] = d["wikipedia"]["error"]
            
            debug_rows.append(row)
        
        st.dataframe(pd.DataFrame(debug_rows), use_container_width=True, hide_index=True)
    
    # === ARTICLES ===
    st.markdown("---")
    st.markdown("## Articles de presse")
    
    for rank, (cid, d) in enumerate(sorted_data, 1):
        arts = d["press"]["articles"]
        with st.expander(f"{rank}. {d['info']['name']} — {len(arts)} article(s)"):
            if arts:
                for i, a in enumerate(arts[:20], 1):
                    st.markdown(f"**{i}.** [{a['title']}]({a['url']})")
                    st.caption(f"{a['date']} · {a['domain']} · {a['source']}")
                if len(arts) > 20:
                    st.info(f"+ {len(arts) - 20} autres articles")
            else:
                st.info("Aucun article trouvé pour cette période")
    
    # === YOUTUBE ===
    st.markdown("---")
    st.markdown("## Vidéos YouTube")
    
    # Debug YouTube
    youtube_available = any(d["youtube"].get("available", False) for _, d in sorted_data)
    has_yt_key = yt_key and yt_key.strip().startswith("AIza")
    
    if not youtube_available:
        if has_yt_key:
            # Afficher les erreurs
            errors = []
            quota_exceeded = False
            for cid, d in sorted_data:
                yt = d["youtube"]
                if yt.get("error"):
                    err = yt["error"]
                    # Détecter quota dépassé
                    if "quota" in err.lower() or "exceeded" in err.lower():
                        quota_exceeded = True
                    else:
                        errors.append(f"{d['info']['name']}: {err}")
            
            if quota_exceeded:
                st.warning("⚠️ Quota YouTube dépassé — réessayez demain (après 9h)")
            elif errors:
                st.warning("Erreurs YouTube:\n" + "\n".join(errors))
            else:
                st.info("Aucune vidéo trouvée pour les 30 derniers jours")
        else:
            st.info("Entrez une clé API YouTube dans la barre latérale pour activer")
    else:
        for rank, (cid, d) in enumerate(sorted_data, 1):
            yt = d["youtube"]
            if yt.get("available") and yt.get("videos"):
                shorts = yt.get("shorts_count", 0)
                longs = yt.get("long_count", 0)
                label = f"{rank}. {d['info']['name']} — {format_num(yt['total_views'])} vues ({longs} vidéos, {shorts} shorts)"
                
                with st.expander(label):
                    for i, v in enumerate(yt["videos"][:15], 1):
                        views = v.get("views", 0)
                        is_short = v.get("is_short", False)
                        duration = v.get("duration", "")
                        pub_date = v.get("published", "")
                        
                        # Formater la durée
                        duration_str = _format_duration(duration) if duration else ""
                        type_label = "[Short]" if is_short else f"[{duration_str}]" if duration_str else ""
                        
                        st.markdown(f"**{i}.** [{v['title']}]({v['url']}) — {format_num(views)} vues {type_label}")
                        st.caption(f"Publié le {pub_date} · {v.get('channel', '')}")

    # Footer
    st.markdown("---")
    st.caption(f"Visibility Index v7.0 · Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
    
    # === SUGGESTIONS D'AMÉLIORATION ===
    with st.expander("Suggestions d'amélioration"):
        st.markdown("""
        **Sources de données supplémentaires possibles :**
        - Twitter/X API : Mentions, engagement, followers (API payante)
        - LinkedIn : Activité des comptes politiques
        - Données INA officielles : Temps d'antenne TV/radio précis
        - Sondages officiels : Intégration automatique quand disponibles
        
        **Améliorations techniques :**
        - Système d'alertes par email sur changements significatifs
        - Export PDF automatique des rapports
        - Analyse de sentiment des articles (positif/négatif/neutre)
        - Base de données cloud pour l'historique (persistance)
        
        **Nouveaux candidats potentiels :**
        - Rémi Féraud (PS)
        - Autres candidats déclarés
        """)


if __name__ == "__main__":
    main()
