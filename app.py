"""
═══════════════════════════════════════════════════════════════════════════════
VISIBILITY INDEX v5.0 - Municipales Paris 2026
═══════════════════════════════════════════════════════════════════════════════

PRINCIPE : Données réelles uniquement. Jamais d'invention.

SOURCES UTILISÉES :
┌─────────────────┬────────────┬─────────────────────────────────────────────┐
│ Source          │ Fiabilité  │ Notes                                       │
├─────────────────┼────────────┼─────────────────────────────────────────────┤
│ Wikipedia       │ 🟢 100%    │ API officielle Wikimedia                    │
│ GDELT           │ 🟢 95%     │ Base mondiale d'articles                    │
│ Google News     │ 🟢 90%     │ Flux RSS officiel                           │
│ Google Trends   │ 🟡 75%     │ API non-officielle (pytrends)               │
│ YouTube + clé   │ 🟢 100%    │ API officielle Google                       │
│ YouTube sans clé│ ❌ 0%      │ Pas de données (on n'invente pas)           │
│ Twitter/Facebook│ ❌ N/A     │ APIs payantes - non disponibles             │
└─────────────────┴────────────┴─────────────────────────────────────────────┘

VERSION : 5.0
═══════════════════════════════════════════════════════════════════════════════
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import requests
import time
import json
import re
import math
from typing import Optional, Dict, List, Any, Tuple
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET

# =============================================================================
# CONFIGURATION STREAMLIT
# =============================================================================

st.set_page_config(
    page_title="Visibility Index v5 - Paris 2026",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# STYLES CSS
# =============================================================================

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1a365d 0%, #2c5282 50%, #2b6cb0 100%);
        color: white;
        padding: 30px;
        border-radius: 16px;
        margin-bottom: 25px;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    }
    .main-header h1 {
        margin: 0;
        font-size: 2rem;
        font-weight: 700;
    }
    .main-header p {
        margin: 10px 0 0 0;
        opacity: 0.9;
    }
    
    .alert-warning {
        background: #fef3c7;
        border: 1px solid #f59e0b;
        border-radius: 10px;
        padding: 15px;
        margin: 15px 0;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# TYPES (dicts simples pour compatibilité cache Streamlit)
# =============================================================================

# Fiabilité : "high", "medium", "low", "none"
# DataSource format: {"name": str, "data": dict, "reliability": str, "message": str}

# =============================================================================
# CANDIDATS
# =============================================================================

CANDIDATES: Dict[str, Dict] = {
    "rachida_dati": {
        "name": "Rachida Dati",
        "short_name": "Dati",
        "party": "LR / Renaissance",
        "role": "Ministre de la Culture, Maire du 7e",
        "color": "#0066CC",
        "wikipedia_fr": "Rachida_Dati",
        "emoji": "👩‍⚖️"
    },
    "emmanuel_gregoire": {
        "name": "Emmanuel Grégoire",
        "short_name": "Grégoire",
        "party": "PS",
        "role": "1er adjoint Mairie de Paris",
        "color": "#FF69B4",
        "wikipedia_fr": "Emmanuel_Grégoire",
        "emoji": "👨‍💼"
    },
    "pierre_yves_bournazel": {
        "name": "Pierre-Yves Bournazel",
        "short_name": "Bournazel",
        "party": "Horizons",
        "role": "Conseiller de Paris",
        "color": "#FF6B35",
        "wikipedia_fr": "Pierre-Yves_Bournazel",
        "emoji": "👨‍💼"
    },
    "david_belliard": {
        "name": "David Belliard",
        "short_name": "Belliard",
        "party": "EELV",
        "role": "Adjoint transports et mobilités",
        "color": "#00A86B",
        "wikipedia_fr": "David_Belliard",
        "emoji": "🌿"
    },
    "sophia_chikirou": {
        "name": "Sophia Chikirou",
        "short_name": "Chikirou",
        "party": "LFI",
        "role": "Députée de Paris",
        "color": "#C9462C",
        "wikipedia_fr": "Sophia_Chikirou",
        "emoji": "👩‍💼"
    },
    "thierry_mariani": {
        "name": "Thierry Mariani",
        "short_name": "Mariani",
        "party": "RN",
        "role": "Député européen",
        "color": "#0D2C54",
        "wikipedia_fr": "Thierry_Mariani",
        "emoji": "👨‍💼"
    }
}

# =============================================================================
# UTILITAIRES
# =============================================================================

def normalize_title(title: str) -> str:
    if not title:
        return ""
    return re.sub(r'[^\w\s]', '', title.lower())[:50].strip()

def format_number(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n/1_000:.1f}k"
    return str(n)

# =============================================================================
# WIKIPEDIA API - 100% FIABLE
# =============================================================================

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_wikipedia_data(page_title: str, start_date: date, end_date: date) -> Dict:
    """API officielle Wikimedia - 100% fiable."""
    try:
        extended_start = start_date - timedelta(days=30)
        
        url = (
            f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
            f"fr.wikipedia/all-access/user/{quote_plus(page_title)}/daily/"
            f"{extended_start.strftime('%Y%m%d')}/{end_date.strftime('%Y%m%d')}"
        )
        
        headers = {"User-Agent": "VisibilityIndex/5.0 (Educational Project)"}
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            
            period_views = 0
            period_days = 0
            reference_views = 0
            reference_days = 0
            daily_data = {}
            
            for item in items:
                ts = item.get("timestamp", "")[:8]
                views = item.get("views", 0)
                
                try:
                    item_date = datetime.strptime(ts, "%Y%m%d").date()
                    date_str = item_date.strftime("%Y-%m-%d")
                    daily_data[date_str] = views
                    
                    if start_date <= item_date <= end_date:
                        period_views += views
                        period_days += 1
                    elif extended_start <= item_date < start_date:
                        reference_views += views
                        reference_days += 1
                except ValueError:
                    continue
            
            period_avg = period_views / max(period_days, 1)
            reference_avg = reference_views / max(reference_days, 1)
            
            variation = 0.0
            if reference_avg > 0:
                variation = ((period_avg - reference_avg) / reference_avg) * 100
            
            return {
                "name": "Wikipedia",
                "data": {
                    "total_views": period_views,
                    "daily_average": round(period_avg),
                    "variation_percent": round(variation, 1),
                    "period_days": period_days,
                    "timeseries": daily_data
                },
                "reliability": "high",
                "message": "API Wikimedia officielle"
            }
        
        return {
            "name": "Wikipedia",
            "data": {"total_views": 0, "daily_average": 0, "variation_percent": 0, "timeseries": {}},
            "reliability": "none",
            "message": f"Erreur HTTP {response.status_code}"
        }
    
    except Exception as e:
        return {
            "name": "Wikipedia",
            "data": {"total_views": 0, "daily_average": 0, "variation_percent": 0, "timeseries": {}},
            "reliability": "none",
            "message": f"Erreur: {str(e)[:40]}"
        }

# =============================================================================
# GDELT + GOOGLE NEWS - PRESSE
# =============================================================================

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_gdelt_articles(search_term: str, start_date: date, end_date: date) -> List[Dict]:
    """GDELT API - Base de données d'articles mondiale."""
    articles = []
    
    try:
        query = f'"{search_term}"'
        url = "https://api.gdeltproject.org/api/v2/doc/doc"
        params = {
            "query": query,
            "mode": "ArtList",
            "format": "json",
            "maxrecords": 250,
            "startdatetime": start_date.strftime("%Y%m%d000000"),
            "enddatetime": end_date.strftime("%Y%m%d235959"),
            "sourcelang": "french"
        }
        
        response = requests.get(url, params=params, timeout=25)
        
        if response.status_code == 200:
            text = response.text.strip()
            if text:
                try:
                    data = json.loads(text)
                    raw_articles = data.get("articles", [])
                    
                    name_lower = search_term.lower()
                    name_parts = name_lower.split()
                    
                    for art in raw_articles:
                        title = art.get("title", "")
                        title_lower = title.lower()
                        
                        # Vérifier que le nom apparaît
                        if len(name_parts) >= 2:
                            if name_lower in title_lower or name_parts[-1] in title_lower:
                                articles.append({
                                    "title": title,
                                    "url": art.get("url", ""),
                                    "domain": art.get("domain", ""),
                                    "date": art.get("seendate", "")[:10] if art.get("seendate") else "",
                                    "source": "GDELT"
                                })
                except json.JSONDecodeError:
                    pass
    except Exception:
        pass
    
    return articles


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_google_news_articles(search_term: str) -> List[Dict]:
    """Google News RSS - Feed officiel."""
    articles = []
    
    try:
        encoded_term = quote_plus(f'"{search_term}"')
        url = f"https://news.google.com/rss/search?q={encoded_term}&hl=fr&gl=FR&ceid=FR:fr"
        
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            
            for item in root.findall(".//item"):
                title_elem = item.find("title")
                link_elem = item.find("link")
                pubdate_elem = item.find("pubDate")
                source_elem = item.find("source")
                
                title = title_elem.text if title_elem is not None else ""
                
                date_str = ""
                if pubdate_elem is not None and pubdate_elem.text:
                    try:
                        dt = datetime.strptime(pubdate_elem.text[:25], "%a, %d %b %Y %H:%M:%S")
                        date_str = dt.strftime("%Y-%m-%d")
                    except ValueError:
                        pass
                
                articles.append({
                    "title": title,
                    "url": link_elem.text if link_elem is not None else "",
                    "domain": source_elem.text if source_elem is not None else "Google News",
                    "date": date_str,
                    "source": "Google News"
                })
    except Exception:
        pass
    
    return articles


def fetch_all_press_articles(search_term: str, start_date: date, end_date: date) -> Dict:
    """Combine GDELT + Google News avec déduplication."""
    gdelt_articles = fetch_gdelt_articles(search_term, start_date, end_date)
    gnews_articles = fetch_google_news_articles(search_term)
    
    all_articles = gdelt_articles + gnews_articles
    
    seen_titles = set()
    unique_articles = []
    domains = set()
    
    for art in all_articles:
        title_norm = normalize_title(art.get("title", ""))
        
        if title_norm and title_norm not in seen_titles:
            seen_titles.add(title_norm)
            unique_articles.append(art)
            
            domain = art.get("domain", "")
            if domain:
                domains.add(domain)
    
    unique_articles.sort(key=lambda x: x.get("date", ""), reverse=True)
    
    return {
        "name": "Presse",
        "data": {
            "article_count": len(unique_articles),
            "domain_count": len(domains),
            "articles": unique_articles,
            "domains": list(domains),
            "gdelt_count": len(gdelt_articles),
            "gnews_count": len(gnews_articles)
        },
        "reliability": "high" if unique_articles else "medium",
        "message": f"{len(gdelt_articles)} GDELT + {len(gnews_articles)} GNews → {len(unique_articles)} uniques"
    }

# =============================================================================
# YOUTUBE DATA API
# =============================================================================

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_youtube_data(search_term: str, api_key: Optional[str] = None) -> Dict:
    """
    YouTube Data API v3 - Nécessite clé API (gratuite).
    Sans clé = pas de données (on n'invente rien).
    """
    if not api_key:
        return {
            "name": "YouTube",
            "data": {"available": False, "video_count": 0, "total_views": 0, "videos": []},
            "reliability": "none",
            "message": "Clé API requise (gratuite sur console.cloud.google.com)"
        }
    
    try:
        # Recherche
        search_url = "https://www.googleapis.com/youtube/v3/search"
        search_params = {
            "part": "snippet",
            "q": search_term,
            "type": "video",
            "order": "date",
            "maxResults": 50,
            "regionCode": "FR",
            "relevanceLanguage": "fr",
            "publishedAfter": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00Z"),
            "key": api_key
        }
        
        response = requests.get(search_url, params=search_params, timeout=15)
        
        if response.status_code == 403:
            return {
                "name": "YouTube",
                "data": {"available": False, "video_count": 0, "total_views": 0, "videos": []},
                "reliability": "none",
                "message": "Quota API dépassé ou clé invalide"
            }
        
        if response.status_code != 200:
            return {
                "name": "YouTube",
                "data": {"available": False, "video_count": 0, "total_views": 0, "videos": []},
                "reliability": "none",
                "message": f"Erreur HTTP {response.status_code}"
            }
        
        search_data = response.json()
        items = search_data.get("items", [])
        
        videos = []
        video_ids = []
        name_parts = search_term.lower().split()
        
        for item in items:
            snippet = item.get("snippet", {})
            video_id = item.get("id", {}).get("videoId", "")
            title = snippet.get("title", "")
            title_lower = title.lower()
            
            if any(part in title_lower for part in name_parts if len(part) > 3):
                if video_id:
                    video_ids.append(video_id)
                    videos.append({
                        "id": video_id,
                        "title": title,
                        "channel": snippet.get("channelTitle", ""),
                        "date": snippet.get("publishedAt", "")[:10],
                        "url": f"https://www.youtube.com/watch?v={video_id}"
                    })
        
        # Statistiques
        total_views = 0
        total_likes = 0
        
        if video_ids:
            stats_url = "https://www.googleapis.com/youtube/v3/videos"
            stats_params = {
                "part": "statistics",
                "id": ",".join(video_ids[:50]),
                "key": api_key
            }
            
            stats_response = requests.get(stats_url, params=stats_params, timeout=10)
            
            if stats_response.status_code == 200:
                stats_data = stats_response.json()
                
                for i, item in enumerate(stats_data.get("items", [])):
                    stats = item.get("statistics", {})
                    views = int(stats.get("viewCount", 0))
                    likes = int(stats.get("likeCount", 0))
                    
                    total_views += views
                    total_likes += likes
                    
                    if i < len(videos):
                        videos[i]["views"] = views
                        videos[i]["likes"] = likes
        
        videos.sort(key=lambda x: x.get("views", 0), reverse=True)
        
        return {
            "name": "YouTube",
            "data": {
                "available": True,
                "video_count": len(videos),
                "total_views": total_views,
                "total_likes": total_likes,
                "videos": videos
            },
            "reliability": "high",
            "message": f"{len(videos)} vidéos, {format_number(total_views)} vues"
        }
    
    except Exception as e:
        return {
            "name": "YouTube",
            "data": {"available": False, "video_count": 0, "total_views": 0, "videos": []},
            "reliability": "none",
            "message": f"Erreur: {str(e)[:40]}"
        }

# =============================================================================
# GOOGLE TRENDS
# =============================================================================

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_google_trends(keywords: List[str], timeframe: str = "today 1-m") -> Dict:
    """pytrends - API non-officielle, peut être instable."""
    try:
        from pytrends.request import TrendReq
        
        pytrends = TrendReq(hl='fr-FR', tz=60, timeout=(10, 30), retries=3, backoff_factor=0.5)
        
        kw_list = keywords[:5]
        pytrends.build_payload(kw_list, cat=0, timeframe=timeframe, geo='FR')
        df = pytrends.interest_over_time()
        
        if df.empty:
            return {
                "name": "Google Trends",
                "data": {"success": False, "results": {}},
                "reliability": "medium",
                "message": "Aucune donnée"
            }
        
        if 'isPartial' in df.columns:
            df = df.drop(columns=['isPartial'])
        
        results = {}
        for kw in kw_list:
            if kw in df.columns:
                values = df[kw].tolist()
                dates = [d.strftime("%Y-%m-%d") for d in df.index]
                
                recent_values = values[-7:] if len(values) >= 7 else values
                score = sum(recent_values) / len(recent_values) if recent_values else 0
                
                results[kw] = {
                    "score": round(score, 1),
                    "max_value": max(values) if values else 0,
                    "timeseries": dict(zip(dates, values))
                }
        
        return {
            "name": "Google Trends",
            "data": {"success": True, "results": results},
            "reliability": "medium",
            "message": f"OK pour {len(results)}/{len(kw_list)} termes"
        }
    
    except ImportError:
        return {
            "name": "Google Trends",
            "data": {"success": False, "results": {}},
            "reliability": "none",
            "message": "pytrends non installé"
        }
    except Exception as e:
        return {
            "name": "Google Trends",
            "data": {"success": False, "results": {}},
            "reliability": "none",
            "message": f"Erreur: {str(e)[:30]}"
        }

# =============================================================================
# CALCUL DU SCORE
# =============================================================================

def calculate_visibility_score(
    wikipedia_views: int,
    press_articles: int,
    press_domains: int,
    trends_score: float,
    youtube_views: int,
    youtube_available: bool
) -> Dict:
    """
    Score composite :
    - Wikipedia (35%) : Échelle log
    - Presse (40%) : Linéaire + bonus diversité
    - Trends (25%) : 0-100
    - YouTube : Bonus +15 max si dispo
    """
    
    # Wikipedia (log scale)
    wiki_score = 0
    if wikipedia_views > 0:
        wiki_score = min((math.log10(wikipedia_views) / 5) * 100, 100)
    
    # Presse
    press_base = min((press_articles / 100) * 80, 80)
    diversity_bonus = min((press_domains / 30) * 20, 20)
    press_score = press_base + diversity_bonus
    
    # Trends
    trends_score_norm = min(max(trends_score, 0), 100)
    
    # Score de base
    base_score = (
        wiki_score * 0.35 +
        press_score * 0.40 +
        trends_score_norm * 0.25
    )
    
    # Bonus YouTube
    youtube_bonus = 0
    if youtube_available and youtube_views > 0:
        youtube_bonus = min((math.log10(youtube_views) / 7) * 15, 15)
    
    total_score = min(base_score + youtube_bonus, 100)
    
    return {
        "total": round(total_score, 1),
        "base_score": round(base_score, 1),
        "components": {
            "wikipedia": round(wiki_score, 1),
            "press": round(press_score, 1),
            "trends": round(trends_score_norm, 1),
            "youtube_bonus": round(youtube_bonus, 1)
        },
        "contributions": {
            "wikipedia": round(wiki_score * 0.35, 1),
            "press": round(press_score * 0.40, 1),
            "trends": round(trends_score_norm * 0.25, 1),
            "youtube": round(youtube_bonus, 1)
        }
    }

# =============================================================================
# COLLECTE
# =============================================================================

def collect_all_data(
    candidate_ids: List[str],
    start_date: date,
    end_date: date,
    youtube_api_key: Optional[str]
) -> Dict[str, Dict]:
    """Collecte toutes les données."""
    
    all_data = {}
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_steps = len(candidate_ids) * 3 + 1
    current_step = 0
    
    # Google Trends (tous en une fois)
    status_text.text("📈 Google Trends...")
    candidate_names = [CANDIDATES[cid]["name"] for cid in candidate_ids]
    trends_data = fetch_google_trends(candidate_names)
    current_step += 1
    progress_bar.progress(current_step / total_steps)
    
    for cid in candidate_ids:
        candidate = CANDIDATES[cid]
        name = candidate["name"]
        
        # Wikipedia
        status_text.text(f"📚 {name}...")
        wiki_data = fetch_wikipedia_data(candidate["wikipedia_fr"], start_date, end_date)
        current_step += 1
        progress_bar.progress(current_step / total_steps)
        
        # Presse
        status_text.text(f"📰 {name}...")
        press_data = fetch_all_press_articles(name, start_date, end_date)
        current_step += 1
        progress_bar.progress(current_step / total_steps)
        
        # YouTube
        status_text.text(f"🎬 {name}...")
        youtube_data = fetch_youtube_data(name, youtube_api_key)
        current_step += 1
        progress_bar.progress(current_step / total_steps)
        
        # Trends pour ce candidat
        trends_score = 0
        trends_timeseries = {}
        if trends_data["data"].get("success"):
            candidate_trends = trends_data["data"]["results"].get(name, {})
            trends_score = candidate_trends.get("score", 0)
            trends_timeseries = candidate_trends.get("timeseries", {})
        
        # Score
        score = calculate_visibility_score(
            wikipedia_views=wiki_data["data"].get("total_views", 0),
            press_articles=press_data["data"].get("article_count", 0),
            press_domains=press_data["data"].get("domain_count", 0),
            trends_score=trends_score,
            youtube_views=youtube_data["data"].get("total_views", 0),
            youtube_available=youtube_data["data"].get("available", False)
        )
        
        all_data[cid] = {
            "info": candidate,
            "wikipedia": wiki_data,
            "press": press_data,
            "youtube": youtube_data,
            "trends": {
                "score": trends_score,
                "timeseries": trends_timeseries,
                "success": trends_data["data"].get("success", False)
            },
            "score": score
        }
    
    progress_bar.empty()
    status_text.empty()
    
    return all_data

# =============================================================================
# INTERFACE
# =============================================================================

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🗳️ Visibility Index v5.0</h1>
        <p>Analyse de visibilité • Municipales Paris 2026 • Données fiables uniquement</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown("## ⚙️ Configuration")
        
        # Période
        st.markdown("### 📅 Période")
        end_date = st.date_input("Date de fin", value=date.today(), max_value=date.today())
        period_days = st.selectbox("Durée", [7, 14, 30], format_func=lambda x: f"{x} jours")
        start_date = end_date - timedelta(days=period_days - 1)
        st.info(f"📆 {start_date.strftime('%d/%m')} → {end_date.strftime('%d/%m/%Y')}")
        
        # Candidats
        st.markdown("### 👥 Candidats")
        all_ids = list(CANDIDATES.keys())
        selected_ids = st.multiselect(
            "Sélection",
            all_ids,
            default=all_ids,
            format_func=lambda x: f"{CANDIDATES[x]['emoji']} {CANDIDATES[x]['short_name']}"
        )
        
        # YouTube
        st.markdown("### 🔑 YouTube API")
        youtube_key = st.text_input("Clé API", type="password", help="Gratuite sur console.cloud.google.com")
        if not youtube_key:
            st.caption("⚠️ Sans clé = pas de YouTube")
        
        st.markdown("---")
        if st.button("🔄 Actualiser", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        st.markdown("---")
        st.markdown("""
        ### 📊 Sources
        - 🟢 Wikipedia : 100%
        - 🟢 Presse : 95%
        - 🟡 Trends : 75%
        - ⚙️ YouTube : Clé requise
        """)
    
    if not selected_ids:
        st.warning("Sélectionnez au moins un candidat")
        return
    
    # Collecte
    all_data = collect_all_data(selected_ids, start_date, end_date, youtube_key if youtube_key else None)
    
    # Tri
    sorted_data = sorted(all_data.items(), key=lambda x: x[1]["score"]["total"], reverse=True)
    
    youtube_available = youtube_key and any(d["youtube"]["data"].get("available") for d in all_data.values())
    
    # État sources
    st.markdown("### 📡 État des sources")
    cols = st.columns(4)
    with cols[0]:
        st.markdown("🟢 **Wikipedia**")
    with cols[1]:
        st.markdown("🟢 **Presse**")
    with cols[2]:
        trends_ok = any(d["trends"]["success"] for d in all_data.values())
        st.markdown(f"{'🟢' if trends_ok else '🟡'} **Trends**")
    with cols[3]:
        st.markdown(f"{'🟢' if youtube_available else '❌'} **YouTube**")
    
    if not youtube_available:
        st.markdown("""
        <div class="alert-warning">
        ⚠️ <strong>YouTube désactivé</strong> - Ajoutez une clé API gratuite pour les vraies données YouTube
        </div>
        """, unsafe_allow_html=True)
    
    # Métriques
    st.markdown("---")
    st.markdown("## 📈 Vue d'ensemble")
    
    leader = sorted_data[0][1]
    total_wiki = sum(d["wikipedia"]["data"].get("total_views", 0) for _, d in sorted_data)
    total_articles = sum(d["press"]["data"].get("article_count", 0) for _, d in sorted_data)
    
    cols = st.columns(4)
    with cols[0]:
        st.metric("🏆 Leader", leader["info"]["short_name"], f"{leader['score']['total']:.0f}/100")
    with cols[1]:
        st.metric("📚 Wikipedia", format_number(total_wiki))
    with cols[2]:
        st.metric("📰 Articles", str(total_articles))
    with cols[3]:
        avg = sum(d["score"]["total"] for _, d in sorted_data) / len(sorted_data)
        st.metric("📊 Moyenne", f"{avg:.0f}")
    
    # Classement
    st.markdown("---")
    st.markdown("## 🏆 Classement")
    
    rows = []
    for rank, (cid, d) in enumerate(sorted_data, 1):
        row = {
            "Rang": rank,
            "Candidat": f"{d['info']['emoji']} {d['info']['name']}",
            "Parti": d["info"]["party"],
            "Score": d["score"]["total"],
            "📚 Wiki": d["wikipedia"]["data"].get("total_views", 0),
            "📰 Articles": d["press"]["data"].get("article_count", 0),
            "📈 Trends": d["trends"]["score"],
        }
        if youtube_available:
            row["🎬 YouTube"] = d["youtube"]["data"].get("total_views", 0) if d["youtube"]["data"].get("available") else 0
        rows.append(row)
    
    df = pd.DataFrame(rows)
    
    st.dataframe(
        df,
        column_config={
            "Score": st.column_config.ProgressColumn("Score /100", min_value=0, max_value=100, format="%.0f"),
            "📚 Wiki": st.column_config.NumberColumn("📚 Wikipedia", format="%d"),
            "📰 Articles": st.column_config.NumberColumn("📰 Presse", format="%d"),
        },
        hide_index=True,
        use_container_width=True
    )
    
    # Visualisations
    st.markdown("---")
    st.markdown("## 📊 Visualisations")
    
    tabs = st.tabs(["📊 Scores", "📚 Wikipedia", "📰 Presse", "📈 Trends", "📋 Articles"])
    
    names = [d["info"]["name"] for _, d in sorted_data]
    colors = [d["info"]["color"] for _, d in sorted_data]
    
    # TAB SCORES
    with tabs[0]:
        col1, col2 = st.columns(2)
        with col1:
            scores = [d["score"]["total"] for _, d in sorted_data]
            fig = px.bar(x=names, y=scores, title="Score de visibilité", color=names, color_discrete_sequence=colors)
            fig.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            decomp = []
            for _, d in sorted_data:
                c = d["score"]["contributions"]
                decomp.append({"Candidat": d["info"]["name"], "Wikipedia (35%)": c["wikipedia"], "Presse (40%)": c["press"], "Trends (25%)": c["trends"], "YouTube": c["youtube"]})
            
            df_decomp = pd.DataFrame(decomp)
            fig = px.bar(df_decomp, x="Candidat", y=["Wikipedia (35%)", "Presse (40%)", "Trends (25%)", "YouTube"], barmode="stack", title="Contributions")
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    # TAB WIKIPEDIA
    with tabs[1]:
        col1, col2 = st.columns(2)
        with col1:
            wiki_views = [d["wikipedia"]["data"].get("total_views", 0) for _, d in sorted_data]
            fig = px.bar(x=names, y=wiki_views, title="Pageviews Wikipedia", color=names, color_discrete_sequence=colors)
            fig.update_layout(showlegend=False, height=350)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            variations = [d["wikipedia"]["data"].get("variation_percent", 0) for _, d in sorted_data]
            fig = px.bar(x=names, y=variations, title="Variation vs 30j précédents (%)", color=variations, color_continuous_scale=["red", "gray", "green"], range_color=[-100, 100])
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)
        
        evo = []
        for cid, d in all_data.items():
            for dt, v in d["wikipedia"]["data"].get("timeseries", {}).items():
                evo.append({"Date": dt, "Candidat": d["info"]["name"], "Vues": v})
        if evo:
            df_evo = pd.DataFrame(evo)
            df_evo["Date"] = pd.to_datetime(df_evo["Date"])
            fig = px.line(df_evo, x="Date", y="Vues", color="Candidat", title="Évolution Wikipedia")
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    # TAB PRESSE
    with tabs[2]:
        col1, col2 = st.columns(2)
        with col1:
            articles = [d["press"]["data"].get("article_count", 0) for _, d in sorted_data]
            fig = px.bar(x=names, y=articles, title="Nombre d'articles", color=names, color_discrete_sequence=colors)
            fig.update_layout(showlegend=False, height=350)
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.pie(names=names, values=articles, title="Part de voix", color=names, color_discrete_sequence=colors)
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("#### Détail sources")
        src = [{"Candidat": d["info"]["name"], "GDELT": d["press"]["data"].get("gdelt_count", 0), "Google News": d["press"]["data"].get("gnews_count", 0), "Total": d["press"]["data"].get("article_count", 0)} for _, d in sorted_data]
        st.dataframe(pd.DataFrame(src), hide_index=True, use_container_width=True)
    
    # TAB TRENDS
    with tabs[3]:
        trends_ok = any(d["trends"]["success"] for _, d in sorted_data)
        if trends_ok:
            col1, col2 = st.columns(2)
            with col1:
                ts = [d["trends"]["score"] for _, d in sorted_data]
                fig = px.bar(x=names, y=ts, title="Google Trends (moy. 7j)", color=names, color_discrete_sequence=colors)
                fig.update_layout(showlegend=False, height=350)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                evo = []
                for cid, d in all_data.items():
                    for dt, v in d["trends"].get("timeseries", {}).items():
                        evo.append({"Date": dt, "Candidat": d["info"]["name"], "Intérêt": v})
                if evo:
                    df_t = pd.DataFrame(evo)
                    df_t["Date"] = pd.to_datetime(df_t["Date"])
                    fig = px.line(df_t, x="Date", y="Intérêt", color="Candidat", title="Évolution Trends")
                    fig.update_layout(height=350)
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Google Trends indisponible (limite de requêtes)")
    
    # TAB ARTICLES
    with tabs[4]:
        st.markdown("### 📋 Tous les articles")
        for cid, d in sorted_data:
            arts = d["press"]["data"].get("articles", [])
            with st.expander(f"{d['info']['emoji']} **{d['info']['name']}** — {len(arts)} articles"):
                if arts:
                    for i, a in enumerate(arts, 1):
                        st.markdown(f"**{i}.** [{a['title']}]({a['url']})")
                        st.caption(f"📅 {a.get('date', 'N/A')} • 🌐 {a.get('domain', '')} • {a.get('source', '')}")
                else:
                    st.info("Aucun article")
    
    # YouTube
    if youtube_available:
        st.markdown("---")
        st.markdown("## 🎬 YouTube")
        for cid, d in sorted_data:
            yt = d["youtube"]
            if yt["data"].get("available"):
                with st.expander(f"{d['info']['emoji']} {d['info']['name']} — {format_number(yt["data"].get('total_views', 0))} vues"):
                    c1, c2 = st.columns(2)
                    c1.metric("Vidéos", yt["data"].get("video_count", 0))
                    c2.metric("Vues totales", format_number(yt["data"].get("total_views", 0)))
                    
                    vids = yt["data"].get("videos", [])
                    if vids:
                        st.markdown("**Top vidéos :**")
                        for v in vids[:10]:
                            st.markdown(f"- [{v['title']}]({v['url']}) — **{format_number(v.get('views', 0))} vues**")
    
    # Export
    st.markdown("---")
    st.markdown("## 📥 Export")
    
    col1, col2 = st.columns(2)
    with col1:
        csv_content = df.to_csv(index=False)
        st.download_button("📊 CSV", csv_content, f"visibility_{end_date.strftime('%Y%m%d')}.csv", use_container_width=True)
    
    with col2:
        lines = [
            "VISIBILITY INDEX v5.0 - MUNICIPALES PARIS 2026",
            f"Période: {start_date.strftime('%d/%m/%Y')} → {end_date.strftime('%d/%m/%Y')}",
            f"Sources: Wikipedia ✓ | Presse ✓ | Trends {'✓' if trends_ok else '✗'} | YouTube {'✓' if youtube_available else '✗'}",
            "",
            "CLASSEMENT:",
        ]
        for rank, (cid, d) in enumerate(sorted_data, 1):
            m = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"{rank}.")
            lines.append(f"{m} {d['info']['name']}: {d['score']['total']:.0f}/100")
        
        lines.append("\nDÉTAILS:")
        for cid, d in sorted_data:
            lines.append(f"\n{d['info']['name']}:")
            lines.append(f"  Wikipedia: {d['wikipedia']["data"].get('total_views', 0):,} vues ({d['wikipedia']["data"].get('variation_percent', 0):+.0f}%)")
            lines.append(f"  Presse: {d['press']["data"].get('article_count', 0)} articles")
            lines.append(f"  Trends: {d['trends']['score']:.0f}")
            if d["youtube"]["data"].get("available"):
                lines.append(f"  YouTube: {d['youtube']["data"].get('total_views', 0):,} vues")
        
        lines.append(f"\nGénéré le {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        summary = "\n".join(lines)
        
        st.download_button("📝 Résumé", summary, f"summary_{end_date.strftime('%Y%m%d')}.txt", use_container_width=True)
    
    # Footer
    st.markdown("---")
    st.caption(f"Visibility Index v5.0 • {datetime.now().strftime('%H:%M')}")


if __name__ == "__main__":
    main()
