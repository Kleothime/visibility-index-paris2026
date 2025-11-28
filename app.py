"""
VISIBILITY INDEX v6.1 - Municipales Paris 2026
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
# FONCTIONS DE COLLECTE
# =============================================================================

@st.cache_data(ttl=1800, show_spinner=False)
def get_wikipedia_views(page_title: str, start_date: date, end_date: date) -> Dict:
    """Wikipedia API - 100% fiable"""
    try:
        extended_start = start_date - timedelta(days=30)
        
        url = (
            f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
            f"fr.wikipedia/all-access/user/{quote_plus(page_title)}/daily/"
            f"{extended_start.strftime('%Y%m%d')}/{end_date.strftime('%Y%m%d')}"
        )
        
        response = requests.get(url, headers={"User-Agent": "VisibilityIndex/6.1"}, timeout=15)
        
        if response.status_code != 200:
            return {"views": 0, "variation": 0, "daily": {}, "error": f"HTTP {response.status_code}"}
        
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
                elif extended_start <= item_date < start_date:
                    reference_views += views
            except:
                continue
        
        days_period = (end_date - start_date).days + 1
        days_ref = 30
        
        avg_period = period_views / max(days_period, 1)
        avg_ref = reference_views / max(days_ref, 1)
        
        variation = 0
        if avg_ref > 0:
            variation = ((avg_period - avg_ref) / avg_ref) * 100
        
        return {
            "views": period_views,
            "variation": round(variation, 1),
            "daily": daily,
            "error": None
        }
    
    except Exception as e:
        return {"views": 0, "variation": 0, "daily": {}, "error": str(e)[:50]}


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
        return {"available": False, "videos": [], "total_views": 0}
    
    try:
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
        
        try:
            response1 = requests.get(search_url, params=params_relevance, timeout=15)
        except Exception:
            response1 = None
        
        if response1 and response1.status_code == 200:
            for item in response1.json().get("items", []):
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
        
        # Recherche 2 : Par nombre de vues
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
        except Exception:
            response2 = None
        
        if response2 and response2.status_code == 200:
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
        
        # Vérifier si au moins une requête a réussi
        r1_ok = response1 and response1.status_code == 200
        r2_ok = response2 and response2.status_code == 200
        
        if not r1_ok and not r2_ok:
            error_code = response1.status_code if response1 else "timeout"
            return {"available": False, "videos": [], "total_views": 0, "error": f"Erreur: {error_code}"}
        
        # Filtrer par nom dans le titre
        name_parts = search_term.lower().split()
        filtered_videos = []
        video_ids = []
        
        for v in all_videos:
            title_lower = v["title"].lower()
            if any(part in title_lower for part in name_parts if len(part) > 3):
                video_ids.append(v["id"])
                filtered_videos.append({
                    "id": v["id"],
                    "title": v["title"],
                    "channel": v["channel"],
                    "published": v["published"],
                    "url": f"https://www.youtube.com/watch?v={v['id']}"
                })
        
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
    
    except Exception as e:
        return {"available": False, "videos": [], "total_views": 0, "error": str(e)[:50]}


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
        youtube = get_youtube_data(name, youtube_key, start_date, end_date) if youtube_key else {"available": False, "total_views": 0, "videos": []}
        
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
    st.markdown("# Visibility Index v6.1")
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
        
        if not yt_key:
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
        if d["youtube"]["available"]:
            row["Vues YouTube"] = d["youtube"]["total_views"]
        rows.append(row)
    
    df = pd.DataFrame(rows)
    
    col_config = {
        "Rang": st.column_config.NumberColumn("Rang", format="%d"),
        "Score": st.column_config.ProgressColumn("Score /100", min_value=0, max_value=100, format="%.1f"),
        "Wikipedia": st.column_config.NumberColumn("Wikipedia", format="%d"),
        "Articles": st.column_config.NumberColumn("Presse", format="%d"),
        "Google Trends": st.column_config.NumberColumn("Google Trends", format="%.0f"),
    }
    
    if any(d["youtube"]["available"] for _, d in sorted_data):
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
    
    tab1, tab2, tab3, tab4 = st.tabs(["Scores", "Wikipedia", "Presse", "Données brutes"])
    
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
    
    with tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            wiki_views = [d["wikipedia"]["views"] for _, d in sorted_data]
            fig = px.bar(x=names, y=wiki_views, color=names, color_discrete_sequence=colors,
                        title="Vues Wikipedia (période)")
            fig.update_layout(showlegend=False)
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
                        title="Variation vs 30 jours précédents (%)")
            fig.update_layout(yaxis_range=[-100, 100])
            st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
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
    
    with tab4:
        debug_rows = []
        for rank, (cid, d) in enumerate(sorted_data, 1):
            row = {
                "Rang": rank,
                "Candidat": d["info"]["name"],
                "Wikipedia (vues)": d["wikipedia"]["views"],
                "Variation (%)": f"{max(min(d['wikipedia']['variation'], 100), -100):+.0f}%",
                "Articles bruts": d["press"]["raw_count"],
                "Après filtre date": d["press"].get("date_filtered_count", d["press"]["raw_count"]),
                "Articles filtrés": d["press"]["count"],
                "Sources": d["press"]["domains"],
                "Google Trends": d["trends_score"],
                "Vues YouTube": d["youtube"].get("total_views", 0) if d["youtube"]["available"] else "-",
                "Score": d["score"]["total"]
            }
            
            if d["wikipedia"].get("error"):
                row["Erreur"] = d["wikipedia"]["error"]
            
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
    if any(d["youtube"]["available"] for _, d in sorted_data):
        st.markdown("---")
        st.markdown("## Vidéos YouTube")
        
        for rank, (cid, d) in enumerate(sorted_data, 1):
            yt = d["youtube"]
            if yt["available"] and yt["videos"]:
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
    st.caption(f"Visibility Index v6.1 · Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
    
    # === SUGGESTIONS D'AMÉLIORATION ===
    with st.expander("Suggestions d'amélioration"):
        st.markdown("""
        **Sources de données supplémentaires possibles :**
        - Twitter/X API : Mentions, engagement, followers (API payante)
        - LinkedIn : Activité des comptes politiques
        - Sondages : Intégrer les derniers sondages d'intentions de vote
        - Médias audiovisuels : Passages TV/radio (données INA)
        
        **Améliorations techniques :**
        - Système d'alertes par email sur changements significatifs
        - Export PDF automatique des rapports
        - Comparaison historique (évolution sur plusieurs semaines)
        - Analyse de sentiment des articles (positif/négatif/neutre)
        
        **Nouveaux candidats potentiels :**
        - Rémi Féraud (PS)
        - Autres candidats déclarés
        """)


if __name__ == "__main__":
    main()
