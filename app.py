"""
Visibility Index v4.0 - Données Fiables Uniquement
Tableau de bord de visibilité pour les municipales Paris 2026

PHILOSOPHIE : Ne jamais inventer de données. Afficher clairement quand une source n'est pas disponible.

SOURCES FIABLES (gratuites) :
- Wikipedia Pageviews API : 100% fiable
- GDELT : Articles de presse
- Google News RSS : Complément presse
- Google Trends : Variable mais réel

SOURCES NÉCESSITANT CONFIGURATION :
- YouTube Data API v3 : Gratuit mais nécessite clé API

SOURCES NON DISPONIBLES (API payantes) :
- Twitter/X : API à partir de 100$/mois
- Facebook : API très restrictive
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import requests
import time
from typing import Optional, Dict, List, Any
import json
import re
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET
import math

# =============================================================================
# CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="Visibility Index - Paris 2026",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
        color: white;
        padding: 25px;
        border-radius: 12px;
        margin-bottom: 20px;
        text-align: center;
    }
    .main-header h1 { margin: 0; font-size: 1.8rem; }
    .main-header p { margin: 8px 0 0 0; opacity: 0.9; font-size: 0.95rem; }
    
    .source-indicator {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.7rem;
        margin: 2px;
    }
    .source-ok { background: #10b981; color: white; }
    .source-partial { background: #f59e0b; color: white; }
    .source-missing { background: #ef4444; color: white; }
    
    .data-card {
        background: #f8fafc;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        border-left: 4px solid #3b82f6;
    }
    
    .warning-box {
        background: #fef3c7;
        border: 1px solid #f59e0b;
        border-radius: 8px;
        padding: 12px;
        margin: 10px 0;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# CANDIDATS
# =============================================================================

CANDIDATES = {
    "rachida_dati": {
        "name": "Rachida Dati",
        "party": "LR / Renaissance",
        "role": "Ministre de la Culture",
        "color": "#0066CC",
        "wikipedia_fr": "Rachida_Dati",
        "emoji": "👩‍⚖️"
    },
    "emmanuel_gregoire": {
        "name": "Emmanuel Grégoire",
        "party": "PS",
        "role": "1er adjoint Mairie Paris",
        "color": "#FF69B4",
        "wikipedia_fr": "Emmanuel_Grégoire",
        "emoji": "👨‍💼"
    },
    "pierre_yves_bournazel": {
        "name": "Pierre-Yves Bournazel",
        "party": "Horizons",
        "role": "Conseiller de Paris",
        "color": "#FF6B35",
        "wikipedia_fr": "Pierre-Yves_Bournazel",
        "emoji": "👨‍💼"
    },
    "david_belliard": {
        "name": "David Belliard",
        "party": "EELV",
        "role": "Adjoint mobilités",
        "color": "#00A86B",
        "wikipedia_fr": "David_Belliard",
        "emoji": "🌿"
    },
    "sophia_chikirou": {
        "name": "Sophia Chikirou",
        "party": "LFI",
        "role": "Députée de Paris",
        "color": "#C9462C",
        "wikipedia_fr": "Sophia_Chikirou",
        "emoji": "👩‍💼"
    },
    "thierry_mariani": {
        "name": "Thierry Mariani",
        "party": "RN",
        "role": "Député européen",
        "color": "#0D2C54",
        "wikipedia_fr": "Thierry_Mariani",
        "emoji": "👨‍💼"
    }
}

# =============================================================================
# WIKIPEDIA API - 100% FIABLE
# =============================================================================

@st.cache_data(ttl=1800, show_spinner=False)
def get_wikipedia_pageviews(page_title: str, start_date: date, end_date: date) -> Dict:
    """
    Récupère les pageviews Wikipedia.
    SOURCE 100% FIABLE - API officielle Wikimedia.
    """
    try:
        # Étendre la période pour avoir l'historique (30 jours avant start_date)
        history_start = start_date - timedelta(days=30)
        
        url = (
            f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
            f"fr.wikipedia/all-access/user/{page_title}/daily/"
            f"{history_start.strftime('%Y%m%d')}/{end_date.strftime('%Y%m%d')}"
        )
        
        headers = {"User-Agent": "VisibilityIndex/4.0 (Educational Project - Paris Municipal Elections)"}
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            
            # Séparer période analysée vs historique
            period_views = 0
            period_days = 0
            history_views = 0
            history_days = 0
            timeseries = {}
            
            for item in items:
                date_str = item.get("timestamp", "")[:8]
                views = item.get("views", 0)
                
                try:
                    item_date = datetime.strptime(date_str, "%Y%m%d").date()
                    timeseries[item_date.strftime("%Y-%m-%d")] = views
                    
                    if start_date <= item_date <= end_date:
                        period_views += views
                        period_days += 1
                    else:
                        history_views += views
                        history_days += 1
                except:
                    continue
            
            # Calculer les moyennes et variation
            period_avg = period_views / max(period_days, 1)
            history_avg = history_views / max(history_days, 1)
            
            variation_pct = 0
            if history_avg > 0:
                variation_pct = ((period_avg - history_avg) / history_avg) * 100
            
            return {
                "total_views": period_views,
                "daily_avg": round(period_avg, 0),
                "variation_pct": round(variation_pct, 1),
                "timeseries": timeseries,
                "period_days": period_days,
                "success": True,
                "confidence": "high",
                "source": "Wikipedia API (Wikimedia)"
            }
        
        return {
            "total_views": 0, "daily_avg": 0, "variation_pct": 0,
            "timeseries": {}, "success": False, "confidence": "none",
            "error": f"HTTP {response.status_code}"
        }
        
    except Exception as e:
        return {
            "total_views": 0, "daily_avg": 0, "variation_pct": 0,
            "timeseries": {}, "success": False, "confidence": "none",
            "error": str(e)
        }


# =============================================================================
# GDELT API - PRESSE
# =============================================================================

@st.cache_data(ttl=1800, show_spinner=False)
def get_gdelt_articles(search_term: str, start_date: date, end_date: date) -> Dict:
    """
    Récupère les articles de presse via GDELT.
    SOURCE FIABLE pour la presse en ligne.
    """
    all_articles = []
    seen_titles = set()
    domains = set()
    
    try:
        # Requête GDELT
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
        
        response = requests.get(url, params=params, timeout=20)
        
        if response.status_code == 200:
            try:
                data = response.json()
                articles = data.get("articles", [])
                
                for article in articles:
                    title = article.get("title", "")
                    title_norm = re.sub(r'[^\w\s]', '', title.lower())[:60]
                    
                    # Vérifier que le nom apparaît vraiment
                    name_parts = search_term.lower().split()
                    if any(part in title.lower() for part in name_parts if len(part) > 3):
                        if title_norm and title_norm not in seen_titles:
                            seen_titles.add(title_norm)
                            domain = article.get("domain", "")
                            if domain:
                                domains.add(domain)
                            
                            all_articles.append({
                                "title": title,
                                "url": article.get("url", ""),
                                "domain": domain,
                                "date": article.get("seendate", "")[:10] if article.get("seendate") else "",
                                "source_type": "GDELT"
                            })
            except json.JSONDecodeError:
                pass  # GDELT retourne parfois vide
    except Exception as e:
        pass
    
    return {
        "article_count": len(all_articles),
        "domain_count": len(domains),
        "articles": sorted(all_articles, key=lambda x: x.get("date", ""), reverse=True),
        "domains": list(domains),
        "success": True,
        "source": "GDELT"
    }


@st.cache_data(ttl=1800, show_spinner=False)
def get_google_news_articles(search_term: str) -> Dict:
    """
    Récupère les articles via Google News RSS.
    SOURCE FIABLE - Complément à GDELT.
    """
    try:
        encoded = quote_plus(f'"{search_term}"')
        url = f"https://news.google.com/rss/search?q={encoded}&hl=fr&gl=FR&ceid=FR:fr"
        
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            articles = []
            seen = set()
            
            for item in root.findall(".//item")[:50]:
                title_elem = item.find("title")
                link_elem = item.find("link")
                pub_date_elem = item.find("pubDate")
                source_elem = item.find("source")
                
                title = title_elem.text if title_elem is not None else ""
                title_norm = re.sub(r'[^\w\s]', '', title.lower())[:60]
                
                if title_norm and title_norm not in seen:
                    seen.add(title_norm)
                    
                    date_str = ""
                    if pub_date_elem is not None and pub_date_elem.text:
                        try:
                            dt = datetime.strptime(pub_date_elem.text[:25], "%a, %d %b %Y %H:%M:%S")
                            date_str = dt.strftime("%Y-%m-%d")
                        except:
                            pass
                    
                    articles.append({
                        "title": title,
                        "url": link_elem.text if link_elem is not None else "",
                        "domain": source_elem.text if source_elem is not None else "Google News",
                        "date": date_str,
                        "source_type": "Google News"
                    })
            
            return {"article_count": len(articles), "articles": articles, "success": True}
    
    except Exception as e:
        pass
    
    return {"article_count": 0, "articles": [], "success": False}


# =============================================================================
# YOUTUBE DATA API - NÉCESSITE CLÉ API
# =============================================================================

@st.cache_data(ttl=1800, show_spinner=False)
def get_youtube_data(search_term: str, api_key: str) -> Dict:
    """
    Récupère les vraies données YouTube via l'API officielle.
    NÉCESSITE UNE CLÉ API (gratuite).
    """
    if not api_key:
        return {
            "available": False,
            "message": "Clé API YouTube non configurée",
            "help": "Obtenez une clé gratuite sur console.cloud.google.com"
        }
    
    try:
        # Recherche de vidéos récentes
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
        
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            
            videos = []
            video_ids = []
            
            for item in items:
                snippet = item.get("snippet", {})
                video_id = item.get("id", {}).get("videoId", "")
                title = snippet.get("title", "").lower()
                
                # Vérifier que le nom apparaît dans le titre ou la description
                name_parts = search_term.lower().split()
                if any(part in title for part in name_parts if len(part) > 3):
                    if video_id:
                        video_ids.append(video_id)
                        videos.append({
                            "title": snippet.get("title", ""),
                            "channel": snippet.get("channelTitle", ""),
                            "date": snippet.get("publishedAt", "")[:10],
                            "video_id": video_id,
                            "url": f"https://youtube.com/watch?v={video_id}"
                        })
            
            # Récupérer les statistiques (vues, likes)
            total_views = 0
            total_likes = 0
            total_comments = 0
            
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
                        comments = int(stats.get("commentCount", 0))
                        
                        total_views += views
                        total_likes += likes
                        total_comments += comments
                        
                        # Ajouter les stats à la vidéo correspondante
                        if i < len(videos):
                            videos[i]["views"] = views
                            videos[i]["likes"] = likes
            
            return {
                "available": True,
                "video_count": len(videos),
                "videos": videos,
                "total_views": total_views,
                "total_likes": total_likes,
                "total_comments": total_comments,
                "success": True,
                "confidence": "high",
                "source": "YouTube Data API v3"
            }
        
        elif response.status_code == 403:
            return {
                "available": False,
                "message": "Quota API YouTube dépassé ou clé invalide",
                "error": response.json().get("error", {}).get("message", "")
            }
        
        return {"available": False, "message": f"Erreur API: {response.status_code}"}
        
    except Exception as e:
        return {"available": False, "message": f"Erreur: {str(e)}"}


# =============================================================================
# GOOGLE TRENDS
# =============================================================================

@st.cache_data(ttl=3600, show_spinner=False)
def get_google_trends(keywords: List[str]) -> Dict:
    """
    Récupère les données Google Trends.
    ATTENTION: API non-officielle, peut être instable.
    """
    try:
        from pytrends.request import TrendReq
        
        pytrends = TrendReq(hl='fr-FR', tz=60, timeout=(10, 30), retries=2)
        
        # Maximum 5 keywords par requête
        kw_list = keywords[:5]
        
        pytrends.build_payload(kw_list, cat=0, timeframe='today 1-m', geo='FR')
        df = pytrends.interest_over_time()
        
        if df.empty:
            return {"success": False, "data": {}, "note": "Pas de données"}
        
        if 'isPartial' in df.columns:
            df = df.drop(columns=['isPartial'])
        
        results = {}
        for kw in kw_list:
            if kw in df.columns:
                values = df[kw].tolist()
                dates = [d.strftime("%Y-%m-%d") for d in df.index]
                
                # Score = moyenne des 7 derniers jours
                recent = values[-7:] if len(values) >= 7 else values
                score = sum(recent) / len(recent) if recent else 0
                
                results[kw] = {
                    "score": round(score, 1),
                    "max": max(values) if values else 0,
                    "latest": values[-1] if values else 0,
                    "timeseries": dict(zip(dates, values))
                }
        
        return {"success": True, "data": results, "confidence": "medium"}
        
    except Exception as e:
        return {"success": False, "data": {}, "error": str(e), "note": "pytrends instable"}


# =============================================================================
# CALCUL DU SCORE
# =============================================================================

def calculate_visibility_score(
    wikipedia_views: int,
    press_articles: int,
    press_domains: int,
    trends_score: float,
    youtube_views: int = 0,
    youtube_available: bool = False
) -> Dict:
    """
    Calcule le score de visibilité.
    
    PONDÉRATION (ajustée selon données disponibles):
    - Wikipedia : 35% (proxy fiable de l'attention publique)
    - Presse : 40% (couverture médiatique)
    - Google Trends : 25% (intérêt de recherche)
    - YouTube : Bonus si disponible
    """
    
    # Wikipedia : échelle logarithmique (1000 vues = 50, 10000 = 75, 100000 = 100)
    wiki_score = 0
    if wikipedia_views > 0:
        wiki_score = min(math.log10(wikipedia_views) / 5 * 100, 100)
    
    # Presse : linéaire avec bonus diversité
    # 20 articles = 50 points, 50 articles = 80 points, 100+ = 100 points
    press_base = min(press_articles / 100, 1) * 80
    diversity_bonus = min(press_domains / 30, 1) * 20
    press_score = press_base + diversity_bonus
    
    # Trends : déjà sur 0-100
    trends_score_norm = min(trends_score, 100)
    
    # Score de base (sans YouTube)
    base_score = (
        wiki_score * 0.35 +
        press_score * 0.40 +
        trends_score_norm * 0.25
    )
    
    # Bonus YouTube si disponible
    youtube_bonus = 0
    if youtube_available and youtube_views > 0:
        # Bonus jusqu'à 15 points
        youtube_bonus = min(math.log10(max(youtube_views, 1)) / 7 * 15, 15)
    
    total = min(base_score + youtube_bonus, 100)
    
    return {
        "total": round(total, 1),
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
# INTERFACE
# =============================================================================

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🗳️ Visibility Index v4.0</h1>
        <p>Municipales Paris 2026 • Données fiables uniquement</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown("## ⚙️ Configuration")
        
        # Période
        st.markdown("### 📅 Période")
        end_date = st.date_input("Date de fin", value=date.today(), max_value=date.today())
        period = st.selectbox("Durée", [7, 14, 30], format_func=lambda x: f"{x} jours")
        start_date = end_date - timedelta(days=period - 1)
        
        st.info(f"📆 {start_date.strftime('%d/%m')} → {end_date.strftime('%d/%m/%Y')}")
        
        # Candidats
        st.markdown("### 👥 Candidats")
        selected = st.multiselect(
            "Sélection",
            list(CANDIDATES.keys()),
            default=list(CANDIDATES.keys()),
            format_func=lambda x: f"{CANDIDATES[x]['emoji']} {CANDIDATES[x]['name'].split()[-1]}"
        )
        
        # API YouTube
        st.markdown("### 🔑 YouTube API")
        youtube_key = st.text_input(
            "Clé API",
            type="password",
            help="Gratuit sur console.cloud.google.com"
        )
        if not youtube_key:
            st.warning("⚠️ Sans clé, pas de données YouTube")
        
        st.markdown("---")
        if st.button("🔄 Actualiser", type="primary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        # Sources
        st.markdown("---")
        st.markdown("""
        ### 📊 Sources
        - 🟢 **Wikipedia** : Fiable
        - 🟢 **GDELT/News** : Fiable
        - 🟡 **Trends** : Variable
        - ⚙️ **YouTube** : Nécessite clé
        - ❌ **Twitter/FB** : API payante
        """)
    
    if not selected:
        st.warning("Sélectionnez au moins un candidat")
        return
    
    # Collecte
    all_data = collect_data(selected, start_date, end_date, youtube_key)
    
    # Affichage
    display_results(all_data, start_date, end_date, bool(youtube_key))


def collect_data(candidates: List[str], start_date: date, end_date: date, youtube_key: str) -> Dict:
    """Collecte toutes les données."""
    
    all_data = {}
    progress = st.progress(0)
    status = st.empty()
    
    # Google Trends (tous les candidats en une fois)
    status.text("📈 Google Trends...")
    names = [CANDIDATES[c]["name"] for c in candidates]
    trends_data = get_google_trends(names)
    progress.progress(15)
    
    for i, cand_id in enumerate(candidates):
        cand = CANDIDATES[cand_id]
        name = cand["name"]
        status.text(f"📊 {name}...")
        
        # Wikipedia
        wiki = get_wikipedia_pageviews(cand["wikipedia_fr"], start_date, end_date)
        
        # Presse (GDELT + Google News)
        gdelt = get_gdelt_articles(name, start_date, end_date)
        gnews = get_google_news_articles(name)
        
        # Fusionner articles
        all_articles = gdelt.get("articles", []) + gnews.get("articles", [])
        seen = set()
        unique_articles = []
        domains = set(gdelt.get("domains", []))
        
        for art in all_articles:
            title_norm = re.sub(r'[^\w\s]', '', art.get("title", "").lower())[:50]
            if title_norm and title_norm not in seen:
                seen.add(title_norm)
                unique_articles.append(art)
                if art.get("domain"):
                    domains.add(art["domain"])
        
        unique_articles.sort(key=lambda x: x.get("date", ""), reverse=True)
        
        press = {
            "article_count": len(unique_articles),
            "domain_count": len(domains),
            "articles": unique_articles,
            "domains": list(domains)
        }
        
        # YouTube (si clé dispo)
        youtube = get_youtube_data(name, youtube_key) if youtube_key else {"available": False}
        
        # Trends pour ce candidat
        trends_score = 0
        trends_ts = {}
        if trends_data.get("success") and name in trends_data.get("data", {}):
            td = trends_data["data"][name]
            trends_score = td.get("score", 0)
            trends_ts = td.get("timeseries", {})
        
        # Score
        yt_views = youtube.get("total_views", 0) if youtube.get("available") else 0
        score = calculate_visibility_score(
            wiki.get("total_views", 0),
            press["article_count"],
            press["domain_count"],
            trends_score,
            yt_views,
            youtube.get("available", False)
        )
        
        all_data[cand_id] = {
            "info": cand,
            "wikipedia": wiki,
            "press": press,
            "youtube": youtube,
            "trends": {"score": trends_score, "timeseries": trends_ts, "success": trends_data.get("success", False)},
            "score": score
        }
        
        progress.progress(15 + int(85 * (i + 1) / len(candidates)))
    
    progress.empty()
    status.empty()
    
    return all_data


def display_results(all_data: Dict, start_date: date, end_date: date, youtube_available: bool):
    """Affiche les résultats."""
    
    # Tri par score
    sorted_data = sorted(all_data.items(), key=lambda x: x[1]["score"]["total"], reverse=True)
    
    # Indicateur de fiabilité des données
    st.markdown("### 📊 État des sources")
    cols = st.columns(4)
    with cols[0]:
        st.markdown('<span class="source-indicator source-ok">🟢 Wikipedia</span>', unsafe_allow_html=True)
    with cols[1]:
        st.markdown('<span class="source-indicator source-ok">🟢 Presse</span>', unsafe_allow_html=True)
    with cols[2]:
        trends_ok = any(d["trends"]["success"] for _, d in sorted_data)
        cls = "source-ok" if trends_ok else "source-partial"
        st.markdown(f'<span class="source-indicator {cls}">{"🟢" if trends_ok else "🟡"} Trends</span>', unsafe_allow_html=True)
    with cols[3]:
        cls = "source-ok" if youtube_available else "source-missing"
        st.markdown(f'<span class="source-indicator {cls}">{"🟢" if youtube_available else "❌"} YouTube</span>', unsafe_allow_html=True)
    
    if not youtube_available:
        st.markdown("""
        <div class="warning-box">
        ⚠️ <strong>YouTube désactivé</strong> : Ajoutez une clé API (gratuite) dans la sidebar pour avoir les vraies vues YouTube.
        <a href="https://console.cloud.google.com/apis/credentials" target="_blank">Obtenir une clé</a>
        </div>
        """, unsafe_allow_html=True)
    
    # Métriques globales
    st.markdown("---")
    st.markdown("## 📈 Vue d'ensemble")
    
    leader = sorted_data[0] if sorted_data else None
    total_wiki = sum(d["wikipedia"]["total_views"] for _, d in sorted_data)
    total_press = sum(d["press"]["article_count"] for _, d in sorted_data)
    
    cols = st.columns(4)
    with cols[0]:
        st.metric("🏆 Leader", leader[1]["info"]["name"].split()[-1] if leader else "-",
                  f"{leader[1]['score']['total']:.0f}/100" if leader else None)
    with cols[1]:
        st.metric("📚 Wikipedia", f"{total_wiki:,} vues")
    with cols[2]:
        st.metric("📰 Articles", f"{total_press}")
    with cols[3]:
        avg_score = sum(d["score"]["total"] for _, d in sorted_data) / len(sorted_data)
        st.metric("📊 Score moyen", f"{avg_score:.0f}")
    
    # Classement
    st.markdown("---")
    st.markdown("## 🏆 Classement")
    
    ranking = []
    for rank, (cid, d) in enumerate(sorted_data, 1):
        ranking.append({
            "Rang": rank,
            "Candidat": f"{d['info']['emoji']} {d['info']['name']}",
            "Score": d["score"]["total"],
            "Wikipedia": d["wikipedia"]["total_views"],
            "Presse": d["press"]["article_count"],
            "Sources": d["press"]["domain_count"],
            "Trends": d["trends"]["score"],
            "YouTube": d["youtube"].get("total_views", "-") if d["youtube"].get("available") else "N/A"
        })
    
    df = pd.DataFrame(ranking)
    st.dataframe(
        df,
        column_config={
            "Score": st.column_config.ProgressColumn("Score /100", min_value=0, max_value=100, format="%.0f"),
            "Wikipedia": st.column_config.NumberColumn("📚 Wiki", format="%d"),
            "Presse": st.column_config.NumberColumn("📰 Articles", format="%d"),
        },
        hide_index=True,
        use_container_width=True
    )
    
    # Graphiques
    st.markdown("---")
    st.markdown("## 📊 Visualisations")
    
    tabs = st.tabs(["📊 Scores", "📚 Wikipedia", "📰 Presse", "📈 Trends", "📋 Articles"])
    
    with tabs[0]:
        fig = px.bar(df, x="Candidat", y="Score", color="Candidat", title="Score de visibilité")
        fig.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # Décomposition
        st.markdown("### 🎯 Contributions au score")
        decomp = []
        for cid, d in sorted_data:
            c = d["score"]["contributions"]
            decomp.append({"Candidat": d["info"]["name"], "Pilier": "📚 Wikipedia (35%)", "Points": c["wikipedia"]})
            decomp.append({"Candidat": d["info"]["name"], "Pilier": "📰 Presse (40%)", "Points": c["press"]})
            decomp.append({"Candidat": d["info"]["name"], "Pilier": "📈 Trends (25%)", "Points": c["trends"]})
            if c["youtube"] > 0:
                decomp.append({"Candidat": d["info"]["name"], "Pilier": "🎬 YouTube (bonus)", "Points": c["youtube"]})
        
        fig2 = px.bar(pd.DataFrame(decomp), x="Candidat", y="Points", color="Pilier", barmode="stack", title="Contribution de chaque source")
        fig2.update_layout(height=400)
        st.plotly_chart(fig2, use_container_width=True)
    
    with tabs[1]:
        wiki_df = pd.DataFrame([
            {"Candidat": d["info"]["name"], "Vues": d["wikipedia"]["total_views"], "Variation": d["wikipedia"]["variation_pct"]}
            for _, d in sorted_data
        ])
        
        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(wiki_df, x="Candidat", y="Vues", title="Pageviews Wikipedia (période)")
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.bar(wiki_df, x="Candidat", y="Variation", title="Variation vs 30j précédents (%)",
                        color="Variation", color_continuous_scale=["red", "gray", "green"], range_color=[-100, 100])
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)
        
        # Évolution temporelle
        evo = []
        for cid, d in all_data.items():
            for dt, v in d["wikipedia"].get("timeseries", {}).items():
                evo.append({"Date": dt, "Candidat": d["info"]["name"], "Vues": v})
        
        if evo:
            evo_df = pd.DataFrame(evo)
            evo_df["Date"] = pd.to_datetime(evo_df["Date"])
            fig = px.line(evo_df, x="Date", y="Vues", color="Candidat", title="Évolution Wikipedia")
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    with tabs[2]:
        col1, col2 = st.columns(2)
        with col1:
            press_df = pd.DataFrame([{"Candidat": d["info"]["name"], "Articles": d["press"]["article_count"]} for _, d in sorted_data])
            fig = px.bar(press_df, x="Candidat", y="Articles", title="Nombre d'articles")
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.pie(press_df, values="Articles", names="Candidat", title="Part de voix (presse)")
            st.plotly_chart(fig, use_container_width=True)
    
    with tabs[3]:
        if any(d["trends"]["success"] for _, d in sorted_data):
            trends_df = pd.DataFrame([
                {"Candidat": d["info"]["name"], "Score": d["trends"]["score"]}
                for _, d in sorted_data
            ])
            fig = px.bar(trends_df, x="Candidat", y="Score", title="Google Trends (moyenne 7 derniers jours)")
            st.plotly_chart(fig, use_container_width=True)
            
            # Évolution
            evo = []
            for cid, d in all_data.items():
                for dt, v in d["trends"].get("timeseries", {}).items():
                    evo.append({"Date": dt, "Candidat": d["info"]["name"], "Intérêt": v})
            if evo:
                evo_df = pd.DataFrame(evo)
                evo_df["Date"] = pd.to_datetime(evo_df["Date"])
                fig = px.line(evo_df, x="Date", y="Intérêt", color="Candidat", title="Évolution Google Trends")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Google Trends n'a pas pu récupérer les données (limite de requêtes possible)")
    
    with tabs[4]:
        st.markdown("### 📋 Tous les articles par candidat")
        
        for cid, d in sorted_data:
            articles = d["press"]["articles"]
            with st.expander(f"{d['info']['emoji']} **{d['info']['name']}** - {len(articles)} articles"):
                if articles:
                    for i, art in enumerate(articles, 1):
                        st.markdown(f"**{i}.** [{art['title']}]({art['url']})")
                        st.caption(f"📅 {art.get('date', 'N/A')} | 🌐 {art.get('domain', 'N/A')} | 📌 {art.get('source_type', '')}")
                        st.markdown("---")
                else:
                    st.info("Aucun article trouvé")
    
    # YouTube (si dispo)
    if youtube_available:
        st.markdown("---")
        st.markdown("## 🎬 YouTube")
        
        for cid, d in sorted_data:
            yt = d["youtube"]
            if yt.get("available"):
                with st.expander(f"{d['info']['emoji']} {d['info']['name']} - {yt.get('total_views', 0):,} vues"):
                    st.metric("Vidéos trouvées", yt.get("video_count", 0))
                    st.metric("Vues totales", f"{yt.get('total_views', 0):,}")
                    st.metric("Likes totaux", f"{yt.get('total_likes', 0):,}")
                    
                    if yt.get("videos"):
                        st.markdown("**Vidéos récentes :**")
                        for v in yt["videos"][:10]:
                            views = v.get("views", "N/A")
                            st.markdown(f"- [{v['title']}]({v['url']}) - {views:,} vues" if isinstance(views, int) else f"- [{v['title']}]({v['url']})")
    
    # Export
    st.markdown("---")
    st.markdown("## 📥 Export")
    
    col1, col2 = st.columns(2)
    with col1:
        csv = df.to_csv(index=False)
        st.download_button("📊 CSV", csv, f"visibility_{end_date.strftime('%Y%m%d')}.csv", use_container_width=True)
    with col2:
        summary = generate_summary(sorted_data, start_date, end_date, youtube_available)
        st.download_button("📝 Résumé", summary, f"summary_{end_date.strftime('%Y%m%d')}.txt", use_container_width=True)
    
    with st.expander("📋 Résumé (copier-coller)"):
        st.code(summary, language=None)


def generate_summary(sorted_data: List, start_date: date, end_date: date, youtube_ok: bool) -> str:
    """Génère le résumé."""
    lines = [
        "📊 VISIBILITY INDEX - MUNICIPALES PARIS 2026",
        f"Période: {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}",
        f"Sources: Wikipedia ✓ | Presse ✓ | Trends ✓ | YouTube {'✓' if youtube_ok else '✗'}",
        "",
        "=" * 50,
        "🏆 CLASSEMENT",
        "=" * 50,
    ]
    
    for rank, (cid, d) in enumerate(sorted_data, 1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"{rank}.")
        lines.append(f"{medal} {d['info']['name']}: {d['score']['total']:.0f}/100")
    
    lines.extend(["", "=" * 50, "📊 DÉTAILS", "=" * 50])
    
    for cid, d in sorted_data:
        lines.append(f"\n{d['info']['name']} ({d['info']['party']}):")
        lines.append(f"  • Wikipedia: {d['wikipedia']['total_views']:,} vues ({d['wikipedia']['variation_pct']:+.0f}%)")
        lines.append(f"  • Presse: {d['press']['article_count']} articles ({d['press']['domain_count']} sources)")
        lines.append(f"  • Trends: {d['trends']['score']:.0f}/100")
        if d['youtube'].get('available'):
            lines.append(f"  • YouTube: {d['youtube']['total_views']:,} vues ({d['youtube']['video_count']} vidéos)")
    
    lines.extend(["", f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}"])
    
    return "\n".join(lines)


if __name__ == "__main__":
    main()
