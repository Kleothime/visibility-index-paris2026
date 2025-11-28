"""
Visibility Index v3.0 - Application Web Interactive
Tableau de bord de visibilité pour les municipales Paris 2026

Sources fiables :
- PRESSE : GDELT + Google News RSS
- RÉSEAUX : YouTube Data API + Reddit API + Twitter (via recherche Google) + estimation engagement
- TRENDS : Google Trends (pytrends)

Coefficients :
- Couverture presse : 40%
- Réseaux sociaux : 35%
- Google Trends : 25%
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import requests
import time
from typing import Any, Optional
import json
import re
from urllib.parse import quote_plus, quote
import xml.etree.ElementTree as ET
import math

# Configuration de la page
st.set_page_config(
    page_title="Visibility Index - Paris 2026",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé
st.markdown("""
<style>
    .main > div { padding-top: 1rem; }
    
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        color: white;
        padding: 25px;
        border-radius: 15px;
        margin-bottom: 25px;
        text-align: center;
    }
    .main-header h1 { margin: 0; font-size: 2rem; }
    .main-header p { margin: 8px 0 0 0; opacity: 0.85; }
    
    .source-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 15px;
        font-size: 0.75rem;
        margin: 2px;
        font-weight: 500;
    }
    .badge-press { background: #3b82f6; color: white; }
    .badge-social { background: #ec4899; color: white; }
    .badge-trends { background: #10b981; color: white; }
    .badge-youtube { background: #ef4444; color: white; }
    .badge-twitter { background: #1da1f2; color: white; }
    .badge-reddit { background: #ff4500; color: white; }
    
    .confidence-high { color: #10b981; font-weight: bold; }
    .confidence-medium { color: #f59e0b; font-weight: bold; }
    .confidence-low { color: #ef4444; font-weight: bold; }
    
    .article-item {
        padding: 10px;
        border-left: 3px solid #3b82f6;
        margin: 8px 0;
        background: #f8fafc;
        border-radius: 0 8px 8px 0;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# CONFIGURATION DES CANDIDATS
# =============================================================================

CANDIDATES = {
    "rachida_dati": {
        "name": "Rachida Dati",
        "party": "LR / Renaissance",
        "role": "Ministre de la Culture, Maire du 7e",
        "color": "#0066CC",
        "wikipedia": "Rachida_Dati",
        "twitter_handle": "daborachida",
        "search_variants": ["Rachida Dati", "R. Dati"],
        "emoji": "👩‍⚖️"
    },
    "pierre_yves_bournazel": {
        "name": "Pierre-Yves Bournazel",
        "party": "Horizons",
        "role": "Conseiller de Paris",
        "color": "#FF6B35",
        "wikipedia": "Pierre-Yves_Bournazel",
        "twitter_handle": "pabornazel",
        "search_variants": ["Pierre-Yves Bournazel", "Bournazel"],
        "emoji": "👨‍💼"
    },
    "emmanuel_gregoire": {
        "name": "Emmanuel Grégoire",
        "party": "PS",
        "role": "Premier adjoint à la Maire de Paris",
        "color": "#FF69B4",
        "wikipedia": "Emmanuel_Grégoire",
        "twitter_handle": "egregoire",
        "search_variants": ["Emmanuel Grégoire"],
        "emoji": "👨‍💼"
    },
    "david_belliard": {
        "name": "David Belliard",
        "party": "EELV",
        "role": "Adjoint aux mobilités",
        "color": "#00A86B",
        "wikipedia": "David_Belliard",
        "twitter_handle": "DavidBelliard",
        "search_variants": ["David Belliard"],
        "emoji": "🌿"
    },
    "sophia_chikirou": {
        "name": "Sophia Chikirou",
        "party": "LFI",
        "role": "Députée de Paris",
        "color": "#C9462C",
        "wikipedia": "Sophia_Chikirou",
        "twitter_handle": "SophiaChikirou",
        "search_variants": ["Sophia Chikirou"],
        "emoji": "👩‍💼"
    },
    "thierry_mariani": {
        "name": "Thierry Mariani",
        "party": "RN",
        "role": "Député européen",
        "color": "#0D2C54",
        "wikipedia": "Thierry_Mariani",
        "twitter_handle": "ThierryMARIANI",
        "search_variants": ["Thierry Mariani"],
        "emoji": "👨‍💼"
    }
}

# =============================================================================
# FONCTIONS DE COLLECTE - PRESSE
# =============================================================================

@st.cache_data(ttl=1800, show_spinner=False)
def get_gdelt_articles(search_term: str, start_date: date, end_date: date) -> dict:
    """
    Récupère les articles via GDELT API.
    Source très fiable pour la presse française.
    """
    try:
        start_str = start_date.strftime("%Y%m%d000000")
        end_str = end_date.strftime("%Y%m%d235959")
        
        # Requête avec le nom exact
        query = f'"{search_term}"'
        
        url = "https://api.gdeltproject.org/api/v2/doc/doc"
        params = {
            "query": query,
            "mode": "ArtList",
            "format": "json",
            "maxrecords": 250,
            "startdatetime": start_str,
            "enddatetime": end_str,
            "sourcelang": "french"
        }
        
        response = requests.get(url, params=params, timeout=20)
        
        if response.status_code == 200:
            try:
                data = response.json()
                articles = data.get("articles", [])
                
                # Dédupliquer par titre normalisé
                seen_titles = set()
                unique_articles = []
                domains = set()
                
                for article in articles:
                    title = article.get("title", "").lower().strip()
                    title_normalized = re.sub(r'[^\w\s]', '', title)[:50]
                    
                    if title_normalized and title_normalized not in seen_titles:
                        # Vérifier que le nom apparaît bien dans le titre ou l'URL
                        search_lower = search_term.lower()
                        if search_lower in title or search_lower.split()[-1] in title:
                            seen_titles.add(title_normalized)
                            unique_articles.append({
                                "title": article.get("title", "Sans titre"),
                                "url": article.get("url", ""),
                                "domain": article.get("domain", ""),
                                "date": article.get("seendate", "")[:10] if article.get("seendate") else "",
                                "source": "GDELT",
                                "language": article.get("language", "French")
                            })
                            if article.get("domain"):
                                domains.add(article["domain"])
                
                return {
                    "article_count": len(unique_articles),
                    "domain_count": len(domains),
                    "articles": unique_articles,
                    "domains": list(domains),
                    "success": True,
                    "source": "GDELT"
                }
            except json.JSONDecodeError:
                return {"article_count": 0, "domain_count": 0, "articles": [], "domains": [], "success": True, "source": "GDELT"}
        
        return {"article_count": 0, "domain_count": 0, "articles": [], "domains": [], "success": False, "source": "GDELT"}
        
    except Exception as e:
        return {"article_count": 0, "domain_count": 0, "articles": [], "domains": [], "success": False, "error": str(e), "source": "GDELT"}


@st.cache_data(ttl=1800, show_spinner=False)
def get_google_news_rss(search_term: str, max_results: int = 50) -> dict:
    """
    Récupère les articles via Google News RSS.
    Complément fiable à GDELT.
    """
    try:
        encoded_term = quote_plus(f'"{search_term}"')
        url = f"https://news.google.com/rss/search?q={encoded_term}&hl=fr&gl=FR&ceid=FR:fr"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            
            articles = []
            seen_titles = set()
            
            for item in root.findall(".//item")[:max_results]:
                title_elem = item.find("title")
                link_elem = item.find("link")
                pub_date_elem = item.find("pubDate")
                source_elem = item.find("source")
                
                title = title_elem.text if title_elem is not None else ""
                title_normalized = re.sub(r'[^\w\s]', '', title.lower())[:50]
                
                if title_normalized and title_normalized not in seen_titles:
                    seen_titles.add(title_normalized)
                    
                    # Parser la date
                    date_str = ""
                    if pub_date_elem is not None and pub_date_elem.text:
                        try:
                            dt = datetime.strptime(pub_date_elem.text[:25], "%a, %d %b %Y %H:%M:%S")
                            date_str = dt.strftime("%Y-%m-%d")
                        except:
                            date_str = pub_date_elem.text[:10] if pub_date_elem.text else ""
                    
                    articles.append({
                        "title": title,
                        "url": link_elem.text if link_elem is not None else "",
                        "domain": source_elem.text if source_elem is not None else "Google News",
                        "date": date_str,
                        "source": "Google News"
                    })
            
            return {
                "article_count": len(articles),
                "articles": articles,
                "success": True,
                "source": "Google News RSS"
            }
        
        return {"article_count": 0, "articles": [], "success": False, "source": "Google News RSS"}
        
    except Exception as e:
        return {"article_count": 0, "articles": [], "success": False, "error": str(e), "source": "Google News RSS"}


# =============================================================================
# FONCTIONS DE COLLECTE - RÉSEAUX SOCIAUX
# =============================================================================

@st.cache_data(ttl=1800, show_spinner=False)
def get_youtube_data(search_term: str, api_key: Optional[str] = None) -> dict:
    """
    Récupère les données YouTube.
    Avec clé API : données précises (vidéos, vues, etc.)
    Sans clé API : estimation via recherche
    """
    
    if api_key:
        try:
            # Recherche de vidéos
            url = "https://www.googleapis.com/youtube/v3/search"
            params = {
                "part": "snippet",
                "q": search_term,
                "type": "video",
                "order": "date",
                "maxResults": 25,
                "regionCode": "FR",
                "relevanceLanguage": "fr",
                "publishedAfter": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00Z"),
                "key": api_key
            }
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                
                videos = []
                video_ids = []
                
                for item in items:
                    snippet = item.get("snippet", {})
                    video_id = item.get("id", {}).get("videoId", "")
                    if video_id:
                        video_ids.append(video_id)
                        videos.append({
                            "title": snippet.get("title", ""),
                            "channel": snippet.get("channelTitle", ""),
                            "date": snippet.get("publishedAt", "")[:10],
                            "video_id": video_id,
                            "thumbnail": snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
                            "description": snippet.get("description", "")[:200]
                        })
                
                # Récupérer les statistiques des vidéos
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
                        for item in stats_data.get("items", []):
                            stats = item.get("statistics", {})
                            total_views += int(stats.get("viewCount", 0))
                            total_likes += int(stats.get("likeCount", 0))
                            total_comments += int(stats.get("commentCount", 0))
                
                return {
                    "video_count": len(videos),
                    "videos": videos,
                    "total_views": total_views,
                    "total_likes": total_likes,
                    "total_comments": total_comments,
                    "engagement": total_views + (total_likes * 10) + (total_comments * 20),
                    "success": True,
                    "source": "YouTube API",
                    "confidence": "high"
                }
            
            return {"video_count": 0, "videos": [], "total_views": 0, "engagement": 0, "success": False, "source": "YouTube API", "confidence": "none"}
            
        except Exception as e:
            return {"video_count": 0, "videos": [], "total_views": 0, "engagement": 0, "success": False, "error": str(e), "source": "YouTube API", "confidence": "none"}
    
    # Sans clé API : estimation via page de recherche
    else:
        try:
            encoded_term = quote_plus(search_term)
            url = f"https://www.youtube.com/results?search_query={encoded_term}&sp=CAISBAgCEAE"  # Filtre: cette semaine
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "fr-FR,fr;q=0.9"
            }
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                # Compter les video IDs dans le HTML
                video_ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', response.text)
                unique_videos = list(set(video_ids))[:20]
                
                return {
                    "video_count": len(unique_videos),
                    "videos": [],
                    "total_views": len(unique_videos) * 5000,  # Estimation conservatrice
                    "engagement": len(unique_videos) * 6000,
                    "success": True,
                    "source": "YouTube (estimation)",
                    "confidence": "medium",
                    "note": "Ajoutez une clé API YouTube pour des données précises"
                }
            
            return {"video_count": 0, "videos": [], "total_views": 0, "engagement": 0, "success": False, "source": "YouTube", "confidence": "none"}
            
        except Exception as e:
            return {"video_count": 0, "videos": [], "total_views": 0, "engagement": 0, "success": False, "error": str(e), "source": "YouTube", "confidence": "none"}


@st.cache_data(ttl=1800, show_spinner=False)
def get_reddit_data(search_term: str) -> dict:
    """
    Récupère les données Reddit via l'API publique.
    Fiable et gratuit.
    """
    try:
        # Recherche dans tous les subreddits
        url = f"https://www.reddit.com/search.json"
        params = {
            "q": search_term,
            "sort": "new",
            "limit": 100,
            "t": "month"  # Dernier mois
        }
        headers = {
            "User-Agent": "VisibilityIndex/3.0 (Educational Project)"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            posts = data.get("data", {}).get("children", [])
            
            post_list = []
            total_score = 0
            total_comments = 0
            subreddits = set()
            
            for post in posts:
                post_data = post.get("data", {})
                title = post_data.get("title", "")
                
                # Vérifier que le terme apparaît dans le titre ou selftext
                search_lower = search_term.lower()
                if search_lower in title.lower() or search_lower in post_data.get("selftext", "").lower():
                    score = post_data.get("score", 0)
                    num_comments = post_data.get("num_comments", 0)
                    
                    total_score += score
                    total_comments += num_comments
                    subreddits.add(post_data.get("subreddit", ""))
                    
                    post_list.append({
                        "title": title,
                        "subreddit": post_data.get("subreddit", ""),
                        "score": score,
                        "comments": num_comments,
                        "url": f"https://reddit.com{post_data.get('permalink', '')}",
                        "date": datetime.fromtimestamp(post_data.get("created_utc", 0)).strftime("%Y-%m-%d") if post_data.get("created_utc") else ""
                    })
            
            engagement = total_score + (total_comments * 5)
            
            return {
                "post_count": len(post_list),
                "posts": post_list[:20],
                "total_score": total_score,
                "total_comments": total_comments,
                "subreddits": list(subreddits),
                "engagement": engagement,
                "success": True,
                "source": "Reddit API",
                "confidence": "high"
            }
        
        return {"post_count": 0, "posts": [], "engagement": 0, "success": False, "source": "Reddit API", "confidence": "none"}
        
    except Exception as e:
        return {"post_count": 0, "posts": [], "engagement": 0, "success": False, "error": str(e), "source": "Reddit API", "confidence": "none"}


@st.cache_data(ttl=1800, show_spinner=False)
def get_twitter_mentions(search_term: str, twitter_handle: str) -> dict:
    """
    Estime l'activité Twitter/X via recherche Google.
    Twitter API est payante ($100/mois), donc on utilise des proxies.
    """
    try:
        mentions_count = 0
        tweets_found = []
        
        # Méthode 1: Recherche Google pour tweets récents
        encoded_query = quote_plus(f'"{search_term}" site:twitter.com OR site:x.com')
        google_url = f"https://www.google.com/search?q={encoded_query}&tbs=qdr:w"  # Dernière semaine
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        response = requests.get(google_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            # Compter les résultats Twitter/X
            twitter_matches = len(re.findall(r'twitter\.com|x\.com', response.text.lower()))
            mentions_count += twitter_matches
        
        # Méthode 2: Vérifier l'existence et l'activité du compte via Nitter (proxy Twitter open source)
        nitter_instances = [
            "nitter.net",
            "nitter.privacydev.net",
            "nitter.poast.org"
        ]
        
        account_data = None
        for instance in nitter_instances:
            try:
                nitter_url = f"https://{instance}/{twitter_handle}"
                nitter_response = requests.get(nitter_url, headers=headers, timeout=8)
                
                if nitter_response.status_code == 200:
                    html = nitter_response.text
                    
                    # Extraire le nombre de tweets
                    tweets_match = re.search(r'class="profile-stat-num"[^>]*>([0-9,]+)', html)
                    followers_match = re.search(r'Followers.*?([0-9,]+[KM]?)', html, re.IGNORECASE)
                    
                    if tweets_match or followers_match:
                        account_data = {
                            "handle": twitter_handle,
                            "active": True,
                            "source": instance
                        }
                        break
            except:
                continue
        
        # Estimation basée sur la visibilité Google + activité compte
        base_mentions = mentions_count * 15  # Multiplication car Google ne montre qu'une partie
        
        return {
            "estimated_mentions": base_mentions,
            "google_results": mentions_count,
            "handle": twitter_handle,
            "account_found": account_data is not None,
            "engagement": base_mentions * 3,
            "success": True,
            "source": "Twitter (via Google + Nitter)",
            "confidence": "medium",
            "note": "Estimation basée sur l'indexation Google (Twitter API payante)"
        }
        
    except Exception as e:
        return {
            "estimated_mentions": 0,
            "engagement": 0,
            "success": False,
            "error": str(e),
            "source": "Twitter",
            "confidence": "low"
        }


@st.cache_data(ttl=1800, show_spinner=False)
def get_facebook_estimate(search_term: str) -> dict:
    """
    Estime l'activité Facebook.
    L'API Facebook est très restrictive, on utilise des proxies.
    """
    try:
        # Recherche Google pour posts Facebook publics
        encoded_query = quote_plus(f'"{search_term}" site:facebook.com')
        google_url = f"https://www.google.com/search?q={encoded_query}&tbs=qdr:w"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(google_url, headers=headers, timeout=15)
        
        mentions = 0
        if response.status_code == 200:
            fb_matches = len(re.findall(r'facebook\.com', response.text.lower()))
            mentions = fb_matches
        
        # Estimation de l'engagement (Facebook a généralement plus d'engagement que Reddit)
        estimated_engagement = mentions * 50
        
        return {
            "estimated_mentions": mentions * 10,  # Google ne montre qu'une fraction
            "google_results": mentions,
            "engagement": estimated_engagement,
            "success": True,
            "source": "Facebook (via Google)",
            "confidence": "low",
            "note": "Estimation approximative (API Facebook très restrictive)"
        }
        
    except Exception as e:
        return {
            "estimated_mentions": 0,
            "engagement": 0,
            "success": False,
            "error": str(e),
            "source": "Facebook",
            "confidence": "none"
        }


# =============================================================================
# FONCTIONS DE COLLECTE - GOOGLE TRENDS
# =============================================================================

@st.cache_data(ttl=3600, show_spinner=False)
def get_google_trends_individual(search_term: str, days: int = 30) -> dict:
    """
    Récupère les données Google Trends pour un terme spécifique.
    Requête individuelle pour plus de précision.
    """
    try:
        from pytrends.request import TrendReq
        
        # Initialisation avec retry
        pytrends = TrendReq(
            hl='fr-FR',
            tz=60,
            timeout=(10, 30),
            retries=3,
            backoff_factor=0.5
        )
        
        # Timeframe selon la période
        if days <= 7:
            timeframe = 'now 7-d'
        elif days <= 30:
            timeframe = 'today 1-m'
        else:
            timeframe = 'today 3-m'
        
        # Build payload avec un seul terme
        pytrends.build_payload(
            kw_list=[search_term],
            cat=0,
            timeframe=timeframe,
            geo='FR',
            gprop=''
        )
        
        # Récupérer les données
        df = pytrends.interest_over_time()
        
        if df.empty:
            return {
                "score": 0,
                "avg": 0,
                "max": 0,
                "latest": 0,
                "timeseries": {},
                "success": False,
                "source": "Google Trends",
                "confidence": "none",
                "note": "Pas de données disponibles"
            }
        
        # Supprimer isPartial si présent
        if 'isPartial' in df.columns:
            df = df.drop(columns=['isPartial'])
        
        # Extraire les données
        values = df[search_term].tolist()
        dates = [d.strftime("%Y-%m-%d") for d in df.index]
        
        avg_score = float(df[search_term].mean())
        max_score = float(df[search_term].max())
        latest_score = float(df[search_term].iloc[-1]) if len(df) > 0 else 0
        
        # Score composite (moyenne pondérée récente)
        recent_values = values[-7:] if len(values) >= 7 else values
        recent_avg = sum(recent_values) / len(recent_values) if recent_values else 0
        
        return {
            "score": round(recent_avg, 1),
            "avg": round(avg_score, 1),
            "max": round(max_score, 1),
            "latest": round(latest_score, 1),
            "timeseries": dict(zip(dates, values)),
            "success": True,
            "source": "Google Trends",
            "confidence": "high"
        }
        
    except Exception as e:
        error_msg = str(e)
        return {
            "score": 0,
            "avg": 0,
            "max": 0,
            "latest": 0,
            "timeseries": {},
            "success": False,
            "source": "Google Trends",
            "confidence": "none",
            "error": error_msg,
            "note": "Erreur de récupération (limite de requêtes possible)"
        }


@st.cache_data(ttl=3600, show_spinner=False)
def get_google_trends_comparison(candidates: dict) -> dict:
    """
    Compare tous les candidats sur Google Trends en une seule requête.
    Plus fiable pour la comparaison relative.
    """
    try:
        from pytrends.request import TrendReq
        
        pytrends = TrendReq(
            hl='fr-FR',
            tz=60,
            timeout=(10, 30),
            retries=3,
            backoff_factor=0.5
        )
        
        # Prendre les 5 premiers candidats (limite pytrends)
        names = [c["name"] for c in list(candidates.values())[:5]]
        
        pytrends.build_payload(
            kw_list=names,
            cat=0,
            timeframe='today 1-m',
            geo='FR',
            gprop=''
        )
        
        df = pytrends.interest_over_time()
        
        if df.empty:
            return {"success": False, "data": {}}
        
        if 'isPartial' in df.columns:
            df = df.drop(columns=['isPartial'])
        
        results = {}
        for name in names:
            if name in df.columns:
                values = df[name].tolist()
                dates = [d.strftime("%Y-%m-%d") for d in df.index]
                recent_values = values[-7:] if len(values) >= 7 else values
                
                results[name] = {
                    "score": round(sum(recent_values) / len(recent_values), 1) if recent_values else 0,
                    "avg": round(float(df[name].mean()), 1),
                    "max": round(float(df[name].max()), 1),
                    "latest": round(float(df[name].iloc[-1]), 1) if len(df) > 0 else 0,
                    "timeseries": dict(zip(dates, values))
                }
        
        return {"success": True, "data": results}
        
    except Exception as e:
        return {"success": False, "data": {}, "error": str(e)}


# =============================================================================
# CALCUL DU SCORE DE VISIBILITÉ
# =============================================================================

def calculate_visibility_score(
    press_score: float,
    social_score: float,
    trends_score: float
) -> dict:
    """
    Calcule le score de visibilité selon les 3 piliers :
    - Couverture presse : 40%
    - Réseaux sociaux : 35%
    - Google Trends : 25%
    """
    
    # Normalisation (chaque composante sur 100)
    press_norm = min(press_score, 100)
    social_norm = min(social_score, 100)
    trends_norm = min(trends_score, 100)
    
    # Score pondéré
    final_score = (
        press_norm * 0.40 +
        social_norm * 0.35 +
        trends_norm * 0.25
    )
    
    return {
        "total": round(min(final_score, 100), 1),
        "press_component": round(press_norm * 0.40, 1),
        "social_component": round(social_norm * 0.35, 1),
        "trends_component": round(trends_norm * 0.25, 1),
        "breakdown": {
            "press": round(press_norm, 1),
            "social": round(social_norm, 1),
            "trends": round(trends_norm, 1)
        }
    }


def normalize_press_score(article_count: int, domain_count: int) -> float:
    """Normalise le score presse sur 100."""
    # Formule: articles + bonus diversité (domaines)
    # 50 articles = score 100
    article_score = min(article_count / 50, 1) * 80
    diversity_score = min(domain_count / 20, 1) * 20
    return article_score + diversity_score


def normalize_social_score(youtube: dict, reddit: dict, twitter: dict, facebook: dict) -> float:
    """Normalise le score réseaux sociaux sur 100."""
    
    # YouTube : 30% du score social
    yt_engagement = youtube.get("engagement", 0)
    yt_score = min(math.log10(max(yt_engagement, 1)) / 6, 1) * 30  # log10(1M) = 6
    
    # Reddit : 25% du score social
    reddit_engagement = reddit.get("engagement", 0)
    reddit_score = min(math.log10(max(reddit_engagement, 1)) / 4, 1) * 25  # log10(10k) = 4
    
    # Twitter : 30% du score social
    twitter_engagement = twitter.get("engagement", 0)
    twitter_score = min(math.log10(max(twitter_engagement, 1)) / 5, 1) * 30  # log10(100k) = 5
    
    # Facebook : 15% du score social
    fb_engagement = facebook.get("engagement", 0)
    fb_score = min(math.log10(max(fb_engagement, 1)) / 4, 1) * 15
    
    return yt_score + reddit_score + twitter_score + fb_score


# =============================================================================
# INTERFACE UTILISATEUR
# =============================================================================

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🗳️ Visibility Index v3.0</h1>
        <p>Tableau de bord de visibilité • Municipales Paris 2026</p>
        <div style="margin-top: 15px;">
            <span class="source-badge badge-press">📰 Presse 40%</span>
            <span class="source-badge badge-social">📱 Réseaux 35%</span>
            <span class="source-badge badge-trends">📈 Trends 25%</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown("## ⚙️ Paramètres")
        
        # Période
        st.markdown("### 📅 Période")
        col1, col2 = st.columns(2)
        with col1:
            end_date = st.date_input(
                "Fin",
                value=date.today(),
                max_value=date.today()
            )
        with col2:
            period_days = st.selectbox(
                "Durée",
                options=[7, 14, 30],
                index=0,
                format_func=lambda x: f"{x}j"
            )
        
        start_date = end_date - timedelta(days=period_days - 1)
        st.info(f"📆 {start_date.strftime('%d/%m')} → {end_date.strftime('%d/%m/%Y')}")
        
        # Candidats
        st.markdown("### 👥 Candidats")
        selected = st.multiselect(
            "Sélection",
            options=list(CANDIDATES.keys()),
            default=list(CANDIDATES.keys()),
            format_func=lambda x: f"{CANDIDATES[x]['emoji']} {CANDIDATES[x]['name'].split()[-1]}"
        )
        
        # API YouTube (optionnel)
        st.markdown("### 🔑 API (optionnel)")
        with st.expander("Clé YouTube"):
            yt_api_key = st.text_input("Clé API", type="password", help="Pour des stats YouTube précises")
            st.caption("[Obtenir une clé gratuite](https://console.cloud.google.com/apis/credentials)")
        
        st.markdown("---")
        if st.button("🔄 Actualiser", use_container_width=True, type="primary"):
            st.cache_data.clear()
            st.rerun()
        
        # Légende fiabilité
        st.markdown("---")
        st.markdown("""
        ### 📊 Fiabilité des données
        - 🟢 **Haute** : API officielle
        - 🟡 **Moyenne** : Estimation fiable
        - 🔴 **Basse** : Approximation
        """)
    
    if not selected:
        st.warning("⚠️ Sélectionnez au moins un candidat")
        return
    
    # Collecte des données
    all_data = collect_all_data(
        selected,
        start_date,
        end_date,
        yt_api_key if 'yt_api_key' in dir() and yt_api_key else None
    )
    
    # Affichage
    display_results(all_data, start_date, end_date, period_days)


def collect_all_data(candidates: list, start_date: date, end_date: date, yt_api_key: str = None) -> dict:
    """Collecte toutes les données."""
    
    all_data = {}
    progress = st.progress(0)
    status = st.empty()
    
    # Google Trends comparatif
    status.text("📈 Google Trends...")
    selected_candidates = {k: CANDIDATES[k] for k in candidates}
    trends_comparison = get_google_trends_comparison(selected_candidates)
    progress.progress(10)
    
    total = len(candidates)
    
    for i, cand_id in enumerate(candidates):
        cand = CANDIDATES[cand_id]
        name = cand["name"]
        
        status.text(f"📊 {name}...")
        
        # === PRESSE ===
        gdelt = get_gdelt_articles(name, start_date, end_date)
        gnews = get_google_news_rss(name, max_results=50)
        
        # Fusionner et dédupliquer les articles
        all_articles = gdelt.get("articles", []) + gnews.get("articles", [])
        seen_titles = set()
        unique_articles = []
        domains = set(gdelt.get("domains", []))
        
        for article in all_articles:
            title_norm = re.sub(r'[^\w\s]', '', article.get("title", "").lower())[:50]
            if title_norm and title_norm not in seen_titles:
                seen_titles.add(title_norm)
                unique_articles.append(article)
                if article.get("domain"):
                    domains.add(article["domain"])
        
        # Trier par date
        unique_articles.sort(key=lambda x: x.get("date", ""), reverse=True)
        
        press_data = {
            "article_count": len(unique_articles),
            "domain_count": len(domains),
            "articles": unique_articles,
            "domains": list(domains),
            "gdelt_count": gdelt.get("article_count", 0),
            "gnews_count": gnews.get("article_count", 0),
            "confidence": "high"
        }
        
        # === RÉSEAUX SOCIAUX ===
        youtube = get_youtube_data(name, yt_api_key)
        reddit = get_reddit_data(name)
        twitter = get_twitter_mentions(name, cand.get("twitter_handle", ""))
        facebook = get_facebook_estimate(name)
        
        social_data = {
            "youtube": youtube,
            "reddit": reddit,
            "twitter": twitter,
            "facebook": facebook,
            "total_engagement": (
                youtube.get("engagement", 0) +
                reddit.get("engagement", 0) +
                twitter.get("engagement", 0) +
                facebook.get("engagement", 0)
            )
        }
        
        # === GOOGLE TRENDS ===
        if trends_comparison.get("success") and name in trends_comparison.get("data", {}):
            trends_data = trends_comparison["data"][name]
            trends_data["success"] = True
            trends_data["confidence"] = "high"
        else:
            # Fallback: requête individuelle
            trends_data = get_google_trends_individual(name, (end_date - start_date).days)
        
        # === CALCUL DU SCORE ===
        press_score = normalize_press_score(
            press_data["article_count"],
            press_data["domain_count"]
        )
        
        social_score = normalize_social_score(youtube, reddit, twitter, facebook)
        
        trends_score = trends_data.get("score", 0)
        
        visibility = calculate_visibility_score(press_score, social_score, trends_score)
        
        all_data[cand_id] = {
            "info": cand,
            "press": press_data,
            "social": social_data,
            "trends": trends_data,
            "scores": {
                "press_raw": press_score,
                "social_raw": social_score,
                "trends_raw": trends_score,
                "visibility": visibility
            }
        }
        
        progress.progress(10 + int(90 * (i + 1) / total))
    
    progress.empty()
    status.empty()
    
    return all_data


def display_results(all_data: dict, start_date: date, end_date: date, period_days: int):
    """Affiche les résultats."""
    
    # Trier par score
    sorted_data = sorted(
        all_data.items(),
        key=lambda x: x[1]["scores"]["visibility"]["total"],
        reverse=True
    )
    
    # === MÉTRIQUES GLOBALES ===
    st.markdown("## 📈 Vue d'ensemble")
    
    cols = st.columns(5)
    
    leader = sorted_data[0] if sorted_data else None
    total_articles = sum(d["press"]["article_count"] for _, d in sorted_data)
    total_engagement = sum(d["social"]["total_engagement"] for _, d in sorted_data)
    avg_trends = sum(d["trends"].get("score", 0) for _, d in sorted_data) / len(sorted_data) if sorted_data else 0
    
    with cols[0]:
        st.metric("🏆 Leader", leader[1]["info"]["name"].split()[-1] if leader else "-")
    with cols[1]:
        st.metric("📰 Articles", f"{total_articles}")
    with cols[2]:
        st.metric("📱 Engagement", f"{total_engagement:,.0f}")
    with cols[3]:
        st.metric("📈 Trends moy.", f"{avg_trends:.0f}")
    with cols[4]:
        st.metric("👥 Candidats", f"{len(sorted_data)}")
    
    # === CLASSEMENT ===
    st.markdown("---")
    st.markdown("## 🏆 Classement")
    
    ranking_data = []
    for rank, (cand_id, data) in enumerate(sorted_data, 1):
        v = data["scores"]["visibility"]
        ranking_data.append({
            "Rang": rank,
            "Candidat": f"{data['info']['emoji']} {data['info']['name']}",
            "Score": v["total"],
            "📰 Presse": f"{v['breakdown']['press']:.0f}",
            "📱 Social": f"{v['breakdown']['social']:.0f}",
            "📈 Trends": f"{v['breakdown']['trends']:.0f}",
            "Articles": data["press"]["article_count"],
            "Engagement": f"{data['social']['total_engagement']:,.0f}"
        })
    
    df = pd.DataFrame(ranking_data)
    
    st.dataframe(
        df,
        column_config={
            "Rang": st.column_config.NumberColumn("🏅", width="small"),
            "Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.1f"),
        },
        hide_index=True,
        use_container_width=True
    )
    
    # === GRAPHIQUES ===
    st.markdown("---")
    st.markdown("## 📊 Visualisations")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Scores", "📰 Presse", "📱 Réseaux", "📈 Trends", "📋 Articles"])
    
    with tab1:
        # Bar chart des scores
        fig = px.bar(
            df,
            x="Candidat",
            y="Score",
            color="Candidat",
            title="Score de visibilité global",
            color_discrete_map={
                f"{CANDIDATES[cid]['emoji']} {CANDIDATES[cid]['name']}": CANDIDATES[cid]["color"]
                for cid in CANDIDATES
            }
        )
        fig.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # Décomposition par pilier
        st.markdown("### 🎯 Décomposition par pilier")
        
        decomp_data = []
        for cand_id, data in sorted_data:
            v = data["scores"]["visibility"]
            decomp_data.append({"Candidat": data["info"]["name"], "Pilier": "📰 Presse (40%)", "Score": v["press_component"]})
            decomp_data.append({"Candidat": data["info"]["name"], "Pilier": "📱 Réseaux (35%)", "Score": v["social_component"]})
            decomp_data.append({"Candidat": data["info"]["name"], "Pilier": "📈 Trends (25%)", "Score": v["trends_component"]})
        
        df_decomp = pd.DataFrame(decomp_data)
        fig_decomp = px.bar(
            df_decomp,
            x="Candidat",
            y="Score",
            color="Pilier",
            title="Contribution de chaque pilier au score final",
            barmode="stack"
        )
        fig_decomp.update_layout(height=400)
        st.plotly_chart(fig_decomp, use_container_width=True)
    
    with tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            press_df = pd.DataFrame([
                {"Candidat": d["info"]["name"], "Articles": d["press"]["article_count"], "Sources": d["press"]["domain_count"]}
                for _, d in sorted_data
            ])
            fig_press = px.bar(press_df, x="Candidat", y="Articles", color="Candidat", title="Nombre d'articles")
            fig_press.update_layout(showlegend=False, height=350)
            st.plotly_chart(fig_press, use_container_width=True)
        
        with col2:
            fig_pie = px.pie(
                press_df,
                values="Articles",
                names="Candidat",
                title="Part de voix (presse)"
            )
            fig_pie.update_layout(height=350)
            st.plotly_chart(fig_pie, use_container_width=True)
        
        # Détail des sources presse
        st.markdown("### 📰 Détail par source")
        for cand_id, data in sorted_data[:3]:
            st.markdown(f"**{data['info']['name']}** : {data['press']['gdelt_count']} GDELT + {data['press']['gnews_count']} Google News = **{data['press']['article_count']} articles** de {data['press']['domain_count']} sources")
    
    with tab3:
        st.markdown("### 📱 Engagement par plateforme")
        
        social_df_data = []
        for cand_id, data in sorted_data:
            social = data["social"]
            social_df_data.append({
                "Candidat": data["info"]["name"],
                "YouTube": social["youtube"].get("engagement", 0),
                "Reddit": social["reddit"].get("engagement", 0),
                "Twitter": social["twitter"].get("engagement", 0),
                "Facebook": social["facebook"].get("engagement", 0)
            })
        
        social_df = pd.DataFrame(social_df_data)
        
        fig_social = px.bar(
            social_df.melt(id_vars="Candidat", var_name="Plateforme", value_name="Engagement"),
            x="Candidat",
            y="Engagement",
            color="Plateforme",
            title="Engagement par plateforme",
            barmode="group",
            color_discrete_map={
                "YouTube": "#ff0000",
                "Reddit": "#ff4500",
                "Twitter": "#1da1f2",
                "Facebook": "#4267b2"
            }
        )
        fig_social.update_layout(height=400)
        st.plotly_chart(fig_social, use_container_width=True)
        
        # Détails par candidat
        st.markdown("### 📊 Détails réseaux sociaux")
        for cand_id, data in sorted_data:
            social = data["social"]
            with st.expander(f"{data['info']['emoji']} {data['info']['name']}"):
                c1, c2, c3, c4 = st.columns(4)
                
                with c1:
                    st.markdown("**🎬 YouTube**")
                    yt = social["youtube"]
                    st.metric("Vidéos", yt.get("video_count", 0))
                    if yt.get("total_views"):
                        st.metric("Vues", f"{yt['total_views']:,}")
                    conf = yt.get("confidence", "none")
                    st.caption(f"Fiabilité: {'🟢' if conf == 'high' else '🟡' if conf == 'medium' else '🔴'}")
                
                with c2:
                    st.markdown("**🔴 Reddit**")
                    rd = social["reddit"]
                    st.metric("Posts", rd.get("post_count", 0))
                    st.metric("Score total", rd.get("total_score", 0))
                    conf = rd.get("confidence", "none")
                    st.caption(f"Fiabilité: {'🟢' if conf == 'high' else '🟡' if conf == 'medium' else '🔴'}")
                
                with c3:
                    st.markdown("**🐦 Twitter/X**")
                    tw = social["twitter"]
                    st.metric("Mentions est.", tw.get("estimated_mentions", 0))
                    st.caption(f"@{tw.get('handle', 'N/A')}")
                    conf = tw.get("confidence", "none")
                    st.caption(f"Fiabilité: {'🟢' if conf == 'high' else '🟡' if conf == 'medium' else '🔴'}")
                
                with c4:
                    st.markdown("**📘 Facebook**")
                    fb = social["facebook"]
                    st.metric("Mentions est.", fb.get("estimated_mentions", 0))
                    conf = fb.get("confidence", "none")
                    st.caption(f"Fiabilité: {'🟢' if conf == 'high' else '🟡' if conf == 'medium' else '🔴'}")
    
    with tab4:
        st.markdown("### 📈 Google Trends (7 derniers jours)")
        
        trends_df = pd.DataFrame([
            {
                "Candidat": d["info"]["name"],
                "Score": d["trends"].get("score", 0),
                "Max": d["trends"].get("max", 0),
                "Dernier": d["trends"].get("latest", 0)
            }
            for _, d in sorted_data
        ])
        
        fig_trends = px.bar(
            trends_df,
            x="Candidat",
            y="Score",
            color="Candidat",
            title="Score Google Trends (moyenne 7 jours)"
        )
        fig_trends.update_layout(showlegend=False, height=350)
        st.plotly_chart(fig_trends, use_container_width=True)
        
        # Évolution temporelle
        st.markdown("### 📈 Évolution temporelle")
        
        evolution_data = []
        for cand_id, data in all_data.items():
            ts = data["trends"].get("timeseries", {})
            for date_str, value in ts.items():
                evolution_data.append({
                    "Date": date_str,
                    "Candidat": data["info"]["name"],
                    "Intérêt": value
                })
        
        if evolution_data:
            df_evo = pd.DataFrame(evolution_data)
            df_evo["Date"] = pd.to_datetime(df_evo["Date"])
            df_evo = df_evo.sort_values("Date")
            
            fig_evo = px.line(
                df_evo,
                x="Date",
                y="Intérêt",
                color="Candidat",
                title="Évolution de l'intérêt Google Trends"
            )
            fig_evo.update_layout(height=400)
            st.plotly_chart(fig_evo, use_container_width=True)
    
    with tab5:
        st.markdown("### 📋 Tous les articles par candidat")
        
        for cand_id, data in sorted_data:
            articles = data["press"]["articles"]
            with st.expander(f"{data['info']['emoji']} **{data['info']['name']}** - {len(articles)} articles", expanded=False):
                if articles:
                    for i, article in enumerate(articles):
                        st.markdown(f"""
                        <div class="article-item">
                            <strong>{i+1}.</strong> <a href="{article.get('url', '#')}" target="_blank">{article.get('title', 'Sans titre')}</a><br>
                            <small>📅 {article.get('date', 'N/A')} | 🌐 {article.get('domain', 'Source inconnue')} | 📌 {article.get('source', '')}</small>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("Aucun article trouvé pour cette période")
    
    # === EXPORT ===
    st.markdown("---")
    st.markdown("## 📥 Export")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        csv = df.to_csv(index=False)
        st.download_button("📊 CSV Classement", csv, f"visibility_{end_date.strftime('%Y%m%d')}.csv", "text/csv", use_container_width=True)
    
    with col2:
        # Export détaillé
        detailed_data = []
        for cand_id, data in sorted_data:
            detailed_data.append({
                "Candidat": data["info"]["name"],
                "Score Total": data["scores"]["visibility"]["total"],
                "Score Presse": data["scores"]["press_raw"],
                "Score Social": data["scores"]["social_raw"],
                "Score Trends": data["scores"]["trends_raw"],
                "Articles": data["press"]["article_count"],
                "Sources Presse": data["press"]["domain_count"],
                "YouTube Vidéos": data["social"]["youtube"].get("video_count", 0),
                "YouTube Vues": data["social"]["youtube"].get("total_views", 0),
                "Reddit Posts": data["social"]["reddit"].get("post_count", 0),
                "Twitter Mentions": data["social"]["twitter"].get("estimated_mentions", 0),
                "Facebook Mentions": data["social"]["facebook"].get("estimated_mentions", 0),
                "Google Trends": data["trends"].get("score", 0)
            })
        df_detailed = pd.DataFrame(detailed_data)
        csv_detailed = df_detailed.to_csv(index=False)
        st.download_button("📋 CSV Détaillé", csv_detailed, f"visibility_detailed_{end_date.strftime('%Y%m%d')}.csv", "text/csv", use_container_width=True)
    
    with col3:
        summary = generate_summary(sorted_data, start_date, end_date)
        st.download_button("📝 Résumé texte", summary, f"visibility_summary_{end_date.strftime('%Y%m%d')}.txt", "text/plain", use_container_width=True)
    
    with st.expander("📋 Résumé pour Sarah (copier-coller)"):
        st.code(summary, language=None)


def generate_summary(sorted_data: list, start_date: date, end_date: date) -> str:
    """Génère le résumé texte."""
    
    lines = [
        "📊 VISIBILITY INDEX - MUNICIPALES PARIS 2026",
        f"Période: {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}",
        "",
        "=" * 50,
        "🏆 CLASSEMENT",
        "=" * 50,
    ]
    
    for rank, (cand_id, data) in enumerate(sorted_data, 1):
        medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."
        v = data["scores"]["visibility"]
        lines.append(f"{medal} {data['info']['name']}: {v['total']:.1f}/100")
        lines.append(f"   📰 Presse: {v['breakdown']['press']:.0f} | 📱 Social: {v['breakdown']['social']:.0f} | 📈 Trends: {v['breakdown']['trends']:.0f}")
    
    lines.extend([
        "",
        "=" * 50,
        "📰 COUVERTURE PRESSE (40% du score)",
        "=" * 50,
    ])
    
    for cand_id, data in sorted_data:
        lines.append(f"• {data['info']['name']}: {data['press']['article_count']} articles ({data['press']['domain_count']} sources)")
    
    lines.extend([
        "",
        "=" * 50,
        "📱 RÉSEAUX SOCIAUX (35% du score)",
        "=" * 50,
    ])
    
    for cand_id, data in sorted_data:
        social = data["social"]
        lines.append(f"• {data['info']['name']}:")
        lines.append(f"   YouTube: {social['youtube'].get('video_count', 0)} vidéos | Reddit: {social['reddit'].get('post_count', 0)} posts")
        lines.append(f"   Twitter: ~{social['twitter'].get('estimated_mentions', 0)} mentions | Facebook: ~{social['facebook'].get('estimated_mentions', 0)} mentions")
    
    lines.extend([
        "",
        "=" * 50,
        "📈 GOOGLE TRENDS (25% du score)",
        "=" * 50,
    ])
    
    for cand_id, data in sorted_data:
        lines.append(f"• {data['info']['name']}: {data['trends'].get('score', 0):.0f}/100")
    
    lines.extend([
        "",
        f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}",
        "Source: Visibility Index v3.0"
    ])
    
    return "\n".join(lines)


if __name__ == "__main__":
    main()
