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
- X (Twitter), Facebook, Instagram, TikTok : APIs fermées ou payantes

L'appli :
- Interroge les APIs en direct quand c'est possible
- Affiche clairement les métriques manquantes ou dégradées
- Produit un score de visibilité par candidat, en séparant bien :
  - Visibilité organique (Wikipedia, Trends, Presse)
  - Bonus YouTube si configuré

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
# CONFIGURATION GLOBALE
# =============================================================================

st.set_page_config(
    page_title="Visibility Index - Paris 2026",
    page_icon="📊",
    layout="wide",
)

# Styles CSS simples
st.markdown(
    """
<style>
    .big-title {
        font-size: 30px;
        font-weight: 700;
        margin-bottom: 0px;
    }
    .subtitle {
        font-size: 16px;
        color: #555;
        margin-bottom: 20px;
    }
    .card {
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #ddd;
        background-color: #fafafa;
        margin-bottom: 10px;
    }
    .score-badge {
        font-size: 26px;
        font-weight: 700;
    }
    .source-indicator {
        font-size: 13px;
        margin-right: 8px;
        padding: 3px 6px;
        border-radius: 5px;
        background-color: #eee;
        display: inline-block;
    }
    .source-ok {
        border: 1px solid #16a34a;
    }
    .source-ko {
        border: 1px solid #b91c1c;
    }
    .warning-box {
        background-color: #fff7ed;
        border: 1px solid #f97316;
        border-radius: 8px;
        padding: 12px;
        margin: 10px 0;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""",
    unsafe_allow_html=True,
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
        "party": "Horizons / Centre-droit",
        "role": "Député de Paris",
        "color": "#FF8C00",
        "wikipedia_fr": "Pierre-Yves_Bournazel",
        "emoji": "🧑‍💼"
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
def get_google_trends(names: List[str]) -> Dict:
    """
    Récupère Google Trends pour plusieurs noms.
    - Essayage multi-candidat
    - Si ça plante, fallback candidat par candidat
    - Ne renvoie JAMAIS 0 si en réalité il y a des recherches (>0 certains jours)
    """
    if TrendReq is None:
        return {
            "success": False,
            "message": "pytrends non installé",
            "data": {}
        }

    try:
        pytrends = TrendReq(hl="fr-FR", tz=60)
        results = {}

        # 1) tentative multi-candidat (tous les noms d'un coup)
        try:
            pytrends.build_payload(names, timeframe="today 3-m", geo="FR")
            df = pytrends.interest_over_time()
        except Exception:
            df = pd.DataFrame()

        if not df.empty:
            df = df.reset_index()
            for name in names:
                if name not in df.columns:
                    continue
                series = df[["date", name]].rename(columns={name: "value"})
                series["date"] = series["date"].dt.date

                avg_raw = float(series["value"].mean())
                max_val = float(series["value"].max())
                days_positive = int((series["value"] > 0).sum())

                # Si il y a des jours > 0 mais la moyenne arrondie tombe à 0 → on force à 0.5
                if max_val > 0 and avg_raw == 0:
                    avg = 0.5
                else:
                    avg = round(avg_raw, 1)

                timeseries = {
                    row["date"].strftime("%Y-%m-%d"): int(row["value"])
                    for _, row in series.iterrows()
                }

                results[name] = {
                    "score": avg,
                    "score_raw": avg_raw,
                    "days_positive": days_positive,
                    "timeseries": timeseries,
                    "success": True,
                }

            return {
                "success": True,
                "data": results,
            }

        # 2) fallback candidat par candidat si la requête multi a complètement foiré
        for name in names:
            try:
                pytrends.build_payload([name], timeframe="today 3-m", geo="FR")
                df = pytrends.interest_over_time()
                if df.empty or name not in df.columns:
                    continue
                df = df.reset_index()
                series = df[["date", name]].rename(columns={name: "value"})
                series["date"] = series["date"].dt.date

                avg_raw = float(series["value"].mean())
                max_val = float(series["value"].max())
                days_positive = int((series["value"] > 0).sum())

                if max_val > 0 and avg_raw == 0:
                    avg = 0.5
                else:
                    avg = round(avg_raw, 1)

                timeseries = {
                    row["date"].strftime("%Y-%m-%d"): int(row["value"])
                    for _, row in series.iterrows()
                }

                results[name] = {
                    "score": avg,
                    "score_raw": avg_raw,
                    "days_positive": days_positive,
                    "timeseries": timeseries,
                    "success": True,
                }

                # éviter de spammer l'API
                time.sleep(2)

            except Exception:
                continue

        if results:
            return {
                "success": True,
                "data": results,
            }

        return {
            "success": False,
            "message": "Erreur Trends pour tous les candidats",
            "data": {}
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Erreur globale Trends : {e}",
            "data": {}
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
        
        if response.status_code != 200:
            return {
                "success": False,
                "message": f"Erreur HTTP {response.status_code} GDELT",
                "articles": [],
                "count": 0,
                "domains": [],
                "confidence": "medium"
            }
        
        try:
            data = response.json()
        except Exception:
            return {
                "success": False,
                "message": "Impossible de décoder la réponse GDELT",
                "articles": [],
                "count": 0,
                "domains": [],
                "confidence": "low"
            }
        
        articles = data.get("articles", [])
        for a in articles:
            title = a.get("title", "").strip()
            domain = a.get("domain", "").lower()
            url_a = a.get("url", "")
            seendate = a.get("seendate", "")
            
            # Normalisation simple
            title_norm = re.sub(r"\s+", " ", title.lower())
            key = (domain, title_norm)
            if key in seen_titles:
                continue
            seen_titles.add(key)
            domains.add(domain)
            
            all_articles.append({
                "title": title,
                "url": url_a,
                "domain": domain,
                "date": seendate[:8],
                "source_type": "GDELT"
            })
        
        return {
            "success": True,
            "articles": sorted(all_articles, key=lambda x: x.get("date", ""), reverse=True),
            "count": len(all_articles),
            "domains": list(domains),
            "confidence": "medium"
        }
    except Exception:
        # GDELT retourne parfois vide
        return {
            "success": False,
            "message": "Erreur GDELT",
            "articles": [],
            "count": 0,
            "domains": [],
            "confidence": "low"
        }

# =============================================================================
# GOOGLE NEWS RSS - COMPLÉMENT PRESSE
# =============================================================================

@st.cache_data(ttl=1800, show_spinner=False)
def get_google_news_articles(search_term: str) -> Dict:
    """
    Récupère les articles via Google News RSS.
    SOURCE FIABLE - Complément à GDELT.
    """
    try:
        encoded = quote_plus(f'"{search_term}"')
        url = f"https://news.google.com/rss/search?q={encoded}&hl=fr&gl=FR&ceid=FR:fr"
        
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            return {
                "success": False,
                "message": f"Erreur HTTP {response.status_code} Google News",
                "articles": [],
                "count": 0,
                "confidence": "medium"
            }
        
        root = ET.fromstring(response.content)
        channel = root.find("channel")
        items = channel.findall("item") if channel is not None else []
        
        all_articles = []
        domains = set()
        seen_titles = set()
        
        for item in items:
            title_el = item.find("title")
            link_el = item.find("link")
            pub_date_el = item.find("pubDate")
            
            title = title_el.text if title_el is not None else ""
            link = link_el.text if link_el is not None else ""
            pub_date = pub_date_el.text if pub_date_el is not None else ""
            
            if not title or not link:
                continue
            
            title_norm = re.sub(r"\s+", " ", title.lower())
            if title_norm in seen_titles:
                continue
            seen_titles.add(title_norm)
            
            # Extraire domaine
            m = re.search(r"https?://([^/]+)/", link)
            domain = m.group(1).lower() if m else ""
            domains.add(domain)
            
            all_articles.append({
                "title": title.strip(),
                "url": link.strip(),
                "domain": domain,
                "date": pub_date,
                "source_type": "GoogleNews"
            })
        
        # fusion
        unique_articles = all_articles
        unique_articles.sort(key=lambda x: x.get("date", ""), reverse=True)
        
        return {
            "success": True,
            "articles": unique_articles,
            "count": len(unique_articles),
            "domains": list(domains),
            "confidence": "medium"
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "articles": [],
            "count": 0,
            "confidence": "low"
        }

# =============================================================================
# YOUTUBE DATA API - NÉCESSITE CLÉ API
# =============================================================================

@st.cache_data(ttl=1800, show_spinner=False)
def get_youtube_data(search_term: str, api_key: str) -> Dict:
    """
    Récupère les vraies données YouTube via l'API officielle.
    """
    if not api_key:
        return {
            "success": False,
            "available": False,
            "message": "Clé API YouTube non configurée",
            "total_views": 0,
            "video_count": 0,
            "confidence": "low"
        }
    
    try:
        search_url = "https://www.googleapis.com/youtube/v3/search"
        stats_url = "https://www.googleapis.com/youtube/v3/videos"
        
        search_params = {
            "part": "id",
            "q": search_term,
            "type": "video",
            "maxResults": 20,
            "order": "date",
            "key": api_key,
        }
        
        search_response = requests.get(search_url, params=search_params, timeout=10)
        if search_response.status_code != 200:
            return {
                "success": False,
                "available": False,
                "message": "Erreur YouTube API (search)",
                "total_views": 0,
                "video_count": 0,
                "confidence": "low"
            }
        
        search_data = search_response.json()
        video_ids = [
            item["id"]["videoId"]
            for item in search_data.get("items", [])
            if item.get("id", {}).get("videoId")
        ]
        
        if not video_ids:
            return {
                "success": True,
                "available": False,
                "message": "Aucune vidéo trouvée",
                "total_views": 0,
                "video_count": 0,
                "confidence": "medium"
            }
        
        stats_params = {
            "part": "statistics",
            "id": ",".join(video_ids),
            "key": api_key,
        }
        stats_response = requests.get(stats_url, params=stats_params, timeout=10)
        if stats_response.status_code != 200:
            return {
                "success": False,
                "available": False,
                "message": "Erreur YouTube API (stats)",
                "total_views": 0,
                "video_count": 0,
                "confidence": "low"
            }
        
        stats_data = stats_response.json()
        
        total_views = 0
        video_count = 0
        for item in stats_data.get("items", []):
            stats = item.get("statistics", {})
            try:
                v = int(stats.get("viewCount", 0))
            except Exception:
                v = 0
            total_views += v
            video_count += 1
        
        return {
            "success": True,
            "available": True,
            "message": "",
            "total_views": total_views,
            "video_count": video_count,
            "confidence": "medium"
        }
    
    except Exception:
        return {
            "success": False,
            "available": False,
            "message": "Quota API YouTube dépassé ou clé invalide",
            "total_views": 0,
            "video_count": 0,
            "confidence": "low"
        }

# =============================================================================
# GOOGLE TRENDS - VIA PYTRENDS
# =============================================================================

try:
    from pytrends.request import TrendReq
except ImportError:
    TrendReq = None

@st.cache_data(ttl=1800, show_spinner=False)
def get_google_trends(names: List[str]) -> Dict:
    """
    Récupère Google Trends pour plusieurs noms.
    Renvoie un score moyen sur la période + timeseries.
    """
    if TrendReq is None:
        return {
            "success": False,
            "message": "pytrends non installé",
            "data": {}
        }
    
    try:
        pytrends = TrendReq(hl="fr-FR", tz=60)
        kw_list = names
        pytrends.build_payload(kw_list, timeframe="today 3-m", geo="FR")
        df = pytrends.interest_over_time()
        if df.empty:
            return {
                "success": False,
                "message": "Aucune donnée Trends",
                "data": {}
            }
        
        df = df.reset_index()
        
        data_out = {}
        for name in names:
            if name not in df.columns:
                continue
            series = df[["date", name]].rename(columns={name: "value"})
            series["date"] = series["date"].dt.date
            
            # score moyen global sur 90 jours
            avg_score = float(series["value"].mean())
            timeseries = {
                row["date"].strftime("%Y-%m-%d"): int(row["value"])
                for _, row in series.iterrows()
            }
            data_out[name] = {
                "score": round(avg_score, 1),
                "timeseries": timeseries,
            }
        
        return {
            "success": True,
            "data": data_out
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Erreur Trends : {e}",
            "data": {}
        }

# =============================================================================
# SCORING VISIBILITÉ
# =============================================================================

def compute_visibility_score(
    wiki_data: Dict,
    press_data: Dict,
    news_data: Dict,
    trends_score: float,
    youtube_data: Dict
) -> Dict:
    """
    Score global sur 100, en séparant organique vs bonus YouTube.
    """

    wiki_views = wiki_data.get("total_views", 0) if wiki_data.get("success") else 0
    wiki_var = wiki_data.get("variation_pct", 0) if wiki_data.get("success") else 0
    wiki_factor = 0
    if wiki_views > 0:
        wiki_factor = 1 + min(max(wiki_var / 100, -0.5), 1.0)

    press_count = press_data.get("count", 0) if press_data.get("success") else 0
    news_count = news_data.get("count", 0) if news_data.get("success") else 0

    total_press = press_count + news_count

    score_wiki = min(wiki_views / 50, 40) * wiki_factor
    score_press = min(total_press / 2, 30)
    score_trends = min(trends_score / 2, 20)

    youtube_total = youtube_data.get("total_views", 0) if youtube_data.get("available") else 0
    score_youtube = min(math.log10(youtube_total + 1) * 8, 10) if youtube_total > 0 else 0

    base_score = score_wiki + score_press + score_trends
    total_score = min(base_score + score_youtube, 100.0)

    return {
        "wiki": round(score_wiki, 1),
        "press": round(score_press, 1),
        "trends": round(score_trends, 1),
        "youtube": round(score_youtube, 1),
        "total": round(total_score, 1),
        "base": round(base_score, 1),
    }

# =============================================================================
# COLLECTE GLOBALE POUR TOUS LES CANDIDATS
# =============================================================================

@st.cache_data(ttl=1800, show_spinner=False)
def collect_data(candidates: List[str], start_date: date, end_date: date, youtube_key: str) -> Dict:
    """Collecte toutes les données."""
    
    all_data = {}
    progress = st.progress(0)
    status = st.empty()
    
    status.text("📈 Google Trends...")
    names = [CANDIDATES[c]["name"] for c in candidates]
    trends_data = get_google_trends(names)
    progress.progress(15)
    
    for i, cand_id in enumerate(candidates):
        cand = CANDIDATES[cand_id]
        name = cand["name"]
        
        status.text(f"🔍 {name} - Wikipedia")
        wiki = get_wikipedia_pageviews(
            page_title=cand["wikipedia_fr"],
            start_date=start_date,
            end_date=end_date,
            history_days=30
        )
        progress.progress(15 + int((i / max(len(candidates), 1)) * 60))

        status.text(f"📰 {name} - Presse (GDELT)")
        gdelt = get_gdelt_articles(name, start_date, end_date)

        status.text(f"📰 {name} - Google News")
        gnews = get_google_news_articles(name)

        if gdelt.get("success") and gnews.get("success"):
            articles = gdelt["articles"] + gnews["articles"]
            seen = set()
            unique_articles = []
            domains = set()
            for art in articles:
                key = (art["domain"], art["title"].strip().lower())
                if key in seen:
                    continue
                seen.add(key)
                unique_articles.append(art)
                domains.add(art["domain"])
            press_data = {
                "success": True,
                "articles": unique_articles,
                "count": len(unique_articles),
                "domains": list(domains),
                "confidence": "medium"
            }
        else:
            press_data = {
                "success": False,
                "articles": [],
                "count": 0,
                "domains": [],
                "confidence": "low"
            }
        
        youtube = get_youtube_data(name, youtube_key) if youtube_key else {"available": False}
        
        trends_score = 0
        trends_ts = {}
        trends_ok = False

        if trends_data.get("success") and name in trends_data.get("data", {}):
            td = trends_data["data"][name]
            trends_score = td.get("score", 0)
            trends_ts = td.get("timeseries", {})
            trends_ok = td.get("success", True)

        score = compute_visibility_score(
            wiki_data=wiki,
            press_data=press_data,
            news_data=gnews,
            trends_score=trends_score if trends_ok else 0,
            youtube_data=youtube
        )

        all_data[cand_id] = {
            "info": cand,
            "wiki": wiki,
            "press": press_data,
            "gnews": gnews,
            "trends": {
                "score": trends_score,
                "timeseries": trends_ts,
                "success": trends_ok,
            },
            "youtube": youtube,
            "score": score
        }

    
    progress.progress(100)
    status.text("✅ Données collectées")

    sorted_data = sorted(all_data.items(), key=lambda x: x[1]["score"]["total"], reverse=True)
    ordered = {k: v for k, v in sorted_data}
    return ordered

# =============================================================================
# INTERFACE STREAMLIT
# =============================================================================

def render_sidebar() -> Dict:
    st.sidebar.title("⚙️ Paramètres")

    default_end = datetime.today().date()
    default_start = default_end - timedelta(days=2)

    start_date = st.sidebar.date_input("Date de début", default_start)
    end_date = st.sidebar.date_input("Date de fin", default_end)

    if start_date > end_date:
        st.sidebar.error("La date de début doit être avant la date de fin.")

    selected_candidates = st.sidebar.multiselect(
        "Candidats",
        options=list(CANDIDATES.keys()),
        default=list(CANDIDATES.keys()),
        format_func=lambda x: f"{CANDIDATES[x]['emoji']} {CANDIDATES[x]['name'].split()[-1]}"
    )
    
    st.markdown("### 🔑 YouTube API")
    youtube_key = st.sidebar.text_input(
        "Clé API YouTube (optionnel)",
        type="password",
        help="Gratuit sur console.cloud.google.com"
    )
    if not youtube_key:
        st.sidebar.warning("⚠️ Sans clé, pas de données YouTube")
    
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Actualiser", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Légende des sources")
    st.sidebar.markdown(
        """
        - 🟢 **Wikipedia** : 100% fiable
        - 🟢 **GDELT/News** : Fiable
        - 🟠 **Trends** : Bruit correct
        - 🔴 **YouTube** : Bonus si clé
        """
    )
    
    return {
        "start_date": start_date,
        "end_date": end_date,
        "candidates": selected_candidates,
        "youtube_key": youtube_key
    }

def render_header(start_date: date, end_date: date):
    st.markdown('<div class="big-title">📊 Visibility Index - Municipales Paris 2026</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="subtitle">Période analysée : <b>{start_date.strftime("%d/%m/%Y")}</b> '
        f'au <b>{end_date.strftime("%d/%m/%Y")}</b></div>',
        unsafe_allow_html=True
    )
    st.markdown(
        """
<div class="warning-box">
<b>Principe :</b> l'outil ne devine rien. Il affiche uniquement des données réellement mesurées (Wikipedia, Trends, presse, YouTube).
<br>Quand une source n'est pas accessible (API, quota, etc.), c'est indiqué clairement.
</div>
""",
        unsafe_allow_html=True
    )

def format_source_indicator(d: Dict) -> str:
    wiki_ok = d["wiki"].get("success", False)
    press_ok = d["press"].get("success", False)
    trends_ok = True if d["trends"].get("timeseries") else False
    youtube_ok = d["youtube"].get("available", False)

    parts = []
    cls = "source-indicator source-ok" if wiki_ok else "source-indicator source-ko"
    parts.append(f'<span class="{cls}">{"✅" if wiki_ok else "❌"} Wikipedia</span>')

    cls = "source-indicator source-ok" if press_ok else "source-indicator source-ko"
    parts.append(f'<span class="{cls}">{"✅" if press_ok else "❌"} Presse</span>')

    cls = "source-indicator source-ok" if trends_ok else "source-indicator source-ko"
    parts.append(f'<span class="{cls}">{"✅" if trends_ok else "❌"} Trends</span>')

    cls = "source-indicator source-ok" if youtube_ok else "source-indicator source-ko"
    parts.append(f'<span class="{cls}">{"✅" if youtube_ok else "❌"} YouTube</span>')

    return " ".join(parts)

def render_leaderboard(data: Dict):
    st.markdown("## 🏆 Leaderboard visibilité")
    rows = []
    for cand_id, d in data.items():
        info = d["info"]
        score = d["score"]
        rows.append({
            "Candidat": info["name"],
            "Parti": info["party"],
            "Score total /100": score["total"],
            "Wikipedia (pages vues)": d["wiki"].get("total_views", 0) if d["wiki"].get("success") else 0,
            "Presse (articles)": d["press"].get("count", 0),
            "Trends (score)": d["trends"]["score"] if d["trends"].get("success") else None,

            "YouTube (vues)": d["youtube"].get("total_views", 0) if d["youtube"].get("available") else 0,
        })
    
    if not rows:
        st.info("Aucun candidat sélectionné.")
        return
    
    df = pd.DataFrame(rows)
    df = df.sort_values("Score total /100", ascending=False)
    st.dataframe(df, use_container_width=True)

    st.markdown("### 🧱 Décomposition du score")
    decomp = []
    for cand_id, d in data.items():
        info = d["info"]
        sc = d["score"]
        decomp.append({"Candidat": info["name"], "Pilier": "📚 Wikipedia", "Points": sc["wiki"]})
        decomp.append({"Candidat": info["name"], "Pilier": "📰 Presse (GDELT+News)", "Points": sc["press"]})
        decomp.append({"Candidat": info["name"], "Pilier": "📈 Trends", "Points": sc["trends"]})
        if sc["youtube"] > 0:
            decomp.append({"Candidat": info["name"], "Pilier": "🎬 YouTube (bonus)", "Points": sc["youtube"]})
    
    df_decomp = pd.DataFrame(decomp)
    if not df_decomp.empty:
        fig = px.bar(
            df_decomp,
            x="Candidat",
            y="Points",
            color="Pilier",
            barmode="stack",
            title="Décomposition du score de visibilité",
        )
        fig.update_layout(legend_title_text="")
        st.plotly_chart(fig, use_container_width=True)

def render_candidate_detail(candidate_id: str, candidate_data: Dict):
    info = candidate_data["info"]
    wiki = candidate_data["wiki"]
    press = candidate_data["press"]
    gnews = candidate_data["gnews"]
    trends = candidate_data["trends"]
    youtube = candidate_data["youtube"]
    score = candidate_data["score"]

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown(
            f"""
<div class="card">
  <div style="font-size:22px;font-weight:bold;margin-bottom:8px;">
    {info['emoji']} {info['name']}
  </div>
  <div style="font-size:14px;color:#555;">
    <b>{info['party']}</b><br>
    {info['role']}
  </div>
  <hr>
  <div style="font-size:14px;">
    <b>Score total :</b> <span class="score-badge">{score['total']}/100</span><br>
    <b>Score hors YouTube :</b> {score['base']}/100
  </div>
  <div style="margin-top:8px;font-size:13px;">
    {format_source_indicator(candidate_data)}
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown("#### 📚 Wikipedia")
        if wiki.get("success"):
            st.write(
                f"- Vues sur la période : **{wiki['total_views']:,}**"
                f" (moyenne {wiki['daily_avg']}/jour)"
            )
            st.write(f"- Variation vs. historique : **{wiki['variation_pct']}%**")
        else:
            st.write("Données Wikipedia indisponibles.")
        
        st.markdown("#### 📰 Presse (GDELT + Google News)")
        press_count = press.get("count", 0)
        gnews_count = gnews.get("count", 0)
        st.write(
            f"- Articles unique (fusion) : **{press_count} (GDELT) + {gnews_count} (News)** "
            f"≈ **{press_count+gnews_count}** (après fusion et déduplication)"
        )
        
    st.markdown("#### 📈 Google Trends")
    if trends.get("success"):
        t_score = trends.get("score", 0)
        st.write(f"- Score moyen 90 jours : **{t_score}** (index 0–100, FR)")
        if t_score == 0 and trends.get("timeseries"):
            st.write(
                "  (score arrondi à 0 mais il y a bien des recherches : voir la courbe ci-dessous.)"
            )
    else:
        st.write("- Données Google Trends non disponibles ou instables pour cette période.")


        st.markdown("#### 🎬 YouTube")
        if youtube.get("available"):
            st.write(
                f"- Vues totales sur les vidéos trouvées : **{youtube['total_views']:,}** "
                f"({youtube['video_count']} vidéos)"
            )
        else:
            st.write("YouTube désactivé (pas de clé API).")

    st.markdown("---")
    st.markdown("### 🕵️ Détails des sources")

    tab_wiki, tab_press, tab_trends, tab_youtube = st.tabs(
        ["Wikipedia", "Presse", "Trends", "YouTube"]
    )

    with tab_wiki:
        if wiki.get("success") and wiki.get("timeseries"):
            ts = pd.DataFrame(
                [
                    {"date": k, "views": v}
                    for k, v in wiki["timeseries"].items()
                ]
            )
            ts["date"] = pd.to_datetime(ts["date"])
            ts = ts.sort_values("date")
            fig = px.line(ts, x="date", y="views", title="Vues quotidiennes Wikipedia")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.write("Pas de timeseries détaillée disponible.")

    with tab_press:
        arts = press.get("articles", [])
        if not arts:
            st.write("Pas d'articles de presse disponibles.")
        else:
            df_press = pd.DataFrame(arts)
            df_press = df_press[["date", "domain", "title", "url", "source_type"]]
            st.dataframe(df_press, use_container_width=True)

    with tab_trends:
        ts = trends.get("timeseries", {})
        if ts:
            df_tr = pd.DataFrame(
                [{"date": k, "trends": v} for k, v in ts.items()]
            )
            df_tr["date"] = pd.to_datetime(df_tr["date"])
            df_tr = df_tr.sort_values("date")
            fig = px.line(df_tr, x="date", y="trends", title="Google Trends (90 jours)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.write("Pas de données Trends détaillées (pytrends indisponible ou erreur).")

    with tab_youtube:
        if youtube.get("available"):
            st.write(
                f"Total vues : **{youtube['total_views']:,}** "
                f"({youtube['video_count']} vidéos)."
            )
            st.info(
                "Détail vidéo par vidéo non affiché ici (quota API). "
                "On travaille uniquement avec un agrégat."
            )
        else:
            st.markdown(
                "⚠️ <strong>YouTube désactivé</strong> : Ajoutez une clé API (gratuite) "
                "dans la sidebar pour avoir les vraies vues YouTube.",
                unsafe_allow_html=True,
            )

def render_export_section(data: Dict, start_date: date, end_date: date):
    st.markdown("### 📤 Export brut (CSV)")

    rows = []
    for cand_id, d in data.items():
        info = d["info"]
        rows.append({
            "candidate_id": cand_id,
            "name": info["name"],
            "party": info["party"],
            "start_date": start_date,
            "end_date": end_date,
            "wiki_total_views": d["wiki"].get("total_views", 0) if d["wiki"].get("success") else 0,
            "wiki_daily_avg": d["wiki"].get("daily_avg", 0) if d["wiki"].get("success") else 0,
            "wiki_variation_pct": d["wiki"].get("variation_pct", 0) if d["wiki"].get("success") else 0,
            "press_articles_count": d["press"].get("count", 0),
            "press_domains_count": len(d["press"].get("domains", [])),
            "trends_score": d["trends"].get("score", 0),
            "youtube_total_views": d["youtube"].get("total_views", 0) if d["youtube"].get("available") else 0,
            "youtube_video_count": d["youtube"].get("video_count", 0) if d["youtube"].get("available") else 0,
            "score_total": d["score"]["total"],
            "score_base": d["score"]["base"],
            "score_wiki": d["score"]["wiki"],
            "score_press": d["score"]["press"],
            "score_trends": d["score"]["trends"],
            "score_youtube": d["score"]["youtube"],
        })
    
    if not rows:
        st.info("Rien à exporter.")
        return
    
    df = pd.DataFrame(rows)
    csv = df.to_csv(index=False)
    st.download_button(
        "📊 Télécharger CSV",
        csv,
        f"visibility_{end_date.strftime('%Y%m%d')}.csv",
        use_container_width=True
    )

def render_brief_text(data: Dict, start_date: date, end_date: date):
    st.markdown("### 📝 Résumé texte (copier-coller mail)")

    if not data:
        st.info("Aucune donnée pour générer un résumé.")
        return

    sorted_items = sorted(
        data.items(),
        key=lambda x: x[1]["score"]["total"],
        reverse=True
    )

    lines = []
    lines.append(
        f"Municipales Paris 2026 – Visibilité concurrents, période {start_date.strftime('%d/%m/%Y')}–{end_date.strftime('%d/%m/%Y')}."
    )

    leader_id, leader_data = sorted_items[0]
    lines.append(
        f"1) {leader_data['info']['name']} est en tête en visibilité globale "
        f"({leader_data['score']['total']}/100)."
    )

    lines.append("2) Détail par pilier (leader) :")
    lines.append(
        f"   • Wikipedia: {leader_data['wiki'].get('total_views', 0)} vues "
        f"({leader_data['wiki'].get('daily_avg', 0)}/jour, "
        f"variation {leader_data['wiki'].get('variation_pct', 0)}%)."
    )
    lines.append(
        f"   • Presse (GDELT+News): {leader_data['press'].get('count', 0)} articles uniques."
    )
    lines.append(
        f"   • Trends: score moyen {leader_data['trends'].get('score', 0)} (FR, 90j)."
    )
    if leader_data["youtube"].get("available"):
        lines.append(
            f"   • YouTube: {leader_data['youtube']['total_views']:,} vues "
            f"({leader_data['youtube']['video_count']} vidéos)."
        )
    else:
        lines.append("   • YouTube: non pris en compte (pas de clé API).")

    if len(sorted_items) > 1:
        runner_id, runner_data = sorted_items[1]
        diff = leader_data["score"]["total"] - runner_data["score"]["total"]
        lines.append(
            f"3) {runner_data['info']['name']} suit avec {runner_data['score']['total']}/100 "
            f"(écart ~{diff:.1f} pts)."
        )

    lines.append(
        "4) Attention : les chiffres reflètent la visibilité globale nationale (Wikipedia, Trends, presse en ligne), "
        "pas uniquement Paris intramuros."
    )

    lines.append(
        "5) Les sources X / Facebook / Instagram / TikTok ne sont pas comptabilisées (APIs fermées ou payantes)."
    )

    text = "\n".join(lines)
    st.text_area("Résumé généré", value=text, height=220)

# =============================================================================
# MAIN
# =============================================================================

def main():
    params = render_sidebar()
    start_date = params["start_date"]
    end_date = params["end_date"]
    candidates = params["candidates"]
    youtube_key = params["youtube_key"]

    render_header(start_date, end_date)

    if not candidates:
        st.warning("Sélectionne au moins un candidat dans la sidebar.")
        return

    with st.spinner("Collecte des données en cours..."):
        data = collect_data(candidates, start_date, end_date, youtube_key)

    render_leaderboard(data)
    st.markdown("---")

    st.markdown("## 🔍 Détail par candidat")
    cand_ids = list(data.keys())
    if cand_ids:
        selected = st.selectbox(
            "Choisir un candidat",
            options=cand_ids,
            format_func=lambda x: data[x]["info"]["name"]
        )
        render_candidate_detail(selected, data[selected])
    else:
        st.info("Aucun candidat à afficher en détail.")

    st.markdown("---")
    col1, col2 = st.columns([1, 1])
    with col1:
        render_export_section(data, start_date, end_date)
    with col2:
        render_brief_text(data, start_date, end_date)

if __name__ == "__main__":
    main()
