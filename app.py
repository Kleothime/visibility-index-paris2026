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
from collections import Counter

# =============================================================================
# CONFIG
# =============================================================================

st.set_page_config(
    page_title="Baromètre Visibilité Médiatique - Paris 2026",
    page_icon="BVM",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Clé API YouTube (sécurisée via secrets)
try:
    YOUTUBE_API_KEY = st.secrets.get("YOUTUBE_API_KEY", "")
except:
    YOUTUBE_API_KEY = ""  # Fallback si secrets non configurés

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
    },
    "sarah_knafo": {
        "name": "Sarah Knafo",
        "party": "Reconquête!",
        "role": "Députée européenne",
        "color": "#1E3A5F",
        "wikipedia": "Sarah_Knafo",
        "search_terms": ["Sarah Knafo", "Knafo Reconquête", "Knafo Paris"],
    }
}

# =============================================================================
# SONDAGES OFFICIELS - Instituts reconnus uniquement
# =============================================================================

SONDAGES_FILE = "sondages_paris2026.json"

# Sondages de base - DONNÉES VÉRIFIÉES aux sources officielles
SONDAGES_BASE = [
    # --- IFOP Novembre 2025 --- VÉRIFIÉ sur ifop.com
    {
        "date": "2025-11-05",
        "institut": "IFOP-Fiducial",
        "commanditaire": "Le Figaro / Sud Radio",
        "echantillon": 1037,
        "methode": "Internet, 29 oct - 3 nov 2025",
        "hypothese": "Listes separees (Dati LR-MoDem-UDI vs Bournazel Horizons-Renaissance)",
        "source_url": "https://www.ifop.com/article/le-climat-politique-a-paris-11/",
        "scores": {
            "Rachida Dati": 27,
            "Emmanuel Grégoire": 21,
            "Pierre-Yves Bournazel": 14,
            "David Belliard": 13,
            "Sophia Chikirou": 12,
        }
    },
    # --- ELABE Juin 2025 --- VÉRIFIÉ sur elabe.fr
    {
        "date": "2025-06-21",
        "institut": "Elabe",
        "commanditaire": "BFMTV / La Tribune Dimanche",
        "echantillon": 1206,
        "methode": "Internet, 6-16 juin 2025",
        "hypothese": "Sans candidature Bournazel",
        "source_url": "https://elabe.fr/municipale-paris/",
        "scores": {
            "Rachida Dati": 34,
            "David Belliard": 19,
            "Emmanuel Grégoire": 17,
            "Sophia Chikirou": 15,
            "Thierry Mariani": 7,
            "Sarah Knafo": 5,
        }
    },
    {
        "date": "2025-06-21",
        "institut": "Elabe",
        "commanditaire": "BFMTV / La Tribune Dimanche",
        "echantillon": 1206,
        "methode": "Internet, 6-16 juin 2025",
        "hypothese": "Avec candidature Bournazel (Horizons)",
        "source_url": "https://elabe.fr/municipale-paris/",
        "scores": {
            "Rachida Dati": 29,
            "David Belliard": 19,
            "Emmanuel Grégoire": 16,
            "Sophia Chikirou": 15,
            "Pierre-Yves Bournazel": 8,
            "Thierry Mariani": 7,
            "Sarah Knafo": 5,
        }
    },
]


def load_sondages() -> List[Dict]:
    """Charge les sondages depuis le fichier JSON + base"""
    sondages = list(SONDAGES_BASE)  # Copie des sondages de base

    try:
        with open(SONDAGES_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
            if isinstance(saved, list):
                # Fusionner sans doublons (clé = date + institut + hypothese)
                existing_keys = {
                    (s["date"], s["institut"], s.get("hypothese", ""))
                    for s in sondages
                }
                for s in saved:
                    key = (s["date"], s["institut"], s.get("hypothese", ""))
                    if key not in existing_keys:
                        sondages.append(s)
                        existing_keys.add(key)
    except FileNotFoundError:
        pass
    except Exception as e:
        st.warning(f"Erreur chargement sondages: {e}")

    return sorted(sondages, key=lambda x: x["date"], reverse=True)


def save_sondages(sondages: List[Dict]) -> bool:
    """Sauvegarde les sondages dans le fichier JSON"""
    try:
        # Ne sauvegarder que les sondages qui ne sont pas dans SONDAGES_BASE
        base_keys = {
            (s["date"], s["institut"], s.get("hypothese", ""))
            for s in SONDAGES_BASE
        }
        to_save = [
            s for s in sondages
            if (s["date"], s["institut"], s.get("hypothese", "")) not in base_keys
        ]

        with open(SONDAGES_FILE, "w", encoding="utf-8") as f:
            json.dump(to_save, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Erreur sauvegarde sondages: {e}")
        return False


def add_sondage(sondage: Dict) -> bool:
    """Ajoute un sondage s'il n'existe pas déjà"""
    sondages = load_sondages()
    key = (sondage["date"], sondage["institut"], sondage.get("hypothese", ""))

    existing_keys = {
        (s["date"], s["institut"], s.get("hypothese", ""))
        for s in sondages
    }

    if key not in existing_keys:
        sondages.append(sondage)
        return save_sondages(sondages)
    return False  # Déjà existant


def fetch_new_sondages() -> List[Dict]:
    """
    Recherche de nouveaux sondages sur les sources officielles.
    Retourne la liste des nouveaux sondages trouvés.
    """
    new_sondages = []

    # Sources à scraper
    sources = [
        {
            "name": "IFOP",
            "search_url": "https://www.google.com/search?q=site:ifop.com+sondage+municipales+paris+2026",
        },
        {
            "name": "Elabe",
            "search_url": "https://www.google.com/search?q=site:elabe.fr+sondage+municipales+paris+2026",
        },
        {
            "name": "Harris Interactive",
            "search_url": "https://www.google.com/search?q=site:harris-interactive.fr+sondage+municipales+paris",
        },
        {
            "name": "OpinionWay",
            "search_url": "https://www.google.com/search?q=site:opinion-way.com+sondage+municipales+paris",
        },
    ]

    # Note: Le scraping automatique des instituts est complexe car chaque site
    # a une structure différente. On utilise plutôt une recherche Google News
    # pour détecter les nouveaux sondages.

    try:
        # Recherche via Google News RSS
        search_query = "sondage municipales Paris 2026 IFOP OR Elabe OR Harris OR OpinionWay"
        rss_url = f"https://news.google.com/rss/search?q={quote_plus(search_query)}&hl=fr&gl=FR&ceid=FR:fr"

        response = requests.get(rss_url, timeout=15)
        if response.status_code == 200:
            root = ET.fromstring(response.content)

            for item in root.findall(".//item"):
                title = item.findtext("title", "").lower()
                link = item.findtext("link", "")
                pub_date = item.findtext("pubDate", "")

                # Filtrer les articles qui parlent de sondages Paris
                if "sondage" in title and "paris" in title:
                    # Détecter l'institut
                    institut = None
                    if "ifop" in title:
                        institut = "IFOP"
                    elif "elabe" in title:
                        institut = "Elabe"
                    elif "harris" in title:
                        institut = "Harris Interactive"
                    elif "opinionway" in title:
                        institut = "OpinionWay"
                    elif "ipsos" in title:
                        institut = "Ipsos"

                    if institut:
                        # Parser la date
                        try:
                            from email.utils import parsedate_to_datetime
                            dt = parsedate_to_datetime(pub_date)
                            date_str = dt.strftime("%Y-%m-%d")
                        except:
                            date_str = datetime.now().strftime("%Y-%m-%d")

                        new_sondages.append({
                            "detected": True,
                            "date": date_str,
                            "institut": institut,
                            "title": item.findtext("title", ""),
                            "url": link,
                            "source": "Google News"
                        })

    except Exception as e:
        st.warning(f"Erreur recherche sondages: {e}")

    return new_sondages


# Variable globale pour les sondages (chargée au démarrage)
SONDAGES = load_sondages()


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
YOUTUBE_CACHE_FILE = "youtube_cache.json"
TRENDS_CACHE_FILE = "trends_cache.json"

# =============================================================================
# LEMMATISATION BASIQUE FRANÇAIS
# =============================================================================

LEMMA_DICT = {
    # Logement
    "logements": "logement", "loger": "logement", "logé": "logement", "logée": "logement",
    "loyers": "loyer", "locataire": "loyer", "locataires": "loyer",
    "immobilière": "immobilier", "immobiliers": "immobilier",
    # Sécurité
    "sécuritaire": "sécurité", "sécuritaires": "sécurité",
    "policier": "police", "policiers": "police", "policière": "police",
    "délinquant": "délinquance", "délinquants": "délinquance",
    # Transport
    "transports": "transport", "transporteur": "transport",
    "vélos": "vélo", "cycliste": "vélo", "cyclistes": "vélo", "cyclable": "vélo",
    "voitures": "voiture", "automobiliste": "voiture", "automobilistes": "voiture",
    # Propreté
    "propre": "propreté", "propres": "propreté",
    "poubelles": "poubelle", "ordure": "poubelle", "ordures": "poubelle",
    "rats": "rat",
    "déchets": "déchet",
    # Immigration
    "immigré": "immigration", "immigrés": "immigration", "immigrée": "immigration",
    "migrants": "migrant", "migrante": "migrant", "migrantes": "migrant",
    "étrangers": "étranger", "étrangère": "étranger", "étrangères": "étranger",
    "clandestins": "clandestin", "clandestine": "clandestin",
    # Économie
    "économique": "économie", "économiques": "économie",
    "emplois": "emploi", "employé": "emploi", "employés": "emploi",
    "entreprises": "entreprise", "entrepreneur": "entreprise",
    "commerces": "commerce", "commerçant": "commerce", "commerçants": "commerce",
    # Écologie
    "écologique": "écologie", "écologiques": "écologie", "écologiste": "écologie",
    "environnemental": "environnement", "environnementaux": "environnement",
    "pollué": "pollution", "polluée": "pollution", "polluant": "pollution",
    "verts": "vert", "verte": "vert", "vertes": "vert",
    "climatique": "climat", "climatiques": "climat",
    # Culture
    "culturel": "culture", "culturelle": "culture", "culturels": "culture",
    "musées": "musée",
    "spectacles": "spectacle",
    "arts": "art", "artistique": "art", "artistiques": "art",
    # Politique générale
    "électorale": "électoral", "électoraux": "électoral",
    "programmes": "programme",
    "projets": "projet",
    "propositions": "proposition",
    # Pluriels courants
    "parisiens": "parisien", "parisiennes": "parisien",
    "habitants": "habitant", "habitante": "habitant",
    "citoyens": "citoyen", "citoyenne": "citoyen",
}


def lemmatize_word(word: str) -> str:
    """Applique une lemmatisation basique au mot"""
    word_lower = word.lower()
    return LEMMA_DICT.get(word_lower, word_lower)


# =============================================================================
# CACHE YOUTUBE PERSISTANT + QUOTA MANAGEMENT
# =============================================================================

YOUTUBE_QUOTA_DAILY_LIMIT = 10000
YOUTUBE_COST_PER_CANDIDATE = 101  # 100 (search) + 1 (videos)
YOUTUBE_COOLDOWN_HOURS = 2


def load_youtube_cache() -> Dict:
    """Charge le cache YouTube persistant"""
    try:
        with open(YOUTUBE_CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {
            "last_refresh": None,
            "quota_date": None,
            "quota_used": 0,
            "data": {}
        }


def save_youtube_cache(cache: Dict) -> bool:
    """Sauvegarde le cache YouTube"""
    try:
        with open(YOUTUBE_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
        return True
    except:
        return False


def get_youtube_cache_age_hours() -> float:
    """Retourne l'âge du cache YouTube en heures"""
    cache = load_youtube_cache()
    last_refresh = cache.get("last_refresh")

    if not last_refresh:
        return float('inf')  # Jamais rafraîchi

    try:
        last_dt = datetime.fromisoformat(last_refresh)
        age = (datetime.now() - last_dt).total_seconds() / 3600
        return age
    except:
        return float('inf')


def get_youtube_quota_remaining() -> int:
    """Retourne le quota YouTube restant pour aujourd'hui"""
    cache = load_youtube_cache()
    today = date.today().isoformat()

    # Reset si nouveau jour
    if cache.get("quota_date") != today:
        return YOUTUBE_QUOTA_DAILY_LIMIT

    return max(0, YOUTUBE_QUOTA_DAILY_LIMIT - cache.get("quota_used", 0))


def can_refresh_youtube(force: bool = False, expected_cost: int = YOUTUBE_COST_PER_CANDIDATE) -> tuple[bool, str]:
    """
    Vérifie si un refresh YouTube est autorisé.
    Retourne (autorisé, raison)
    """
    cache_age = get_youtube_cache_age_hours()
    quota_remaining = get_youtube_quota_remaining()

    # Vérifier quota
    if quota_remaining < expected_cost:
        return False, f"Quota épuisé ({quota_remaining} unités restantes, besoin de {expected_cost})"

    # Vérifier cooldown (sauf si jamais rafraîchi)
    if cache_age < YOUTUBE_COOLDOWN_HOURS and cache_age != float('inf'):
        if not force:
            minutes_left = int((YOUTUBE_COOLDOWN_HOURS - cache_age) * 60)
            return False, f"Cooldown actif (encore {minutes_left} min)"
        # Force autorisé seulement si > 30 min
        elif cache_age < 0.5:
            return False, "Données trop récentes (< 30 min)"

    return True, "OK"


def increment_youtube_quota(cost: int = YOUTUBE_COST_PER_CANDIDATE):
    """Incrémente le compteur de quota YouTube"""
    cache = load_youtube_cache()
    today = date.today().isoformat()

    # Reset si nouveau jour
    if cache.get("quota_date") != today:
        cache["quota_date"] = today
        cache["quota_used"] = 0

    cache["quota_used"] = cache.get("quota_used", 0) + cost
    cache["last_refresh"] = datetime.now().isoformat()
    save_youtube_cache(cache)


def get_cached_youtube_data(candidate_name: str) -> Optional[Dict]:
    """Récupère les données YouTube en cache pour un candidat et une période exacte"""
    cache = load_youtube_cache()
    entry = cache.get("data", {}).get(candidate_name)
    if not entry:
        return None

    start = entry.get("start")
    end = entry.get("end")
    payload = entry.get("payload")

    if not (start and end and payload):
        return None

    return payload


def get_cached_youtube_data_for_period(candidate_name: str, start_date: date, end_date: date) -> Optional[Dict]:
    """Récupère le cache seulement si la période correspond exactement"""
    cache = load_youtube_cache()
    entry = cache.get("data", {}).get(candidate_name)
    if not entry:
        return None

    if entry.get("start") != start_date.isoformat() or entry.get("end") != end_date.isoformat():
        return None

    payload = entry.get("payload")
    if isinstance(payload, dict):
        return dict(payload)
    return payload


def set_cached_youtube_data(candidate_name: str, data: Dict, start_date: date, end_date: date):
    """Stocke les données YouTube en cache pour un candidat et une période"""
    cache = load_youtube_cache()
    if "data" not in cache:
        cache["data"] = {}
    cache["data"][candidate_name] = {
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "payload": data
    }
    save_youtube_cache(cache)


# =============================================================================
# CACHE GOOGLE TRENDS RELATED QUERIES
# =============================================================================

TRENDS_CACHE_DURATION_HOURS = 6  # Les related queries changent moins vite


def load_trends_cache() -> Dict:
    """Charge le cache des related queries Google Trends"""
    try:
        with open(TRENDS_CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"last_refresh": None, "data": {}}


def save_trends_cache(cache: Dict) -> bool:
    """Sauvegarde le cache Trends"""
    try:
        with open(TRENDS_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
        return True
    except:
        return False


def get_trends_cache_age_hours() -> float:
    """Retourne l'âge du cache Trends en heures"""
    cache = load_trends_cache()
    last_refresh = cache.get("last_refresh")
    if not last_refresh:
        return float('inf')
    try:
        last_dt = datetime.fromisoformat(last_refresh)
        return (datetime.now() - last_dt).total_seconds() / 3600
    except:
        return float('inf')


def get_cached_trends_queries(candidate_name: str) -> Optional[Dict]:
    """Récupère les related queries en cache pour un candidat"""
    cache = load_trends_cache()
    cache_age = get_trends_cache_age_hours()

    # Cache expiré
    if cache_age > TRENDS_CACHE_DURATION_HOURS:
        return None

    return cache.get("data", {}).get(candidate_name)


def set_cached_trends_queries(candidate_name: str, data: Dict):
    """Stocke les related queries en cache"""
    cache = load_trends_cache()
    if "data" not in cache:
        cache["data"] = {}
    cache["data"][candidate_name] = data
    cache["last_refresh"] = datetime.now().isoformat()
    save_trends_cache(cache)


@st.cache_data(ttl=3600, show_spinner=False)
def get_trends_related_queries(candidate_name: str, timeframe: str = "today 1-m") -> Dict:
    """
    Récupère les sujets et requêtes associés à un candidat via Google Trends.

    Retourne:
    - top_queries: Les requêtes les plus fréquentes associées au candidat
    - rising_topics: Les SUJETS en forte croissance (entités, pas requêtes brutes)

    Args:
        candidate_name: Nom du candidat
        timeframe: Période (ex: "today 1-m" = dernier mois, "today 3-m" = 3 mois)
    """
    import time
    import random

    # Vérifier le cache d'abord
    cached = get_cached_trends_queries(candidate_name)
    if cached:
        cached["from_cache"] = True
        return cached

    result = {
        "success": False,
        "top_queries": [],
        "rising_topics": [],  # Changé: topics au lieu de queries
        "error": None,
        "from_cache": False
    }

    try:
        from pytrends.request import TrendReq

        # Délai pour éviter le rate limiting
        time.sleep(2 + random.uniform(0, 2))

        pytrends = TrendReq(hl="fr-FR", tz=60)
        pytrends.build_payload([candidate_name], timeframe=timeframe, geo="FR")

        time.sleep(1 + random.uniform(0, 1))

        # Top queries (requêtes les plus fréquentes)
        related_queries = pytrends.related_queries()
        if related_queries and candidate_name in related_queries:
            candidate_data = related_queries[candidate_name]
            top_df = candidate_data.get("top")
            if top_df is not None and not top_df.empty:
                for _, row in top_df.head(10).iterrows():
                    query = row.get("query", "")
                    value = row.get("value", 0)
                    if query.lower() != candidate_name.lower():
                        result["top_queries"].append({
                            "query": query,
                            "value": int(value) if isinstance(value, (int, float)) else 0
                        })

        # Note: related_topics() désactivé car trop lent et cause des blocages
        # On garde uniquement les top_queries pour l'instant

        result["success"] = len(result["top_queries"]) > 0

        # Sauvegarder en cache si succès
        if result["success"]:
            set_cached_trends_queries(candidate_name, result)

    except Exception as e:
        error_str = str(e)
        if "429" in error_str:
            result["error"] = "Limite Google Trends atteinte (429)"
        else:
            result["error"] = error_str[:100]

    return result


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

def add_to_history(data: Dict, period_label: str, end_date) -> List[Dict]:
    """Ajoute les données actuelles à l'historique (enregistre à la date de fin de période)"""
    history = load_history()

    # Utiliser la date de fin de période analysée
    record_date = end_date.strftime("%Y-%m-%d")

    # Supprimer l'entrée existante pour cette date si elle existe
    history = [h for h in history if h.get("date") != record_date]

    entry = {
        "date": record_date,
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

def get_historical_comparison(candidate_name: str, current_score: float, reference_date: str = None) -> Dict:
    """Compare le score actuel avec l'historique sur plusieurs périodes"""
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

    # Utiliser la date de référence fournie ou la date du jour
    if reference_date:
        ref_date = datetime.strptime(reference_date, "%Y-%m-%d")
    else:
        ref_date = datetime.now()

    # Définir les périodes de comparaison à partir de la date de référence
    periods = {
        "7j": (ref_date - timedelta(days=7)).strftime("%Y-%m-%d"),
        "14j": (ref_date - timedelta(days=14)).strftime("%Y-%m-%d"),
        "30j": (ref_date - timedelta(days=30)).strftime("%Y-%m-%d"),
    }

    scores_at_periods = {}
    for period_name, target_date in periods.items():
        # Trouver le score le plus proche avant ou à cette date
        score = None
        for ps in past_scores:
            if ps["date"] <= target_date:
                score = ps["score"]
        scores_at_periods[period_name] = score

    # Calculer les variations pour chaque période
    changes = {}
    for period_name, old_score in scores_at_periods.items():
        if old_score is not None:
            changes[period_name] = round(current_score - old_score, 1)
        else:
            changes[period_name] = None

    return {
        "available": True,
        "history": past_scores[-30:],
        "changes": changes
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


# Mots vides français à ignorer dans l'analyse
STOP_WORDS = {
    # Mots grammaticaux
    "le", "la", "les", "de", "du", "des", "un", "une", "et", "en", "à", "au", "aux",
    "pour", "par", "sur", "avec", "dans", "qui", "que", "son", "sa", "ses", "ce",
    "cette", "ces", "est", "sont", "a", "été", "être", "avoir", "fait", "faire",
    "plus", "moins", "très", "tout", "tous", "toute", "toutes", "comme", "mais",
    "ou", "où", "donc", "car", "ni", "ne", "pas", "si", "se", "qu", "leur", "leurs",
    "elle", "elles", "il", "ils", "nous", "vous", "on", "lui", "eux", "y", "dont",
    "c", "d", "l", "n", "s", "j", "m", "t", "quand", "après", "avant", "entre",
    "sous", "sans", "vers", "chez", "contre", "depuis", "pendant", "selon",
    "aussi", "bien", "encore", "déjà", "alors", "ainsi", "peut", "doit", "va",
    "veut", "dit", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf", "dix",
    "premier", "première", "nouveau", "nouvelle", "nouveaux", "nouvelles",
    "via", "the", "of", "and", "to", "in", "for", "is", "on", "that", "by", "this",
    "video", "vidéo", "photo", "photos", "images", "image", "article", "articles",

    # Lieux génériques
    "paris", "parisien", "parisiens", "parisienne", "parisiennes", "capitale",
    "france", "français", "française", "françaises", "français",

    # Élections / politique générique
    "municipales", "municipal", "municipale", "élection", "élections",
    "candidat", "candidate", "candidats", "candidates", "candidature", "candidatures",
    "mairie", "maire", "maires", "campagne", "campagnes",
    "ministre", "ministère", "député", "députée", "députés", "sénateur", "sénatrice",
    "politique", "politiques", "gouvernement",

    # Médias
    "bfm", "bfmtv", "rtl", "cnews", "rmc", "lci", "tf1", "france",
    "agence", "presse", "afp", "reuters", "média", "médias",
    "figaro", "monde", "libération", "liberation", "parisien", "ouest", "sud",
    "actu", "actualités", "actualites", "news", "info", "infos", "minutes",

    # Verbes d'action journalistiques
    "lance", "annonce", "révèle", "affirme", "confie", "déclare", "explique",
    "raconte", "officialise", "présente", "veut", "souhaite", "demande",
    "faut", "falloir", "doit", "peut", "pourrait", "devrait", "soit", "être",
    "mettre", "créer", "faire", "aller", "allant", "avoir", "venir",

    # Mots génériques divers
    "ans", "année", "années", "jour", "jours", "mois", "semaine", "semaines",
    "tête", "idée", "idées", "fin", "début", "face", "côté", "suis",
    "ceux", "celle", "celles", "celui", "autres", "autre", "même", "mêmes",
    "public", "publique", "publics", "publiques", "plutôt", "encore",
    "cours", "course", "investie", "investi", "officiellement",

    # Prénoms communs (pour éviter les parties de noms d'autres personnes)
    "anne", "éric", "eric", "yves", "pierre", "jean", "marie", "michel", "jacques",
    "nicolas", "françois", "bruno", "gérald", "gerald", "olivier", "laurent",
    "rachida", "hidalgo", "darmanin", "attal", "zohra", "dati",

    # Faits divers / bruit
    "fille", "fils", "enfant", "enfants", "enlèvement", "tentative", "bayonne",
    "psg", "football", "match"
}


def extract_keywords_from_articles(articles: List[Dict], candidate_name: str, top_n: int = 10) -> List[tuple]:
    """
    Extrait les mots-clés les plus fréquents des titres d'articles pour un candidat.
    Gère les apostrophes françaises et applique une lemmatisation basique.
    """
    if not articles:
        return []

    # Nom du candidat à exclure (lemmatisé aussi)
    name_parts = set(lemmatize_word(p) for p in candidate_name.lower().split())

    word_counts = Counter()
    word_articles = {}  # Stocke les articles par mot-clé (lemme)

    for article in articles:
        title = article.get("title", "")

        # Étape 1: Gérer les apostrophes françaises
        # Remplacer l', d', qu', n', s', j', m', t', c' par un espace
        title_clean = re.sub(r"\b[lLdDqQnNsSmMtTcCjJ]['']\s*", "", title)

        # Étape 2: Extraire les mots (min 3 caractères)
        words = re.findall(r'\b[a-zA-ZàâäéèêëïîôùûüçœæÀÂÄÉÈÊËÏÎÔÙÛÜÇŒÆ]{3,}\b', title_clean.lower())

        # Étape 3: Lemmatiser et filtrer
        seen_in_article = set()  # Éviter de compter plusieurs fois le même lemme dans un article
        for word in words:
            lemma = lemmatize_word(word)

            # Ignorer stop words et nom du candidat
            if lemma in STOP_WORDS or lemma in name_parts:
                continue

            # Compter une seule fois par article
            if lemma not in seen_in_article:
                seen_in_article.add(lemma)
                word_counts[lemma] += 1

                if lemma not in word_articles:
                    word_articles[lemma] = []
                word_articles[lemma].append(article)

    # Retourner les top mots-clés avec leurs articles associés
    top_keywords = word_counts.most_common(top_n)
    return [(word, count, word_articles.get(word, [])) for word, count in top_keywords]

def get_keywords_summary(keywords: List[tuple], max_display: int = 5) -> str:
    """Formate les mots-clés pour affichage"""
    if not keywords:
        return "-"
    return " · ".join([f"{word} ({count})" for word, count in keywords[:max_display]])

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
    """Récupère les données Google Trends avec support de plus de 5 candidats via pivot"""
    try:
        from pytrends.request import TrendReq
        import time
        import random

        if not keywords:
            return {"success": False, "scores": {}, "errors": ["Aucun mot-clé fourni"]}

        timeframe = f"{start_date.strftime('%Y-%m-%d')} {end_date.strftime('%Y-%m-%d')}"
        scores = {}
        errors = []
        max_retries = 3

        # Si 5 candidats ou moins, une seule requête suffit
        if len(keywords) <= 5:
            for attempt in range(max_retries):
                try:
                    time.sleep(2 + random.uniform(0, 2))
                    pytrends = TrendReq(hl="fr-FR", tz=60)
                    pytrends.build_payload(keywords, timeframe=timeframe, geo="FR")
                    time.sleep(1 + random.uniform(0, 1))
                    df = pytrends.interest_over_time()

                    if df is not None and not df.empty:
                        if "isPartial" in df.columns:
                            df = df.drop(columns=["isPartial"])

                        for kw in keywords:
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

        # Si plus de 5 candidats, utiliser un pivot pour normaliser
        else:
            pivot = keywords[0]  # Premier candidat comme référence
            pivot_score = None

            # Diviser en groupes de 4 + pivot
            batch_size = 4
            for i in range(0, len(keywords), batch_size):
                batch = keywords[i:i+batch_size]
                if pivot not in batch:
                    batch = [pivot] + batch

                for attempt in range(max_retries):
                    try:
                        time.sleep(2 + random.uniform(0, 2))
                        pytrends = TrendReq(hl="fr-FR", tz=60)
                        pytrends.build_payload(batch, timeframe=timeframe, geo="FR")
                        time.sleep(1 + random.uniform(0, 1))
                        df = pytrends.interest_over_time()

                        if df is not None and not df.empty:
                            if "isPartial" in df.columns:
                                df = df.drop(columns=["isPartial"])

                            # Stocker le score du pivot de la première requête
                            if pivot_score is None and pivot in df.columns:
                                pivot_score = float(df[pivot].mean())

                            # Normaliser tous les scores par rapport au pivot
                            for kw in batch:
                                if kw in df.columns:
                                    raw_score = float(df[kw].mean())
                                    if pivot_score and pivot_score > 0:
                                        # Normaliser par rapport au pivot
                                        normalized = (raw_score / float(df[pivot].mean())) * pivot_score
                                        scores[kw] = round(normalized, 1)
                                    else:
                                        scores[kw] = round(raw_score, 1)
                                else:
                                    scores[kw] = 0.0
                            break
                        else:
                            if attempt < max_retries - 1:
                                time.sleep(5 * (attempt + 1))
                            else:
                                errors.append(f"Données vides pour le batch {i//batch_size + 1}")

                    except Exception as e:
                        err_str = str(e)
                        if "429" in err_str:
                            if attempt < max_retries - 1:
                                time.sleep(10 * (attempt + 1) + random.uniform(0, 5))
                            else:
                                errors.append("Limite de requêtes Google atteinte (429)")
                        else:
                            errors.append(f"Erreur batch {i//batch_size + 1}: {err_str[:50]}")
                            break

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
                    trends_score: float, youtube_views: int, youtube_available: bool,
                    period_days: int = 7, all_candidates_press: List[int] = None) -> Dict:
    """Calcule le score de visibilité
    Pondération: Presse 40%, Trends 35%, Wikipedia 15%, YouTube 10%

    Le score presse est relatif aux autres candidats pour garantir une différenciation.
    """

    wiki_score = min((math.log10(wiki_views) / 4.7) * 100, 100) if wiki_views > 0 else 0

    # Score presse RELATIF : basé sur le max des candidats de cette analyse
    if all_candidates_press and max(all_candidates_press) > 0:
        max_press = max(all_candidates_press)
        # Score de base relatif (0-80)
        press_base = (press_count / max_press) * 80
        # Bonus diversité relatif (0-20) - on garde un seuil adapté à la période
        diversity_threshold = max(5, period_days * 2)  # 5 pour 24h, 14 pour 7j, 60 pour 30j
        diversity_bonus = min((press_domains / diversity_threshold) * 20, 20)
        press_score = min(press_base + diversity_bonus, 100)
    else:
        # Fallback si pas de données comparatives
        press_score = 0

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

def collect_data(candidate_ids: List[str], start_date: date, end_date: date, youtube_key: Optional[str], force_youtube_refresh: bool = False) -> Dict:
    """Collecte toutes les données pour les candidats sélectionnés"""
    results = {}

    progress = st.progress(0)
    status = st.empty()

    status.text("Chargement des données Google Trends...")
    names = [CANDIDATES[cid]["name"] for cid in candidate_ids]
    trends = get_google_trends(names, start_date, end_date)

    if not trends.get("success", True):
        err = trends.get("error") or trends.get("errors")
        if err:
            st.warning(f"Attention : Google Trends indisponible - {err}")

    progress.progress(0.1)

    expected_youtube_cost = len(candidate_ids) * YOUTUBE_COST_PER_CANDIDATE if youtube_key else 0

    if youtube_key:
        # Toujours utiliser l'API si la clé existe
        youtube_refresh_allowed = True
        youtube_refresh_reason = "OK"
        youtube_mode = "api"
    else:
        youtube_refresh_allowed = False
        youtube_refresh_reason = "Clé API YouTube manquante"
        youtube_mode = "disabled"

    youtube_api_called = False

    # Déterminer le timeframe pour les related queries selon la période
    period_days = (end_date - start_date).days + 1
    if period_days <= 7:
        trends_timeframe = "now 7-d"
    elif period_days <= 30:
        trends_timeframe = "today 1-m"
    else:
        trends_timeframe = "today 3-m"

    total = len(candidate_ids)
    trends_queries_errors = []

    for i, cid in enumerate(candidate_ids):
        c = CANDIDATES[cid]
        name = c["name"]

        status.text(f"Analyse de {name} ({i+1}/{total})...")

        wiki = get_wikipedia_views(c["wikipedia"], start_date, end_date)
        press = get_all_press_coverage(name, c["search_terms"], start_date, end_date)
        tv_radio = get_tv_radio_mentions(name, start_date, end_date)

        yt_start = start_date
        yt_end = end_date

        if youtube_mode == "api":
            status.text(f"Analyse YouTube de {name}...")
            youtube = get_youtube_data(name, youtube_key, yt_start, yt_end)
            set_cached_youtube_data(name, youtube, yt_start, yt_end)
            youtube_api_called = True
        elif youtube_mode == "cache":
            cached = get_cached_youtube_data_for_period(name, yt_start, yt_end)
            if cached:
                youtube = dict(cached)
                youtube["from_cache"] = True
            else:
                youtube = {"available": False, "total_views": 0, "videos": [], "from_cache": True, "no_cache": True}
        else:
            youtube = {"available": False, "total_views": 0, "videos": [], "disabled": True}

        # Récupérer les Related Queries Google Trends
        status.text(f"Analyse des recherches associées pour {name}...")
        related_queries = get_trends_related_queries(name, timeframe=trends_timeframe)
        if related_queries.get("error"):
            trends_queries_errors.append(f"{name}: {related_queries['error']}")

        trends_score = trends.get("scores", {}).get(name, 0)

        # Mots-clés extraits des articles (fallback si related queries échoue)
        keywords = extract_keywords_from_articles(press["articles"], name, top_n=5)

        # Stocker les données brutes (score calculé après pour comparaison relative)
        results[cid] = {
            "info": c,
            "wikipedia": wiki,
            "press": press,
            "tv_radio": tv_radio,
            "youtube": youtube,
            "trends_score": trends_score,
            "trends_success": trends.get("success", True),
            "trends_error": trends.get("error") or trends.get("errors"),
            "related_queries": related_queries,
            "keywords": keywords
        }

        progress.progress((i + 1) / total)

    # === CALCUL DES SCORES (après collecte de tous les candidats) ===
    # Collecter tous les comptages presse pour calcul relatif
    all_press_counts = [results[cid]["press"]["count"] for cid in candidate_ids]
    period_days = (end_date - start_date).days + 1

    for cid in candidate_ids:
        d = results[cid]
        score = calculate_score(
            wiki_views=d["wikipedia"]["views"],
            press_count=d["press"]["count"],
            press_domains=d["press"]["domains"],
            trends_score=d["trends_score"],
            youtube_views=d["youtube"].get("total_views", 0),
            youtube_available=d["youtube"].get("available", False),
            period_days=period_days,
            all_candidates_press=all_press_counts
        )
        results[cid]["score"] = score

    if youtube_api_called and expected_youtube_cost > 0:
        increment_youtube_quota(cost=expected_youtube_cost)

    # Afficher les erreurs des related queries si présentes
    if trends_queries_errors:
        st.warning(f"Certaines requêtes Trends ont échoué : {'; '.join(trends_queries_errors[:3])}")

    progress.empty()
    status.empty()

    return {
        "candidates": results,
        "youtube": {
            "mode": youtube_mode,
            "cache_age_hours": get_youtube_cache_age_hours(),
            "quota_remaining": get_youtube_quota_remaining(),
            "refresh_reason": youtube_refresh_reason if youtube_mode == "cache" else None,
            "cost": expected_youtube_cost
        },
        "trends_queries": {
            "cache_age_hours": get_trends_cache_age_hours(),
            "errors": trends_queries_errors if trends_queries_errors else None
        }
    }


# =============================================================================
# INTERFACE PRINCIPALE
# =============================================================================

def main():
    # Viewport meta pour iPhone + CSS responsive
    mobile_css = """<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"><style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header[data-testid="stHeader"] {height: 48px; min-height: 48px; visibility: visible; padding: 4px 0; background: transparent;}
[data-testid="collapsedControl"] {width: 60px !important; height: 60px !important;}
[data-testid="collapsedControl"] svg {width: 30px !important; height: 30px !important;}
@media screen and (max-width: 768px) {
    h1 {font-size: 1.5rem !important; line-height: 1.2 !important;}
    h2 {font-size: 1.2rem !important;}
    h3 {font-size: 1rem !important;}
    .main .block-container {padding: 1rem 0.5rem !important;}
    [data-testid="column"] {width: 100% !important; flex: 100% !important; min-width: 100% !important;}
    [data-testid="stMetric"] {padding: 0.5rem !important;}
    [data-testid="stMetricValue"] {font-size: 1.2rem !important;}
    [data-testid="stMetricLabel"] {font-size: 0.7rem !important;}
    [data-testid="stDataFrame"] th:nth-child(3), [data-testid="stDataFrame"] td:nth-child(3),
    [data-testid="stDataFrame"] th:nth-child(5), [data-testid="stDataFrame"] td:nth-child(5),
    [data-testid="stDataFrame"] th:nth-child(6), [data-testid="stDataFrame"] td:nth-child(6),
    [data-testid="stDataFrame"] th:nth-child(7), [data-testid="stDataFrame"] td:nth-child(7),
    [data-testid="stDataFrame"] th:nth-child(8), [data-testid="stDataFrame"] td:nth-child(8) {display: none !important;}
    [data-testid="stDataFrame"] {font-size: 0.8rem !important;}
    .stTabs [data-baseweb="tab-list"] {gap: 0 !important;}
    .stTabs [data-baseweb="tab"] {padding: 0.3rem 0.5rem !important; font-size: 0.75rem !important;}
    [data-testid="stExpander"] {margin-bottom: 0.5rem !important;}
    [data-testid="stPlotlyChart"] {width: 100% !important;}
    [data-testid="stSidebar"] {min-width: 250px !important; width: 250px !important;}
    .stButton > button {min-height: 44px !important; font-size: 0.9rem !important;}
    [data-testid="stMultiSelect"], [data-testid="stSelectbox"] {min-height: 44px !important;}
}
@media screen and (max-width: 380px) {
    h1 {font-size: 1.2rem !important;}
    .stTabs [data-baseweb="tab"] {padding: 0.2rem 0.3rem !important; font-size: 0.65rem !important;}
}
</style>"""
    st.markdown(mobile_css, unsafe_allow_html=True)

    st.markdown("# Baromètre de visibilité médiatique")
    st.markdown("**Élections municipales Paris 2026**")

    with st.sidebar:
        st.markdown("## Configuration")

        # Période
        st.markdown("### Période d'analyse")

        period_type = st.radio("Type de période", ["Prédéfinie", "Personnalisée"], horizontal=True)

        if period_type == "Prédéfinie":
            period_options = {"24 heures": 1, "7 jours": 7, "14 jours": 14, "30 jours": 30}
            period_label = st.selectbox("Durée", list(period_options.keys()), index=0)  # 24h par défaut
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

        st.markdown("---")
        if st.button("🔄 Rafraîchir les données", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")
        st.markdown("### Pondération du score")
        st.caption("Presse 40% · Trends 35% · Wikipedia 15% · YouTube 10%")

        st.markdown("---")
        st.caption("Kléothime Bourdon · bourdonkleothime@gmail.com")

    if not selected:
        st.warning("Veuillez sélectionner au moins un candidat")
        return

    # Gestion du refresh YouTube forcé
    force_yt_refresh = st.session_state.get("force_youtube_refresh", False)
    if force_yt_refresh:
        st.session_state["force_youtube_refresh"] = False  # Reset

    result = collect_data(selected, start_date, end_date, YOUTUBE_API_KEY, force_youtube_refresh=force_yt_refresh)
    data = result["candidates"]
    sorted_data = sorted(data.items(), key=lambda x: x[1]["score"]["total"], reverse=True)

    # === STATUS YOUTUBE ===
    yt_status = result["youtube"]
    yt_cache_age = yt_status["cache_age_hours"]
    yt_quota = yt_status["quota_remaining"]
    yt_mode = yt_status["mode"]

    # Affichage status YouTube
    with st.expander("Status YouTube API", expanded=False):
        col_yt1, col_yt2, col_yt3 = st.columns(3)

        with col_yt1:
            if yt_cache_age == float('inf'):
                st.metric("?ge des donn?es", "Jamais charg?")
            elif yt_cache_age < 1:
                st.metric("?ge des donn?es", f"{int(yt_cache_age * 60)} min")
            else:
                st.metric("?ge des donn?es", f"{yt_cache_age:.1f}h")

        with col_yt2:
            quota_pct = (yt_quota / YOUTUBE_QUOTA_DAILY_LIMIT) * 100
            st.metric("Quota restant", f"{yt_quota:,} / {YOUTUBE_QUOTA_DAILY_LIMIT:,}", f"{quota_pct:.0f}%")

        with col_yt3:
            if yt_mode == "disabled":
                st.info("API YouTube non configur?e")
            elif yt_mode == "cache":
                st.info(f"Depuis cache ({yt_status.get('refresh_reason')})")
            else:
                st.success("Donn?es fra?ches")

        # Bouton refresh manuel avec gardes-fous
        if yt_mode == "disabled":
            st.warning("Refresh impossible : cl? API YouTube absente")
        else:
            expected_cost = len(selected) * YOUTUBE_COST_PER_CANDIDATE
            can_refresh, refresh_reason = can_refresh_youtube(force=True, expected_cost=expected_cost)
            if can_refresh:
                help_text = f"Rafra?chir les donn?es YouTube (co?t estim? {expected_cost} unit?s)"
                if st.button("Forcer refresh YouTube", help=help_text):
                    st.session_state["force_youtube_refresh"] = True
                    st.rerun()
            else:
                st.warning(f"Refresh bloqu? : {refresh_reason}")

    # === CLASSEMENT ===
    st.markdown("---")
    st.markdown("## Classement général")

    rows = []
    for rank, (cid, d) in enumerate(sorted_data, 1):
        # Priorité aux Related Queries Google Trends, fallback sur mots-clés articles
        related = d.get('related_queries', {})
        top_queries = related.get('top_queries', [])

        if top_queries:
            # Utiliser les top queries Google Trends
            themes_str = ' · '.join([q['query'] for q in top_queries[:3]])
        else:
            # Fallback: mots-clés extraits des articles
            top_keywords = d.get('keywords', [])[:3]
            themes_str = ' · '.join([word for word, count, arts in top_keywords]) if top_keywords else '-'

        row = {
            'Rang': rank,
            'Candidat': d['info']['name'],
            'Parti': d['info']['party'],
            'Score': d['score']['total'],
            'Recherches': themes_str,
            'Articles': d['press']['count'],
            'Trends': d['trends_score'],
            'Wikipedia': format_number(d['wikipedia']['views']),
            'Vues YT': format_number(d['youtube'].get('total_views', 0)),
        }
        rows.append(row)

    df = pd.DataFrame(rows)

    col_config = {
        'Rang': st.column_config.NumberColumn('Rang', format='%d'),
        'Score': st.column_config.ProgressColumn('Score / 100', min_value=0, max_value=100, format='%.1f'),
        'Recherches': st.column_config.TextColumn('Top recherches Google', help='Requetes les plus frequentes associees au candidat sur Google'),
        'Articles': st.column_config.NumberColumn('Articles', format='%d'),
        'Trends': st.column_config.NumberColumn('Trends', format='%.0f'),
        'Wikipedia': st.column_config.TextColumn('Wikipedia'),
        'Vues YT': st.column_config.TextColumn('Vues YT'),
    }

    st.dataframe(df, column_config=col_config, hide_index=True, use_container_width=True)

    # Metriques
    leader = sorted_data[0][1]
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric('Leader', leader['info']['name'])
    with col2:
        st.metric('Score', f"{leader['score']['total']:.1f} / 100")
    with col3:
        total_articles = sum(d['press']['count'] for _, d in sorted_data)
        st.metric('Total articles (tous candidats)', format_number(total_articles))
    with col4:
        period_days = (end_date - start_date).days + 1
        if period_days < 2:
            st.metric('Total Wikipedia (tous candidats)', 'N/A', help='Wikipedia requiert une periode de 48h minimum')
        else:
            total_wiki = sum(d['wikipedia']['views'] for _, d in sorted_data)
            st.metric('Total Wikipedia (tous candidats)', format_number(total_wiki))

    # === ONGLETS ===
    st.markdown('---')
    st.markdown('## Visualisations detaillees')

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
        ['Scores', 'Themes', 'Sondages', 'TV / Radio', 'Historique', 'Wikipedia', 'Presse']
    )

    names = [d['info']['name'] for _, d in sorted_data]
    colors = [d['info']['color'] for _, d in sorted_data]

    # Config Plotly pour mobile (désactive zoom/pan au touch)
    plotly_config = {
        'displayModeBar': False,  # Cache la barre d'outils
        'staticPlot': False,
        'scrollZoom': False,
        'doubleClick': False,
    }

    # TAB 1: SCORES
    with tab1:
        col1, col2 = st.columns(2)

        with col1:
            scores = [d['score']['total'] for _, d in sorted_data]
            fig = px.bar(x=names, y=scores, color=names, color_discrete_sequence=colors,
                        title='Score de visibilite')
            fig.update_layout(
                showlegend=False,
                yaxis_range=[0, 100],
                yaxis_title='Score',
                xaxis_title='',
                xaxis_tickangle=-45,  # Rotation labels pour mobile
                margin=dict(b=100),  # Marge pour labels tournés
                dragmode=False,  # Désactive drag
            )
            fig.update_traces(
                hovertemplate='<b>%{x}</b><br>Score: %{y:.1f}<extra></extra>'
            )
            st.plotly_chart(fig, use_container_width=True, config=plotly_config)

        with col2:
            decomp_data = []
            for _, d in sorted_data:
                s = d['score']
                decomp_data.append({
                    'Candidat': d['info']['name'],
                    'Presse (40%)': s['contrib_press'],
                    'Trends (35%)': s['contrib_trends'],
                    'Wikipedia (15%)': s['contrib_wiki'],
                    'YouTube (10%)': s['contrib_youtube'],
                })

            df_decomp = pd.DataFrame(decomp_data)
            fig = px.bar(df_decomp, x='Candidat',
                        y=['Presse (40%)', 'Trends (35%)', 'Wikipedia (15%)', 'YouTube (10%)'],
                        barmode='stack', title='Decomposition du score',
                        color_discrete_map={
                            'Presse (40%)': '#2563eb',
                            'Trends (35%)': '#16a34a',
                            'Wikipedia (15%)': '#eab308',
                            'YouTube (10%)': '#dc2626'
                        })
            fig.update_layout(
                yaxis_range=[0, 100],
                yaxis_title='Points',
                xaxis_title='',
                xaxis_tickangle=-45,
                margin=dict(b=100),
                dragmode=False,
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
            )
            fig.update_traces(
                hovertemplate='%{y:.1f}<extra></extra>'
            )
            st.plotly_chart(fig, use_container_width=True, config=plotly_config)

    # TAB 2: THEMES / ANALYSE QUALITATIVE
    with tab2:
        st.markdown('### Ce que les gens recherchent sur Google')
        st.markdown('*Requetes associees a chaque candidat sur Google Trends (France)*')

        # Afficher le statut du cache Trends
        trends_cache_age = result.get("trends_queries", {}).get("cache_age_hours", float('inf'))
        if trends_cache_age != float('inf') and trends_cache_age < TRENDS_CACHE_DURATION_HOURS:
            st.caption(f"Donnees en cache (age: {trends_cache_age:.1f}h)")

        for rank, (cid, d) in enumerate(sorted_data, 1):
            related = d.get('related_queries', {})
            keywords = d.get('keywords', [])  # Fallback
            name = d['info']['name']

            top_queries = related.get('top_queries', [])
            has_trends_data = len(top_queries) > 0

            # Titre avec indicateur de source
            if has_trends_data:
                title = f'{rank}. {name} - Recherches Google'
            else:
                title = f'{rank}. {name} - Themes presse (fallback)'

            with st.expander(title, expanded=(rank <= 3)):
                if has_trends_data:
                    st.markdown('**Top recherches Google**')
                    st.caption('Ce que les gens recherchent en association avec ce candidat')
                    if top_queries:
                        for q in top_queries[:7]:
                            query_text = q.get('query', '')
                            value = q.get('value', 0)
                            st.markdown(f"**{query_text}**")
                            st.progress(min(value / 100, 1.0))
                    else:
                        st.info('Aucune donnee')

                    # Afficher aussi les themes presse en complement
                    if keywords:
                        st.markdown('---')
                        st.markdown('**Complement: Themes dans la presse**')
                        themes_str = ' · '.join([f"{word} ({count})" for word, count, _ in keywords[:5]])
                        st.caption(themes_str)

                elif keywords:
                    # Fallback: afficher les mots-cles des articles
                    st.warning('Google Trends indisponible, affichage des themes presse')
                    for word, count, articles in keywords:
                        with st.expander(f'**{word}** ({count} mentions)', expanded=False):
                            if articles:
                                for art in articles[:10]:
                                    st.markdown(f"- [{art.get('title', 'Sans titre')}]({art.get('url', '#')})")
                                    st.caption(f"   {art.get('date', '')} - {art.get('domain', '')}")
                                if len(articles) > 10:
                                    st.caption(f"... et {len(articles) - 10} autres articles")
                else:
                    st.info('Aucune donnee disponible')

                # Erreur Trends si presente
                if related.get('error'):
                    st.error(f"Erreur Trends: {related['error']}")

        # === TABLEAU RECAPITULATIF TOP QUERIES ===
        st.markdown('---')
        st.markdown('### Tableau recapitulatif')

        recap_data = []
        for _, d in sorted_data:
            related = d.get('related_queries', {})
            top_queries = related.get('top_queries', [])
            # Extraire les 3 premieres requetes
            top_3 = [q['query'] for q in top_queries[:3]]

            recap_data.append({
                'Candidat': d['info']['name'],
                'Recherche 1': top_3[0] if len(top_3) > 0 else '-',
                'Recherche 2': top_3[1] if len(top_3) > 1 else '-',
                'Recherche 3': top_3[2] if len(top_3) > 2 else '-',
            })

        st.dataframe(pd.DataFrame(recap_data), use_container_width=True, hide_index=True)
    # TAB 3: SONDAGES
    with tab3:
        st.markdown("### Sondages d'intentions de vote")

        # Recharger les sondages
        sondages_actuels = load_sondages()

        if sondages_actuels:
            # === GRAPHIQUE SYNTHESE TOUS SONDAGES ===
            st.markdown("#### Synthese de tous les sondages")

            # Calculer la moyenne par candidat sur tous les sondages
            all_scores = {}
            for sondage in sondages_actuels:
                for candidat, score in sondage["scores"].items():
                    if candidat not in all_scores:
                        all_scores[candidat] = []
                    all_scores[candidat].append(score)

            # Moyenne et dernier score
            synthesis_data = []
            for candidat, scores in all_scores.items():
                synthesis_data.append({
                    "Candidat": candidat,
                    "Moyenne": round(sum(scores) / len(scores), 1),
                    "Dernier": scores[-1] if scores else 0,
                    "Min": min(scores),
                    "Max": max(scores),
                    "Nb sondages": len(scores)
                })

            synthesis_data.sort(key=lambda x: x["Moyenne"], reverse=True)
            color_map = {c["name"]: c["color"] for c in CANDIDATES.values()}

            # Graphique avec barres d'erreur (min-max)
            fig_synthesis = go.Figure()
            for item in synthesis_data:
                candidat = item["Candidat"]
                color = color_map.get(candidat, "#888")
                fig_synthesis.add_trace(go.Bar(
                    name=candidat,
                    x=[candidat],
                    y=[item["Moyenne"]],
                    marker_color=color,
                    error_y=dict(
                        type='data',
                        symmetric=False,
                        array=[item["Max"] - item["Moyenne"]],
                        arrayminus=[item["Moyenne"] - item["Min"]],
                        color='rgba(0,0,0,0.3)'
                    ),
                    hovertemplate=f'<b>{candidat}</b><br>Moyenne: {item["Moyenne"]}%<br>Min: {item["Min"]}% - Max: {item["Max"]}%<extra></extra>'
                ))

            fig_synthesis.update_layout(
                title="Moyenne des intentions de vote (tous sondages confondus)",
                showlegend=False,
                yaxis_title="Intentions de vote (%)",
                yaxis_range=[0, 45],
                xaxis_title=""
            )
            st.plotly_chart(fig_synthesis, use_container_width=True, config=plotly_config)

            # Tableau synthese
            st.dataframe(
                pd.DataFrame(synthesis_data)[["Candidat", "Moyenne", "Min", "Max", "Nb sondages"]],
                use_container_width=True,
                hide_index=True
            )

            st.markdown("---")

            # === EVOLUTION TEMPORELLE ===
            st.markdown("#### Evolution dans le temps")

            # Regrouper par date unique (prendre la moyenne si plusieurs hypotheses meme jour)
            date_scores = {}
            for sondage in sondages_actuels:
                date_key = sondage["date"]
                if date_key not in date_scores:
                    date_scores[date_key] = {}
                for candidat, score in sondage["scores"].items():
                    if candidat not in date_scores[date_key]:
                        date_scores[date_key][candidat] = []
                    date_scores[date_key][candidat].append(score)

            evolution_data = []
            for date_key, candidats in sorted(date_scores.items()):
                for candidat, scores in candidats.items():
                    evolution_data.append({
                        "Date": date_key,
                        "Candidat": candidat,
                        "Score": round(sum(scores) / len(scores), 1)
                    })

            df_evolution = pd.DataFrame(evolution_data)

            fig_evolution = px.line(
                df_evolution,
                x="Date",
                y="Score",
                color="Candidat",
                markers=True,
                color_discrete_map=color_map,
                title="Evolution des intentions de vote"
            )
            fig_evolution.update_layout(
                yaxis_range=[0, 45],
                yaxis_title="Intentions de vote (%)",
                xaxis_title="",
                legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5),
                height=500,
                margin=dict(b=100)
            )
            fig_evolution.update_traces(
                hovertemplate='<b>%{fullData.name}</b><br>%{x}<br>%{y}%<extra></extra>'
            )
            st.plotly_chart(fig_evolution, use_container_width=True, config=plotly_config)

            st.markdown("---")

            # === DETAIL PAR SONDAGE ===
            st.markdown("#### Detail par sondage")

            for sondage in sorted(sondages_actuels, key=lambda x: x["date"], reverse=True):
                with st.expander(f"{sondage['institut']} - {sondage['date']} - {sondage['hypothese'][:50]}...", expanded=(sondage == get_latest_sondage())):
                    col_info, col_chart = st.columns([1, 2])

                    with col_info:
                        st.markdown(f"**Commanditaire:** {sondage['commanditaire']}")
                        st.markdown(f"**Echantillon:** {sondage['echantillon']} personnes")
                        st.markdown(f"**Methode:** {sondage['methode']}")
                        st.markdown(f"**Hypothese:** {sondage['hypothese']}")
                        if sondage.get("source_url"):
                            st.markdown(f"[Voir le sondage]({sondage['source_url']})")

                    with col_chart:
                        sondage_rows = []
                        for name, score in sorted(sondage["scores"].items(), key=lambda x: x[1], reverse=True):
                            party = next((c["party"] for c in CANDIDATES.values() if c["name"] == name), "-")
                            sondage_rows.append({
                                "Candidat": name,
                                "Parti": party,
                                "Intentions": f"{score}%"
                            })

                        sondage_colors = [color_map.get(r["Candidat"], "#888") for r in sondage_rows]

                        fig = px.bar(
                            x=[r["Candidat"] for r in sondage_rows],
                            y=[int(r["Intentions"].replace("%", "")) for r in sondage_rows],
                            color=[r["Candidat"] for r in sondage_rows],
                            color_discrete_sequence=sondage_colors
                        )
                        fig.update_layout(
                            showlegend=False,
                            yaxis_title="%",
                            yaxis_range=[0, 40],
                            xaxis_title="",
                            height=300,
                            margin=dict(t=10)
                        )
                        st.plotly_chart(fig, use_container_width=True, config=plotly_config)

        else:
            st.info("Aucun sondage disponible")

    # TAB 4: TV/RADIO
    with tab4:
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

        for cid, d in sorted_data:
            tv = d.get("tv_radio", {})
            mentions = tv.get("mentions", [])

            if mentions:
                with st.expander(f"{d['info']['name']} - {len(mentions)} mention(s)"):
                    # Clé unique pour chaque candidat
                    show_all_mentions_key = f"show_all_mentions_{cid}"
                    if show_all_mentions_key not in st.session_state:
                        st.session_state[show_all_mentions_key] = False

                    # Afficher toutes les mentions ou seulement les 20 premières
                    mentions_to_show = mentions if st.session_state[show_all_mentions_key] else mentions[:20]

                    for i, mention in enumerate(mentions_to_show, 1):
                        st.markdown(f"**{i}.** [{mention['title']}]({mention['url']})")
                        st.caption(f"{mention['date']} · {mention['source']} · {mention['media']}")

                    # Bouton pour afficher plus/moins
                    if len(mentions) > 20:
                        if st.session_state[show_all_mentions_key]:
                            if st.button(f"Voir moins", key=f"btn_less_mentions_{cid}"):
                                st.session_state[show_all_mentions_key] = False
                                st.rerun()
                        else:
                            if st.button(f"Voir plus ({len(mentions) - 20} autres mentions)", key=f"btn_more_mentions_{cid}"):
                                st.session_state[show_all_mentions_key] = True
                                st.rerun()

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
            st.plotly_chart(fig, use_container_width=True, config=plotly_config)

    # TAB 5: HISTORIQUE
    with tab5:
        st.markdown("### Évolution des scores de visibilité")

        # Bouton pour construire l'historique automatiquement
        col_btn1, col_btn2 = st.columns([1, 3])
        with col_btn1:
            if st.button("Générer l'historique automatique", type="primary"):
                with st.spinner("Analyse des 8 dernières semaines en cours..."):
                    # Construire l'historique des 8 dernières semaines (56 jours = 2 mois)
                    today = datetime.now().date()

                    # Supprimer l'ancien historique
                    save_history([])

                    progress_bar = st.progress(0)

                    for week_num in range(8):
                        # Calculer les dates de la semaine
                        week_end = today - timedelta(days=week_num * 7)
                        week_start = week_end - timedelta(days=6)

                        # Collecter les données pour cette semaine
                        week_result = collect_data(selected, week_start, week_end, YOUTUBE_API_KEY)
                        week_data = week_result["candidates"]

                        # Enregistrer dans l'historique
                        period_label = f"{week_start} à {week_end}"
                        add_to_history(week_data, period_label, week_end)

                        progress_bar.progress((week_num + 1) / 8)

                    st.success("Historique généré avec succès sur 8 semaines")
                    st.rerun()

        with col_btn2:
            st.caption("Analyse automatique des 8 dernières semaines (56 jours)")

        # Charger l'historique existant
        history = load_history()

        if history and len(history) >= 1:
            # Construire les données pour le graphique
            history_df_data = []
            for entry in sorted(history, key=lambda x: x.get("date")):
                for name, scores in entry.get("scores", {}).items():
                    history_df_data.append({
                        "Date": entry.get("date"),
                        "Candidat": name,
                        "Score": scores["total"]
                    })

            if history_df_data:
                df_hist = pd.DataFrame(history_df_data)
                color_map = {c["name"]: c["color"] for c in CANDIDATES.values()}

                unique_dates = df_hist["Date"].nunique()

                if unique_dates == 1:
                    st.info(f"Historique : {unique_dates} semaine enregistrée")
                else:
                    st.success(f"Historique : {unique_dates} semaines enregistrées")

                # Graphique d'évolution avec Knafo mise en avant
                fig = go.Figure()

                # Couleur vive pour Knafo
                KNAFO_COLOR = "#E63946"  # Rouge vif intense

                # Couleurs pâles distinctes pour les concurrents
                PALE_COLORS = {
                    "Rachida Dati": "#B8D4E3",       # Bleu pâle
                    "Emmanuel Grégoire": "#F5CEC7",  # Rose saumon pâle
                    "David Belliard": "#C7E9C0",     # Vert pâle
                    "Pierre-Yves Bournazel": "#E2D4F0",  # Violet pâle
                    "Sophia Chikirou": "#FFE5B4",    # Pêche pâle
                    "Thierry Mariani": "#D4E5F7",    # Bleu ciel pâle
                    "Ian Brossat": "#FADADD",        # Rose pâle
                }

                # D'abord ajouter tous les concurrents (en arrière-plan, couleurs pâles)
                for candidate_name in color_map.keys():
                    if candidate_name == "Sarah Knafo":
                        continue  # On l'ajoute après pour qu'elle soit au premier plan

                    candidate_data = df_hist[df_hist["Candidat"] == candidate_name]
                    if not candidate_data.empty:
                        pale_color = PALE_COLORS.get(candidate_name, "#D3D3D3")
                        fig.add_trace(go.Scatter(
                            x=candidate_data["Date"],
                            y=candidate_data["Score"],
                            name=candidate_name,
                            mode='lines+markers',
                            line=dict(
                                color=pale_color,
                                width=2
                            ),
                            marker=dict(
                                symbol='circle',
                                size=7,
                                color=pale_color,
                                line=dict(color='white', width=1)
                            ),
                            opacity=0.7,
                            hovertemplate='<b>%{fullData.name}</b><br>Score: %{y:.1f}<extra></extra>'
                        ))

                # Ensuite ajouter Knafo au premier plan avec style qui claque
                knafo_data = df_hist[df_hist["Candidat"] == "Sarah Knafo"]
                if not knafo_data.empty:
                    fig.add_trace(go.Scatter(
                        x=knafo_data["Date"],
                        y=knafo_data["Score"],
                        name="Sarah Knafo",
                        mode='lines+markers',
                        line=dict(
                            color=KNAFO_COLOR,
                            width=4
                        ),
                        marker=dict(
                            symbol='diamond',
                            size=12,
                            color=KNAFO_COLOR,
                            line=dict(color='white', width=2)
                        ),
                        hovertemplate='<b>Sarah Knafo</b><br>Score: %{y:.1f}<extra></extra>'
                    ))

                fig.update_layout(
                    title="Évolution temporelle",
                    yaxis_range=[0, 100],
                    yaxis_title="Score de visibilité",
                    xaxis_title="",
                    legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5),
                    height=500,
                    margin=dict(b=100)
                )
                st.plotly_chart(fig, use_container_width=True, config=plotly_config)

                # Tableau des variations
                if unique_dates > 1:
                    st.markdown("### Variations par période")

                    # Trouver la date la plus récente dans l'historique
                    latest_date = max(entry["date"] for entry in history)
                    latest_entry = next(e for e in history if e["date"] == latest_date)

                    var_rows = []
                    for candidate_name in color_map.keys():
                        if candidate_name in latest_entry.get("scores", {}):
                            current = latest_entry["scores"][candidate_name]["total"]
                            hist = get_historical_comparison(candidate_name, current, latest_date)

                            if hist.get("available"):
                                changes = hist.get("changes", {})
                                row = {
                                    "Candidat": candidate_name,
                                    "Actuel": f"{current:.1f}",
                                    "vs 7j": f"{changes['7j']:+.1f}" if changes.get('7j') is not None else "-",
                                    "vs 14j": f"{changes['14j']:+.1f}" if changes.get('14j') is not None else "-",
                                    "vs 30j": f"{changes['30j']:+.1f}" if changes.get('30j') is not None else "-",
                                }
                            else:
                                row = {
                                    "Candidat": candidate_name,
                                    "Actuel": f"{current:.1f}",
                                    "vs 7j": "-",
                                    "vs 14j": "-",
                                    "vs 30j": "-",
                                }
                            var_rows.append(row)

                    st.dataframe(pd.DataFrame(var_rows), use_container_width=True, hide_index=True)
        else:
            st.info("Aucun historique disponible")

    # TAB 6: WIKIPEDIA
    with tab6:
        days_in_period = (end_date - start_date).days + 1

        if days_in_period < 2:
            st.warning("Wikipedia requiert une période de 48h minimum. Les données affichées peuvent être incomplètes.")

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
            st.plotly_chart(fig, use_container_width=True, config=plotly_config)

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
            st.plotly_chart(fig, use_container_width=True, config=plotly_config)

    # TAB 7: PRESSE
    with tab7:
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
            st.plotly_chart(fig, use_container_width=True, config=plotly_config)

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
            st.plotly_chart(fig, use_container_width=True, config=plotly_config)

    # === ARTICLES ===
    st.markdown("---")
    st.markdown("## Articles de presse")

    for rank, (cid, d) in enumerate(sorted_data, 1):
        arts = d["press"]["articles"]
        with st.expander(f"{rank}. {d['info']['name']} — {len(arts)} article(s)"):
            if arts:
                # Clé unique pour chaque candidat
                show_all_key = f"show_all_articles_{cid}"
                if show_all_key not in st.session_state:
                    st.session_state[show_all_key] = False

                # Afficher tous les articles ou seulement les 15 premiers
                articles_to_show = arts if st.session_state[show_all_key] else arts[:15]

                for i, a in enumerate(articles_to_show, 1):
                    st.markdown(f"**{i}.** [{a['title']}]({a['url']})")
                    st.caption(f"{a['date']} · {a['domain']}")

                # Bouton pour afficher plus/moins
                if len(arts) > 15:
                    if st.session_state[show_all_key]:
                        if st.button(f"Voir moins", key=f"btn_less_{cid}"):
                            st.session_state[show_all_key] = False
                            st.rerun()
                    else:
                        if st.button(f"Voir plus ({len(arts) - 15} autres articles)", key=f"btn_more_{cid}"):
                            st.session_state[show_all_key] = True
                            st.rerun()
            else:
                st.info("Aucun article trouvé")

    # === YOUTUBE ===
    st.markdown("---")
    st.markdown("## Vidéos YouTube publiées sur la période")

    if not any(d["youtube"].get("available") for _, d in sorted_data):
        st.info("Aucune vidéo YouTube trouvée pour la période sélectionnée")
    else:
        for rank, (cid, d) in enumerate(sorted_data, 1):
            yt = d["youtube"]
            if yt.get("available") and yt.get("videos"):
                with st.expander(f"{rank}. {d['info']['name']} — {format_number(yt['total_views'])} vues"):
                    # Clé unique pour chaque candidat
                    show_all_videos_key = f"show_all_videos_{cid}"
                    if show_all_videos_key not in st.session_state:
                        st.session_state[show_all_videos_key] = False

                    # Afficher toutes les vidéos ou seulement les 10 premières
                    videos_to_show = yt["videos"] if st.session_state[show_all_videos_key] else yt["videos"][:10]

                    for i, v in enumerate(videos_to_show, 1):
                        views = v.get("views", 0)
                        st.markdown(f"**{i}.** [{v['title']}]({v['url']}) — {format_number(views)} vues")
                        st.caption(f"{v.get('published', '')} · {v.get('channel', '')}")

                    # Bouton pour afficher plus/moins
                    if len(yt["videos"]) > 10:
                        if st.session_state[show_all_videos_key]:
                            if st.button(f"Voir moins", key=f"btn_less_videos_{cid}"):
                                st.session_state[show_all_videos_key] = False
                                st.rerun()
                        else:
                            if st.button(f"Voir plus ({len(yt['videos']) - 10} autres vidéos)", key=f"btn_more_videos_{cid}"):
                                st.session_state[show_all_videos_key] = True
                                st.rerun()


if __name__ == "__main__":
    main()
