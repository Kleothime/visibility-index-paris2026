"""
Visibility Index v2.1 - Application Web Interactive
Tableau de bord de visibilité pour les municipales Paris 2026

Avec données YouTube et estimation réseaux sociaux
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import requests
import time
from typing import Any
import json
import re
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET

# Configuration de la page
st.set_page_config(
    page_title="Visibility Index - Paris 2026",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé pour un design moderne
st.markdown("""
<style>
    /* Style général */
    .main > div {
        padding-top: 2rem;
    }
    
    /* Cards */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        padding: 20px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    /* Candidate cards */
    .candidate-card {
        background: white;
        border-radius: 12px;
        padding: 15px;
        margin: 10px 0;
        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        border-left: 4px solid;
    }
    
    /* Header style */
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        color: white;
        padding: 30px;
        border-radius: 15px;
        margin-bottom: 30px;
        text-align: center;
    }
    
    .main-header h1 {
        margin: 0;
        font-size: 2.2rem;
    }
    
    .main-header p {
        margin: 10px 0 0 0;
        opacity: 0.8;
    }
    
    /* Social icons */
    .social-badge {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 20px;
        font-size: 0.85rem;
        margin: 2px;
    }
    
    .social-youtube { background: #ff0000; color: white; }
    .social-twitter { background: #1da1f2; color: white; }
    .social-news { background: #4285f4; color: white; }
    
    /* Positive/Negative indicators */
    .positive { color: #10b981; font-weight: bold; }
    .negative { color: #ef4444; font-weight: bold; }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 10px 20px;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# CONFIGURATION DES CANDIDATS
# =============================================================================

CANDIDATES = {
    "rachida_dati": {
        "name": "Rachida Dati",
        "party": "LR / Renaissance",
        "color": "#0066CC",
        "wikipedia": "Rachida_Dati",
        "twitter": "daborachida",
        "search_terms": ["Rachida Dati"],
        "emoji": "👩‍⚖️"
    },
    "pierre_yves_bournazel": {
        "name": "Pierre-Yves Bournazel",
        "party": "Horizons",
        "color": "#FF6B35",
        "wikipedia": "Pierre-Yves_Bournazel",
        "twitter": "pabornazel",
        "search_terms": ["Pierre-Yves Bournazel", "Bournazel"],
        "emoji": "👨‍💼"
    },
    "emmanuel_gregoire": {
        "name": "Emmanuel Grégoire",
        "party": "PS",
        "color": "#FF69B4",
        "wikipedia": "Emmanuel_Grégoire",
        "twitter": "egregoire",
        "search_terms": ["Emmanuel Grégoire"],
        "emoji": "👨‍💼"
    },
    "david_belliard": {
        "name": "David Belliard",
        "party": "EELV",
        "color": "#00A86B",
        "wikipedia": "David_Belliard",
        "twitter": "DavidBelliwormed",
        "search_terms": ["David Belliard"],
        "emoji": "🌿"
    },
    "sophia_chikirou": {
        "name": "Sophia Chikirou",
        "party": "LFI",
        "color": "#C9462C",
        "wikipedia": "Sophia_Chikirou",
        "twitter": "SophiaChikirou",
        "search_terms": ["Sophia Chikirou"],
        "emoji": "👩‍💼"
    },
    "thierry_mariani": {
        "name": "Thierry Mariani",
        "party": "RN",
        "color": "#0D2C54",
        "wikipedia": "Thierry_Mariani",
        "twitter": "ThierryMARIANI",
        "search_terms": ["Thierry Mariani"],
        "emoji": "👨‍💼"
    }
}

# =============================================================================
# FONCTIONS DE COLLECTE DE DONNÉES
# =============================================================================

@st.cache_data(ttl=3600, show_spinner=False)
def get_wikipedia_pageviews(page_title: str, start_date: date, end_date: date) -> dict:
    """Récupère les pageviews Wikipedia via l'API Wikimedia."""
    try:
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")
        
        url = (
            f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
            f"fr.wikipedia/all-access/user/{page_title}/daily/{start_str}/{end_str}"
        )
        
        headers = {"User-Agent": "VisibilityIndex/2.1 (Municipal Elections Tracker)"}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            
            timeseries = {}
            total_views = 0
            
            for item in items:
                date_str = item.get("timestamp", "")[:8]
                views = item.get("views", 0)
                try:
                    dt = datetime.strptime(date_str, "%Y%m%d")
                    timeseries[dt.strftime("%Y-%m-%d")] = views
                    total_views += views
                except:
                    continue
            
            return {
                "total_views": total_views,
                "daily_avg": total_views / max(len(items), 1),
                "timeseries": timeseries,
                "success": True
            }
        else:
            return {"total_views": 0, "daily_avg": 0, "timeseries": {}, "success": False}
            
    except Exception as e:
        return {"total_views": 0, "daily_avg": 0, "timeseries": {}, "success": False, "error": str(e)}


@st.cache_data(ttl=3600, show_spinner=False)
def get_gdelt_articles(search_term: str, start_date: date, end_date: date) -> dict:
    """Récupère les articles de presse via GDELT API."""
    try:
        start_str = start_date.strftime("%Y%m%d%H%M%S")
        end_str = (datetime.combine(end_date, datetime.max.time())).strftime("%Y%m%d%H%M%S")
        
        query = f'"{search_term}"'
        
        url = "https://api.gdeltproject.org/api/v2/doc/doc"
        params = {
            "query": query,
            "mode": "ArtList",
            "format": "json",
            "maxrecords": 100,
            "startdatetime": start_str,
            "enddatetime": end_str,
            "sourcelang": "french"
        }
        
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            try:
                data = response.json()
                articles = data.get("articles", [])
                
                seen_titles = set()
                unique_articles = []
                domains = set()
                
                for article in articles:
                    title = article.get("title", "").lower().strip()
                    if title and title not in seen_titles:
                        seen_titles.add(title)
                        unique_articles.append(article)
                        if article.get("domain"):
                            domains.add(article["domain"])
                
                return {
                    "article_count": len(unique_articles),
                    "domain_count": len(domains),
                    "articles": unique_articles[:20],
                    "success": True
                }
            except json.JSONDecodeError:
                return {"article_count": 0, "domain_count": 0, "articles": [], "success": True}
        else:
            return {"article_count": 0, "domain_count": 0, "articles": [], "success": False}
            
    except Exception as e:
        return {"article_count": 0, "domain_count": 0, "articles": [], "success": False, "error": str(e)}


@st.cache_data(ttl=3600, show_spinner=False)
def get_google_news_rss(search_term: str, max_results: int = 20) -> dict:
    """
    Récupère les articles via Google News RSS (gratuit, pas de clé API).
    """
    try:
        # Encoder le terme de recherche
        encoded_term = quote_plus(search_term)
        url = f"https://news.google.com/rss/search?q={encoded_term}&hl=fr&gl=FR&ceid=FR:fr"
        
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            # Parser le XML RSS
            root = ET.fromstring(response.content)
            
            articles = []
            for item in root.findall(".//item")[:max_results]:
                title = item.find("title")
                link = item.find("link")
                pub_date = item.find("pubDate")
                source = item.find("source")
                
                articles.append({
                    "title": title.text if title is not None else "",
                    "url": link.text if link is not None else "",
                    "date": pub_date.text if pub_date is not None else "",
                    "source": source.text if source is not None else "Google News"
                })
            
            return {
                "article_count": len(articles),
                "articles": articles,
                "success": True
            }
        else:
            return {"article_count": 0, "articles": [], "success": False}
            
    except Exception as e:
        return {"article_count": 0, "articles": [], "success": False, "error": str(e)}


@st.cache_data(ttl=3600, show_spinner=False)
def get_youtube_videos(search_term: str, api_key: str = None, max_results: int = 10) -> dict:
    """
    Recherche des vidéos YouTube mentionnant le candidat.
    
    Si pas de clé API, utilise une estimation basée sur d'autres sources.
    """
    # Si on a une clé API YouTube
    if api_key:
        try:
            url = "https://www.googleapis.com/youtube/v3/search"
            params = {
                "part": "snippet",
                "q": search_term,
                "type": "video",
                "order": "date",
                "maxResults": max_results,
                "regionCode": "FR",
                "relevanceLanguage": "fr",
                "key": api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                
                videos = []
                for item in items:
                    snippet = item.get("snippet", {})
                    videos.append({
                        "title": snippet.get("title", ""),
                        "channel": snippet.get("channelTitle", ""),
                        "date": snippet.get("publishedAt", "")[:10],
                        "video_id": item.get("id", {}).get("videoId", ""),
                        "thumbnail": snippet.get("thumbnails", {}).get("medium", {}).get("url", "")
                    })
                
                return {
                    "video_count": len(videos),
                    "videos": videos,
                    "success": True,
                    "source": "youtube_api"
                }
            else:
                return {"video_count": 0, "videos": [], "success": False, "source": "youtube_api"}
                
        except Exception as e:
            return {"video_count": 0, "videos": [], "success": False, "error": str(e), "source": "youtube_api"}
    
    # Sans clé API : recherche via page YouTube (estimation)
    else:
        try:
            encoded_term = quote_plus(search_term)
            url = f"https://www.youtube.com/results?search_query={encoded_term}&sp=CAI%253D"  # Tri par date
            
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                # Compter les occurrences du terme dans la page (estimation grossière)
                content = response.text.lower()
                term_lower = search_term.lower()
                
                # Chercher les patterns de vidéos
                video_pattern = r'"videoId":"([^"]+)"'
                video_ids = list(set(re.findall(video_pattern, response.text)))[:10]
                
                return {
                    "video_count": len(video_ids),
                    "videos": [],
                    "estimated": True,
                    "success": True,
                    "source": "youtube_scrape"
                }
            else:
                return {"video_count": 0, "videos": [], "success": False, "source": "youtube_scrape"}
                
        except Exception as e:
            return {"video_count": 0, "videos": [], "success": False, "error": str(e), "source": "youtube_scrape"}


@st.cache_data(ttl=7200, show_spinner=False)
def get_google_trends_data(keywords: list, geo: str = "FR") -> dict:
    """Récupère les données Google Trends via pytrends."""
    try:
        from pytrends.request import TrendReq
        
        pytrends = TrendReq(hl='fr-FR', tz=60, timeout=(10, 25))
        
        pytrends.build_payload(
            kw_list=keywords[:5],
            cat=0,
            timeframe='today 3-m',
            geo=geo,
            gprop=''
        )
        
        df = pytrends.interest_over_time()
        
        if df.empty:
            return {"success": False, "data": {}}
        
        if 'isPartial' in df.columns:
            df = df.drop(columns=['isPartial'])
        
        result = {}
        for keyword in df.columns:
            result[keyword] = {
                "values": df[keyword].tolist(),
                "dates": [d.strftime("%Y-%m-%d") for d in df.index],
                "avg": float(df[keyword].mean()),
                "max": float(df[keyword].max()),
                "latest": float(df[keyword].iloc[-1]) if len(df) > 0 else 0
            }
        
        return {"success": True, "data": result}
        
    except Exception as e:
        return {"success": False, "data": {}, "error": str(e)}


@st.cache_data(ttl=3600, show_spinner=False)
def get_social_mentions_estimate(search_term: str) -> dict:
    """
    Estime l'activité sur les réseaux sociaux via des sources alternatives.
    
    Utilise :
    - Reddit (API gratuite)
    - Mentions dans Google News (proxy pour viralité)
    """
    total_mentions = 0
    sources = {}
    
    # 1. Reddit (API gratuite)
    try:
        url = f"https://www.reddit.com/search.json?q={quote_plus(search_term)}&limit=25&sort=new"
        headers = {"User-Agent": "VisibilityIndex/2.1"}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            posts = data.get("data", {}).get("children", [])
            reddit_count = len(posts)
            sources["reddit"] = reddit_count
            total_mentions += reddit_count * 2  # Pondération
    except:
        sources["reddit"] = 0
    
    # 2. Estimation basée sur la popularité Google News
    news_data = get_google_news_rss(search_term, max_results=50)
    news_count = news_data.get("article_count", 0)
    sources["news_viral"] = news_count
    total_mentions += news_count * 3  # Les news génèrent des partages
    
    # 3. Score d'engagement estimé (basé sur Wikipedia comme proxy)
    # Plus de pageviews Wikipedia = plus de discussions en ligne
    
    return {
        "estimated_mentions": total_mentions,
        "sources": sources,
        "success": True,
        "note": "Estimation basée sur Reddit et viralité des news"
    }


def calculate_visibility_score(
    wiki_views: int, 
    press_articles: int, 
    trends_score: float,
    youtube_videos: int,
    social_mentions: int
) -> float:
    """
    Calcule un score de visibilité composite (0-100).
    
    Pondérations:
    - Wikipedia: 30% (proxy fiable de l'attention publique)
    - Presse: 25% (couverture médiatique)
    - Trends: 20% (intérêt de recherche)
    - YouTube: 15% (présence vidéo)
    - Social: 10% (estimation réseaux)
    """
    import math
    
    # Normalisation logarithmique pour Wikipedia
    wiki_norm = min(math.log10(max(wiki_views, 1)) / 5, 1) * 100
    
    # Normalisation linéaire pour la presse (0-50 articles = 0-100)
    press_norm = min(press_articles / 50, 1) * 100
    
    # Trends déjà sur 0-100
    trends_norm = min(trends_score, 100)
    
    # YouTube (0-20 vidéos = 0-100)
    youtube_norm = min(youtube_videos / 20, 1) * 100
    
    # Social (0-100 mentions estimées = 0-100)
    social_norm = min(social_mentions / 100, 1) * 100
    
    # Score pondéré
    score = (
        wiki_norm * 0.30 +
        press_norm * 0.25 +
        trends_norm * 0.20 +
        youtube_norm * 0.15 +
        social_norm * 0.10
    )
    
    return round(min(score, 100), 1)


# =============================================================================
# INTERFACE UTILISATEUR
# =============================================================================

def main():
    # Header principal
    st.markdown("""
    <div class="main-header">
        <h1>🗳️ Visibility Index v2.1</h1>
        <p>Tableau de bord de visibilité • Municipales Paris 2026</p>
        <p style="font-size: 0.9rem; margin-top: 15px;">
            📊 Wikipedia • 📰 Presse • 📈 Trends • 🎬 YouTube • 💬 Réseaux
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar - Configuration
    with st.sidebar:
        st.markdown("## ⚙️ Paramètres")
        
        # Sélection de la période
        st.markdown("### 📅 Période d'analyse")
        
        col1, col2 = st.columns(2)
        with col1:
            end_date = st.date_input(
                "Date de fin",
                value=date.today(),
                max_value=date.today(),
                help="Date de fin de la période analysée"
            )
        
        with col2:
            period_days = st.selectbox(
                "Durée",
                options=[3, 7, 14, 30],
                index=1,
                format_func=lambda x: f"{x} jours",
                help="Nombre de jours à analyser"
            )
        
        start_date = end_date - timedelta(days=period_days - 1)
        
        st.info(f"📆 Du **{start_date.strftime('%d/%m/%Y')}** au **{end_date.strftime('%d/%m/%Y')}**")
        
        # Sélection des candidats
        st.markdown("### 👥 Candidats")
        
        selected_candidates = st.multiselect(
            "Candidats à analyser",
            options=list(CANDIDATES.keys()),
            default=list(CANDIDATES.keys()),
            format_func=lambda x: f"{CANDIDATES[x]['emoji']} {CANDIDATES[x]['name']}"
        )
        
        # Configuration API YouTube (optionnel)
        st.markdown("### 🔑 APIs (optionnel)")
        with st.expander("Clé API YouTube"):
            youtube_api_key = st.text_input(
                "Clé API YouTube",
                type="password",
                help="Optionnel. Permet d'avoir plus de détails sur les vidéos YouTube."
            )
            st.caption("Obtenir une clé : [Google Cloud Console](https://console.cloud.google.com/apis/credentials)")
        
        # Bouton de rafraîchissement
        st.markdown("---")
        if st.button("🔄 Actualiser les données", use_container_width=True, type="primary"):
            st.cache_data.clear()
            st.rerun()
        
        # Infos
        st.markdown("---")
        st.markdown("""
        ### 📊 Sources de données
        - **Wikipedia** : Pageviews API
        - **Presse** : GDELT + Google News
        - **Trends** : Google Trends
        - **YouTube** : Recherche vidéos
        - **Social** : Reddit + estimation
        
        *Données mises en cache 1h*
        """)
    
    # Vérification qu'au moins un candidat est sélectionné
    if not selected_candidates:
        st.warning("⚠️ Veuillez sélectionner au moins un candidat dans la barre latérale.")
        return
    
    # Collecte des données
    with st.spinner("📊 Collecte des données en cours... (peut prendre 30-60 secondes)"):
        all_data = collect_all_data(
            selected_candidates, 
            start_date, 
            end_date,
            youtube_api_key if 'youtube_api_key' in dir() else None
        )
    
    # Affichage des résultats
    display_results(all_data, start_date, end_date)


def collect_all_data(candidates: list, start_date: date, end_date: date, youtube_api_key: str = None) -> dict:
    """Collecte toutes les données pour les candidats sélectionnés."""
    
    all_data = {}
    
    # Progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Collecter les données Google Trends pour tous les candidats en une fois
    status_text.text("📈 Récupération Google Trends...")
    all_keywords = [CANDIDATES[c]["name"] for c in candidates]
    trends_data = get_google_trends_data(all_keywords)
    progress_bar.progress(15)
    
    # Collecter les données par candidat
    for i, cand_id in enumerate(candidates):
        cand = CANDIDATES[cand_id]
        status_text.text(f"📊 Analyse de {cand['name']}...")
        
        # Wikipedia
        wiki_data = get_wikipedia_pageviews(cand["wikipedia"], start_date, end_date)
        
        # GDELT (Presse)
        press_data = get_gdelt_articles(cand["name"], start_date, end_date)
        
        # Google News RSS (complément presse)
        news_data = get_google_news_rss(cand["name"], max_results=30)
        
        # Combiner presse GDELT + Google News
        combined_press_count = press_data.get("article_count", 0) + news_data.get("article_count", 0)
        combined_articles = press_data.get("articles", []) + [
            {"title": a["title"], "url": a["url"], "domain": a["source"]} 
            for a in news_data.get("articles", [])
        ]
        
        # YouTube
        youtube_data = get_youtube_videos(cand["name"], youtube_api_key)
        
        # Estimation réseaux sociaux
        social_data = get_social_mentions_estimate(cand["name"])
        
        # Extraire les données Trends pour ce candidat
        trends_score = 0
        trends_timeseries = {}
        if trends_data.get("success") and cand["name"] in trends_data.get("data", {}):
            cand_trends = trends_data["data"][cand["name"]]
            trends_score = cand_trends.get("avg", 0)
            trends_timeseries = dict(zip(cand_trends.get("dates", []), cand_trends.get("values", [])))
        
        # Calculer le score de visibilité
        visibility_score = calculate_visibility_score(
            wiki_data.get("total_views", 0),
            combined_press_count,
            trends_score,
            youtube_data.get("video_count", 0),
            social_data.get("estimated_mentions", 0)
        )
        
        all_data[cand_id] = {
            "info": cand,
            "wikipedia": wiki_data,
            "press": {
                "article_count": combined_press_count,
                "domain_count": press_data.get("domain_count", 0),
                "articles": combined_articles[:25],
                "gdelt_count": press_data.get("article_count", 0),
                "news_count": news_data.get("article_count", 0)
            },
            "youtube": youtube_data,
            "social": social_data,
            "trends": {
                "score": trends_score,
                "timeseries": trends_timeseries,
                "success": trends_data.get("success", False)
            },
            "visibility_score": visibility_score
        }
        
        progress_bar.progress(15 + int(85 * (i + 1) / len(candidates)))
    
    progress_bar.empty()
    status_text.empty()
    
    return all_data


def display_results(all_data: dict, start_date: date, end_date: date):
    """Affiche les résultats de l'analyse."""
    
    # Trier par score de visibilité
    sorted_candidates = sorted(
        all_data.items(),
        key=lambda x: x[1]["visibility_score"],
        reverse=True
    )
    
    # ==========================================================================
    # MÉTRIQUES GLOBALES
    # ==========================================================================
    st.markdown("## 📈 Vue d'ensemble")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    total_wiki = sum(d["wikipedia"]["total_views"] for _, d in sorted_candidates)
    total_press = sum(d["press"]["article_count"] for _, d in sorted_candidates)
    total_youtube = sum(d["youtube"]["video_count"] for _, d in sorted_candidates)
    total_social = sum(d["social"]["estimated_mentions"] for _, d in sorted_candidates)
    leader = sorted_candidates[0] if sorted_candidates else None
    
    with col1:
        st.metric(
            label="🏆 Leader",
            value=leader[1]["info"]["name"].split()[-1] if leader else "N/A",
            delta=f"{leader[1]['visibility_score']:.1f} pts" if leader else None
        )
    
    with col2:
        st.metric(
            label="📚 Wikipedia",
            value=f"{total_wiki:,}",
            help="Total des pageviews Wikipedia"
        )
    
    with col3:
        st.metric(
            label="📰 Presse",
            value=f"{total_press}",
            help="Articles GDELT + Google News"
        )
    
    with col4:
        st.metric(
            label="🎬 YouTube",
            value=f"{total_youtube}",
            help="Vidéos trouvées"
        )
    
    with col5:
        st.metric(
            label="💬 Social",
            value=f"{total_social}",
            help="Mentions estimées (Reddit + viralité)"
        )
    
    # ==========================================================================
    # CLASSEMENT
    # ==========================================================================
    st.markdown("---")
    st.markdown("## 🏆 Classement")
    
    # Créer le dataframe pour le classement
    ranking_data = []
    for rank, (cand_id, data) in enumerate(sorted_candidates, 1):
        ranking_data.append({
            "Rang": rank,
            "Candidat": f"{data['info']['emoji']} {data['info']['name']}",
            "Parti": data["info"]["party"],
            "Score": data["visibility_score"],
            "Wikipedia": data["wikipedia"]["total_views"],
            "Presse": data["press"]["article_count"],
            "YouTube": data["youtube"]["video_count"],
            "Social": data["social"]["estimated_mentions"],
            "Trends": round(data["trends"]["score"], 1)
        })
    
    df_ranking = pd.DataFrame(ranking_data)
    
    # Affichage avec style
    st.dataframe(
        df_ranking,
        column_config={
            "Rang": st.column_config.NumberColumn("🏅", format="%d", width="small"),
            "Candidat": st.column_config.TextColumn("👤 Candidat", width="medium"),
            "Parti": st.column_config.TextColumn("🏛️ Parti", width="small"),
            "Score": st.column_config.ProgressColumn(
                "📊 Score",
                min_value=0,
                max_value=100,
                format="%.1f"
            ),
            "Wikipedia": st.column_config.NumberColumn("📚 Wiki", format="%d"),
            "Presse": st.column_config.NumberColumn("📰 Presse", format="%d"),
            "YouTube": st.column_config.NumberColumn("🎬 YT", format="%d"),
            "Social": st.column_config.NumberColumn("💬 Social", format="%d"),
            "Trends": st.column_config.NumberColumn("📈 Trends", format="%.1f")
        },
        hide_index=True,
        use_container_width=True
    )
    
    # ==========================================================================
    # GRAPHIQUES
    # ==========================================================================
    st.markdown("---")
    st.markdown("## 📊 Visualisations")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Scores", "📚 Wikipedia", "📰 Presse", "🎬 YouTube & Social", "📈 Évolution"])
    
    with tab1:
        # Bar chart des scores
        fig_scores = px.bar(
            df_ranking,
            x="Candidat",
            y="Score",
            color="Candidat",
            color_discrete_map={
                f"{CANDIDATES[cid]['emoji']} {CANDIDATES[cid]['name']}": CANDIDATES[cid]["color"]
                for cid in CANDIDATES
            },
            title="Score de visibilité global par candidat"
        )
        fig_scores.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig_scores, use_container_width=True)
        
        # Radar chart des composantes
        st.markdown("### 🎯 Répartition des scores par source")
        
        categories = ['Wikipedia', 'Presse', 'Trends', 'YouTube', 'Social']
        
        fig_radar = go.Figure()
        
        for cand_id, data in sorted_candidates[:4]:  # Top 4 pour lisibilité
            import math
            wiki_norm = min(math.log10(max(data["wikipedia"]["total_views"], 1)) / 5, 1) * 100
            press_norm = min(data["press"]["article_count"] / 50, 1) * 100
            trends_norm = min(data["trends"]["score"], 100)
            youtube_norm = min(data["youtube"]["video_count"] / 20, 1) * 100
            social_norm = min(data["social"]["estimated_mentions"] / 100, 1) * 100
            
            fig_radar.add_trace(go.Scatterpolar(
                r=[wiki_norm, press_norm, trends_norm, youtube_norm, social_norm],
                theta=categories,
                fill='toself',
                name=data["info"]["name"],
                line_color=data["info"]["color"]
            ))
        
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=True,
            height=400
        )
        st.plotly_chart(fig_radar, use_container_width=True)
    
    with tab2:
        # Wikipedia pageviews
        fig_wiki = px.bar(
            df_ranking,
            x="Candidat",
            y="Wikipedia",
            color="Candidat",
            color_discrete_map={
                f"{CANDIDATES[cid]['emoji']} {CANDIDATES[cid]['name']}": CANDIDATES[cid]["color"]
                for cid in CANDIDATES
            },
            title="Pageviews Wikipedia (période sélectionnée)"
        )
        fig_wiki.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig_wiki, use_container_width=True)
    
    with tab3:
        col1, col2 = st.columns(2)
        
        with col1:
            # Presse - Bar chart
            fig_press = px.bar(
                df_ranking,
                x="Candidat",
                y="Presse",
                color="Candidat",
                color_discrete_map={
                    f"{CANDIDATES[cid]['emoji']} {CANDIDATES[cid]['name']}": CANDIDATES[cid]["color"]
                    for cid in CANDIDATES
                },
                title="Articles de presse"
            )
            fig_press.update_layout(showlegend=False, height=350)
            st.plotly_chart(fig_press, use_container_width=True)
        
        with col2:
            # Presse - Pie chart
            fig_pie = px.pie(
                df_ranking,
                values="Presse",
                names="Candidat",
                title="Part de voix (presse)",
                color="Candidat",
                color_discrete_map={
                    f"{CANDIDATES[cid]['emoji']} {CANDIDATES[cid]['name']}": CANDIDATES[cid]["color"]
                    for cid in CANDIDATES
                }
            )
            fig_pie.update_layout(height=350)
            st.plotly_chart(fig_pie, use_container_width=True)
    
    with tab4:
        st.markdown("### 🎬 YouTube & 💬 Réseaux sociaux")
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_yt = px.bar(
                df_ranking,
                x="Candidat",
                y="YouTube",
                color="Candidat",
                color_discrete_map={
                    f"{CANDIDATES[cid]['emoji']} {CANDIDATES[cid]['name']}": CANDIDATES[cid]["color"]
                    for cid in CANDIDATES
                },
                title="Vidéos YouTube récentes"
            )
            fig_yt.update_layout(showlegend=False, height=350)
            st.plotly_chart(fig_yt, use_container_width=True)
        
        with col2:
            fig_social = px.bar(
                df_ranking,
                x="Candidat",
                y="Social",
                color="Candidat",
                color_discrete_map={
                    f"{CANDIDATES[cid]['emoji']} {CANDIDATES[cid]['name']}": CANDIDATES[cid]["color"]
                    for cid in CANDIDATES
                },
                title="Mentions sociales estimées"
            )
            fig_social.update_layout(showlegend=False, height=350)
            st.plotly_chart(fig_social, use_container_width=True)
        
        st.caption("💡 **Note** : Les données YouTube sont plus précises avec une clé API (gratuite). Les mentions sociales sont estimées via Reddit et la viralité des news.")
    
    with tab5:
        # Évolution temporelle Wikipedia
        st.markdown("### 📈 Évolution des pageviews Wikipedia")
        
        evolution_data = []
        for cand_id, data in all_data.items():
            timeseries = data["wikipedia"].get("timeseries", {})
            for date_str, views in timeseries.items():
                evolution_data.append({
                    "Date": date_str,
                    "Candidat": data["info"]["name"],
                    "Pageviews": views,
                    "color": data["info"]["color"]
                })
        
        if evolution_data:
            df_evolution = pd.DataFrame(evolution_data)
            df_evolution["Date"] = pd.to_datetime(df_evolution["Date"])
            df_evolution = df_evolution.sort_values("Date")
            
            fig_evolution = px.line(
                df_evolution,
                x="Date",
                y="Pageviews",
                color="Candidat",
                color_discrete_map={
                    CANDIDATES[cid]["name"]: CANDIDATES[cid]["color"]
                    for cid in CANDIDATES
                },
                title="Évolution des pageviews Wikipedia"
            )
            fig_evolution.update_layout(height=400)
            st.plotly_chart(fig_evolution, use_container_width=True)
        else:
            st.info("Pas de données d'évolution disponibles")
    
    # ==========================================================================
    # DÉTAILS PAR CANDIDAT
    # ==========================================================================
    st.markdown("---")
    st.markdown("## 👥 Détails par candidat")
    
    for cand_id, data in sorted_candidates:
        with st.expander(f"{data['info']['emoji']} **{data['info']['name']}** ({data['info']['party']}) - Score: {data['visibility_score']:.1f}", expanded=False):
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown("#### 📚 Wikipedia")
                st.metric("Pageviews", f"{data['wikipedia']['total_views']:,}")
                st.metric("Moyenne/jour", f"{data['wikipedia']['daily_avg']:.0f}")
            
            with col2:
                st.markdown("#### 📰 Presse")
                st.metric("Articles total", data['press']['article_count'])
                st.caption(f"GDELT: {data['press']['gdelt_count']} | News: {data['press']['news_count']}")
            
            with col3:
                st.markdown("#### 🎬 YouTube")
                st.metric("Vidéos trouvées", data['youtube']['video_count'])
                if data['youtube'].get('estimated'):
                    st.caption("⚠️ Estimation (pas de clé API)")
            
            with col4:
                st.markdown("#### 💬 Social")
                st.metric("Mentions estimées", data['social']['estimated_mentions'])
                sources = data['social'].get('sources', {})
                st.caption(f"Reddit: {sources.get('reddit', 0)} | Viralité: {sources.get('news_viral', 0)}")
            
            # Afficher les derniers articles
            if data['press']['articles']:
                st.markdown("#### 📰 Derniers articles")
                for article in data['press']['articles'][:5]:
                    title = article.get('title', 'Sans titre')
                    url = article.get('url', '#')
                    domain = article.get('domain', 'Source inconnue')
                    st.markdown(f"- [{title[:80]}...]({url}) *({domain})*")
            
            # Afficher les vidéos YouTube si disponibles
            if data['youtube'].get('videos'):
                st.markdown("#### 🎬 Vidéos récentes")
                for video in data['youtube']['videos'][:3]:
                    yt_url = f"https://www.youtube.com/watch?v={video['video_id']}"
                    st.markdown(f"- [{video['title'][:60]}...]({yt_url}) - *{video['channel']}*")
    
    # ==========================================================================
    # EXPORT
    # ==========================================================================
    st.markdown("---")
    st.markdown("## 📥 Exporter les données")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Export CSV
        csv_data = df_ranking.to_csv(index=False)
        st.download_button(
            label="📊 Télécharger CSV",
            data=csv_data,
            file_name=f"visibility_index_{end_date.strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        # Générer le résumé texte
        summary = generate_text_summary(sorted_candidates, start_date, end_date)
        st.download_button(
            label="📝 Télécharger Résumé",
            data=summary,
            file_name=f"visibility_summary_{end_date.strftime('%Y%m%d')}.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    # Afficher le résumé
    with st.expander("📋 Voir le résumé (copier-coller pour Sarah)"):
        st.code(summary, language=None)


def generate_text_summary(sorted_candidates: list, start_date: date, end_date: date) -> str:
    """Génère un résumé texte des résultats."""
    
    lines = [
        f"📊 VISIBILITY INDEX - MUNICIPALES PARIS 2026",
        f"Période: {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}",
        "",
        "🏆 CLASSEMENT:",
    ]
    
    for rank, (cand_id, data) in enumerate(sorted_candidates, 1):
        medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."
        lines.append(f"{medal} {data['info']['name']}: {data['visibility_score']:.1f} pts")
    
    lines.extend([
        "",
        "📊 DÉTAILS TOP 3:",
    ])
    
    for rank, (cand_id, data) in enumerate(sorted_candidates[:3], 1):
        lines.append(f"")
        lines.append(f"{data['info']['name']}:")
        lines.append(f"  - Wikipedia: {data['wikipedia']['total_views']:,} vues")
        lines.append(f"  - Presse: {data['press']['article_count']} articles")
        lines.append(f"  - YouTube: {data['youtube']['video_count']} vidéos")
        lines.append(f"  - Social: {data['social']['estimated_mentions']} mentions estimées")
    
    lines.extend([
        "",
        "📈 TOTAUX:",
        f"• Wikipedia total: {sum(d['wikipedia']['total_views'] for _, d in sorted_candidates):,} vues",
        f"• Articles presse: {sum(d['press']['article_count'] for _, d in sorted_candidates)}",
        f"• Vidéos YouTube: {sum(d['youtube']['video_count'] for _, d in sorted_candidates)}",
        f"• Mentions sociales: {sum(d['social']['estimated_mentions'] for _, d in sorted_candidates)}",
        "",
        f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}"
    ])
    
    return "\n".join(lines)


if __name__ == "__main__":
    main()
