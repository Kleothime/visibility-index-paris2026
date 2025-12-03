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
YOUTUBE_CACHE_DURATION_HOURS = 12  # Cache YouTube pendant 12h

# Noms de médias à exclure des mots-clés extraits
MEDIA_NAMES = {
    "gala", "figaro", "monde", "parisien", "liberation", "libération", "humanite", "humanité",
    "express", "point", "obs", "nouvelobs", "marianne", "valeurs", "actuelles", "cnews",
    "bfmtv", "bfm", "lci", "tf1", "france", "info", "infos", "rfi", "rmc", "europe",
    "rtl", "radio", "télé", "tele", "20minutes", "minutes", "huffpost", "huffington",
    "mediapart", "lexpress", "lepoint", "lemonde", "lefigaro", "leparisien", "ouest",
    "sudouest", "voici", "closer", "public", "purepeople", "people", "madame", "elle",
    "paris", "match", "parismatch", "afp", "reuters", "actu", "news", "info", "presse",
    "journal", "quotidien", "hebdo", "magazine", "média", "media", "article", "source",
    "interview", "vidéo", "video", "photo", "image", "exclusif", "breaking", "alerte",
    "direct", "live", "replay", "podcast", "émission", "emission",
    # Ajouts
    "jdd", "lejdd", "opinion", "lopinion", "tribune", "latribune", "echos", "lesechos",
    "telegramme", "dépêche", "depeche", "provençal", "provencal", "dauphine", "dauphiné"
}


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
            "data": {},
            "period_refreshes": {},
            "last_valid": {}
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
        return float('inf')

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

    if cache.get("quota_date") != today:
        return YOUTUBE_QUOTA_DAILY_LIMIT

    return max(0, YOUTUBE_QUOTA_DAILY_LIMIT - cache.get("quota_used", 0))


YOUTUBE_24H_COOLDOWN_HOURS = 2  # Cooldown de 2h pour la période 24h
YOUTUBE_LONG_PERIOD_MAX_PER_DAY = 1  # Max 1 requête/jour pour 7j, 14j, 30j


def can_refresh_youtube_for_period(period_type: str, expected_cost: int = 0) -> tuple[bool, str]:
    """
    Vérifie si on peut faire une requête YouTube pour ce type de période.
    - 24h : cooldown de 2h entre les requêtes + vérification quota API
    - 7d/14d/30d : max 1 requête par jour + vérification quota API
    """
    cache = load_youtube_cache()
    today = datetime.now().strftime("%Y-%m-%d")

    # Vérifier le quota API YouTube global
    remaining_quota = get_youtube_quota_remaining()
    if expected_cost > 0 and remaining_quota < expected_cost:
        return False, f"Quota API insuffisant ({remaining_quota})"

    period_refreshes = cache.get("period_refreshes", {})
    period_info = period_refreshes.get(period_type, {})

    # Reset si nouveau jour
    if period_info.get("date") != today:
        return True, "OK"

    if period_type == "24h":
        # Pour 24h : vérifier le cooldown
        last_refresh = period_info.get("last_refresh")
        if last_refresh:
            try:
                last_dt = datetime.fromisoformat(last_refresh)
                age_hours = (datetime.now() - last_dt).total_seconds() / 3600
                if age_hours < YOUTUBE_24H_COOLDOWN_HOURS:
                    remaining = int((YOUTUBE_24H_COOLDOWN_HOURS - age_hours) * 60)
                    return False, f"Cooldown 24h ({remaining} min)"
            except:
                pass
        return True, "OK"
    else:
        # Pour 7d/14d/30d : max 1 par jour
        count = period_info.get("count", 0)
        if count >= YOUTUBE_LONG_PERIOD_MAX_PER_DAY:
            return False, f"Limite {period_type} (1/jour)"
        return True, "OK"


def increment_youtube_period_refresh(period_type: str, cost: int = 0):
    """Incrémente le compteur de refresh YouTube pour un type de période"""
    cache = load_youtube_cache()
    today = datetime.now().strftime("%Y-%m-%d")

    # Incrémenter le quota API global
    if cost > 0:
        if cache.get("quota_date") != today:
            cache["quota_date"] = today
            cache["quota_used"] = 0
        cache["quota_used"] = cache.get("quota_used", 0) + cost

    # Incrémenter le compteur par période
    if "period_refreshes" not in cache:
        cache["period_refreshes"] = {}

    if period_type not in cache["period_refreshes"] or cache["period_refreshes"][period_type].get("date") != today:
        cache["period_refreshes"][period_type] = {"date": today, "count": 0}

    cache["period_refreshes"][period_type]["count"] += 1
    cache["period_refreshes"][period_type]["last_refresh"] = datetime.now().isoformat()
    cache["last_refresh"] = datetime.now().isoformat()

    save_youtube_cache(cache)


def save_youtube_last_valid(period_type: str, candidate_name: str, data: Dict):
    """Sauvegarde les dernières données YouTube valides pour un candidat et type de période"""
    if data.get("total_views", 0) <= 0:
        return  # Ne pas sauvegarder de données vides

    cache = load_youtube_cache()

    if "last_valid" not in cache:
        cache["last_valid"] = {}
    if period_type not in cache["last_valid"]:
        cache["last_valid"][period_type] = {}

    cache["last_valid"][period_type][candidate_name] = {
        "payload": data,
        "timestamp": datetime.now().isoformat()
    }

    save_youtube_cache(cache)


def get_youtube_last_valid(period_type: str, candidate_name: str) -> Optional[Dict]:
    """Récupère les dernières données YouTube valides pour un candidat"""
    cache = load_youtube_cache()

    # 1. Essayer le type de période exact
    last_valid = cache.get("last_valid", {}).get(period_type, {}).get(candidate_name)
    if last_valid:
        payload = last_valid.get("payload", {})
        if payload.get("total_views", 0) > 0:
            result = dict(payload)
            result["is_fallback"] = True
            result["fallback_period"] = period_type
            return result

    # 2. Chercher dans les autres types de période
    for pt in ["24h", "7d", "14d", "30d"]:
        if pt != period_type:
            last_valid = cache.get("last_valid", {}).get(pt, {}).get(candidate_name)
            if last_valid:
                payload = last_valid.get("payload", {})
                if payload.get("total_views", 0) > 0:
                    result = dict(payload)
                    result["is_fallback"] = True
                    result["fallback_period"] = pt
                    return result

    return None


def get_cached_youtube_data_for_period(candidate_name: str, start_date: date, end_date: date) -> Optional[Dict]:
    """
    Récupère le cache YouTube pour un candidat et une période.
    Cherche d'abord une correspondance exacte, puis le fallback last_valid.
    """
    cache = load_youtube_cache()
    period_type = get_period_type(start_date, end_date)
    candidate_cache = cache.get("data", {}).get(candidate_name, {})

    # 1. Chercher correspondance exacte
    period_key = f"{start_date.isoformat()}_{end_date.isoformat()}"
    if period_key in candidate_cache:
        entry = candidate_cache[period_key]
        payload = entry.get("payload")
        if isinstance(payload, dict) and payload.get("total_views", 0) > 0:
            result = dict(payload)
            result["cache_exact_match"] = True
            result["available"] = True
            return result

    # 2. Chercher dans last_valid (fallback)
    fallback = get_youtube_last_valid(period_type, candidate_name)
    if fallback:
        fallback["cache_exact_match"] = False
        fallback["available"] = True
        return fallback

    return None


def set_cached_youtube_data(candidate_name: str, data: Dict, start_date: date, end_date: date):
    """Stocke les données YouTube en cache pour un candidat et une période"""
    if data.get("total_views", 0) <= 0:
        return  # Ne pas cacher de données vides

    cache = load_youtube_cache()
    period_type = get_period_type(start_date, end_date)

    if "data" not in cache:
        cache["data"] = {}
    if candidate_name not in cache["data"]:
        cache["data"][candidate_name] = {}

    period_key = f"{start_date.isoformat()}_{end_date.isoformat()}"
    cache["data"][candidate_name][period_key] = {
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "payload": data
    }

    # Garder max 10 périodes par candidat
    if len(cache["data"][candidate_name]) > 10:
        sorted_keys = sorted(cache["data"][candidate_name].keys())
        for old_key in sorted_keys[:-10]:
            del cache["data"][candidate_name][old_key]

    save_youtube_cache(cache)

    # Sauvegarder aussi comme last_valid
    save_youtube_last_valid(period_type, candidate_name, data)


# =============================================================================
# CACHE GOOGLE TRENDS - SYSTÈME INTELLIGENT PAR PÉRIODE
# =============================================================================

TRENDS_CACHE_FILE = "trends_cache.json"
TRENDS_24H_COOLDOWN_HOURS = 2  # Cooldown de 2h pour la période 24h
TRENDS_LONG_PERIOD_MAX_PER_DAY = 1  # Max 1 requête/jour pour 7j, 14j, 30j


def get_period_type(start_date: date, end_date: date) -> str:
    """Détermine le type de période : 24h, 7d, 14d, 30d"""
    days = (end_date - start_date).days + 1
    if days <= 1:
        return "24h"
    elif days <= 7:
        return "7d"
    elif days <= 14:
        return "14d"
    else:
        return "30d"


def load_trends_cache() -> Dict:
    """Charge le cache Google Trends"""
    try:
        with open(TRENDS_CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {
            "last_refresh": None,
            "data": {},
            "period_refreshes": {},
            "last_valid": {}
        }


def save_trends_cache(cache: Dict) -> bool:
    """Sauvegarde le cache Trends"""
    try:
        with open(TRENDS_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
        return True
    except:
        return False


def get_time_until_quota_reset() -> str:
    """Retourne le temps restant jusqu'à 9h (reset des quotas)"""
    now = datetime.now()
    reset_today = datetime(now.year, now.month, now.day, 9, 0, 0)
    if now.hour >= 9:
        reset_time = reset_today + timedelta(days=1)
    else:
        reset_time = reset_today

    delta = reset_time - now
    hours = int(delta.total_seconds() // 3600)
    minutes = int((delta.total_seconds() % 3600) // 60)
    if hours > 0:
        return f"{hours}h{minutes:02d}"
    return f"{minutes} min"


def can_refresh_trends(period_type: str) -> tuple[bool, str]:
    """
    Vérifie si on peut faire une requête Trends pour ce type de période.
    - 24h : cooldown de 2h entre les requêtes
    - 7d/14d/30d : max 1 requête par jour
    """
    cache = load_trends_cache()
    today = datetime.now().strftime("%Y-%m-%d")

    period_refreshes = cache.get("period_refreshes", {})
    period_info = period_refreshes.get(period_type, {})

    # Reset si nouveau jour
    if period_info.get("date") != today:
        return True, "OK"

    if period_type == "24h":
        # Pour 24h : vérifier le cooldown
        last_refresh = period_info.get("last_refresh")
        if last_refresh:
            try:
                last_dt = datetime.fromisoformat(last_refresh)
                age_hours = (datetime.now() - last_dt).total_seconds() / 3600
                if age_hours < TRENDS_24H_COOLDOWN_HOURS:
                    remaining = int((TRENDS_24H_COOLDOWN_HOURS - age_hours) * 60)
                    return False, f"Cooldown 24h ({remaining} min)"
            except:
                pass
        return True, "OK"
    else:
        # Pour 7d/14d/30d : max 1 par jour
        count = period_info.get("count", 0)
        if count >= TRENDS_LONG_PERIOD_MAX_PER_DAY:
            return False, f"Limite atteinte pour {period_type} (1/jour)"
        return True, "OK"


def increment_trends_period_refresh(period_type: str):
    """Incrémente le compteur de refresh pour un type de période"""
    cache = load_trends_cache()
    today = datetime.now().strftime("%Y-%m-%d")

    if "period_refreshes" not in cache:
        cache["period_refreshes"] = {}

    if period_type not in cache["period_refreshes"] or cache["period_refreshes"][period_type].get("date") != today:
        cache["period_refreshes"][period_type] = {"date": today, "count": 0}

    cache["period_refreshes"][period_type]["count"] += 1
    cache["period_refreshes"][period_type]["last_refresh"] = datetime.now().isoformat()

    save_trends_cache(cache)


def save_trends_last_valid(period_type: str, scores: Dict, keywords: List[str]):
    """Sauvegarde les dernières données valides pour un type de période"""
    cache = load_trends_cache()

    if "last_valid" not in cache:
        cache["last_valid"] = {}

    cache["last_valid"][period_type] = {
        "scores": scores,
        "keywords": keywords,
        "timestamp": datetime.now().isoformat()
    }

    save_trends_cache(cache)


def get_trends_last_valid(period_type: str, keywords: List[str]) -> Optional[Dict]:
    """Récupère les dernières données valides pour un type de période"""
    cache = load_trends_cache()
    last_valid = cache.get("last_valid", {}).get(period_type)

    if not last_valid:
        return None

    # Vérifier que les mots-clés correspondent (même candidats)
    cached_keywords = set(last_valid.get("keywords", []))
    requested_keywords = set(keywords)

    # Si au moins 80% des candidats correspondent, on peut utiliser le fallback
    if len(cached_keywords & requested_keywords) >= len(requested_keywords) * 0.8:
        scores = last_valid.get("scores", {})
        # Ne retourner que les scores des candidats demandés
        filtered_scores = {kw: scores.get(kw, 0.0) for kw in keywords}
        if any(v > 0 for v in filtered_scores.values()):
            return {
                "scores": filtered_scores,
                "timestamp": last_valid.get("timestamp"),
                "is_fallback": True
            }

    return None


def get_trends_cache_age_hours(cache_key: str = None) -> float:
    """Retourne l'âge du cache Trends en heures"""
    cache = load_trends_cache()

    if cache_key:
        entry = cache.get("data", {}).get(cache_key)
        if entry and entry.get("timestamp"):
            try:
                entry_dt = datetime.fromisoformat(entry["timestamp"])
                return (datetime.now() - entry_dt).total_seconds() / 3600
            except:
                pass
        return float('inf')

    last_refresh = cache.get("last_refresh")
    if not last_refresh:
        return float('inf')
    try:
        last_dt = datetime.fromisoformat(last_refresh)
        return (datetime.now() - last_dt).total_seconds() / 3600
    except:
        return float('inf')


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


def format_candidate_name(name: str, html: bool = False) -> str:
    """Formate le nom du candidat - Sarah Knafo en gras"""
    if name == "Sarah Knafo":
        if html:
            return f"<b>{name}</b>"
        return f"**{name}**"
    return name


def is_sarah_knafo(name: str) -> bool:
    """Vérifie si c'est Sarah Knafo"""
    return name == "Sarah Knafo"


# Mots vides français à ignorer dans l'analyse
STOP_WORDS = {
    # Mots grammaticaux de base
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
    "mon", "ma", "mes", "ton", "ta", "tes", "notre", "nos", "votre", "vos",
    "quel", "quelle", "quels", "quelles", "lequel", "laquelle", "lesquels", "lesquelles",
    "chaque", "quelque", "quelques", "certain", "certaine", "certains", "certaines",
    "aucun", "aucune", "tel", "telle", "tels", "telles", "tant", "peu", "beaucoup",
    "trop", "assez", "autant", "combien", "comment", "pourquoi", "parce",

    # Lieux génériques
    "paris", "parisien", "parisiens", "parisienne", "parisiennes", "capitale",
    "france", "français", "française", "françaises", "ile", "île",
    "ville", "villes", "arrondissement", "arrondissements", "quartier", "quartiers",
    "rue", "avenue", "boulevard", "place", "métro", "metro",

    # Élections / politique générique
    "municipales", "municipal", "municipale", "élection", "élections", "vote", "votes", "voter",
    "candidat", "candidate", "candidats", "candidates", "candidature", "candidatures",
    "mairie", "maire", "maires", "campagne", "campagnes", "électeur", "électeurs", "électoral",
    "ministre", "ministère", "député", "députée", "députés", "sénateur", "sénatrice",
    "politique", "politiques", "gouvernement", "parti", "partis", "droite", "gauche",
    "opposition", "majorité", "assemblée", "sénat", "élysée", "matignon",

    # Médias et journalisme
    "bfm", "bfmtv", "rtl", "cnews", "rmc", "lci", "tf1", "france", "radio",
    "agence", "presse", "afp", "reuters", "média", "médias", "journal", "journaux",
    "figaro", "monde", "libération", "liberation", "parisien", "ouest", "sud",
    "actu", "actualités", "actualites", "news", "info", "infos", "minutes",
    "interview", "interviews", "émission", "plateau", "direct", "live",
    "exclusif", "exclusivité", "révélation", "scoop", "breaking",

    # Verbes journalistiques et génériques (infinitifs + conjugaisons)
    "lance", "annonce", "révèle", "affirme", "confie", "déclare", "explique",
    "raconte", "officialise", "présente", "veut", "souhaite", "demande",
    "faut", "falloir", "doit", "peut", "pourrait", "devrait", "soit", "être",
    "mettre", "créer", "faire", "aller", "allant", "avoir", "venir", "prendre",
    "pris", "prise", "dit", "dire", "parle", "parler", "parlé", "montre", "montrer",
    "trouve", "trouver", "sait", "savoir", "croit", "croire", "pense", "penser",
    "reste", "rester", "devient", "devenir", "tient", "tenir", "donne", "donner",
    "met", "mis", "mise", "prend", "rendu", "rendue", "laisse", "laisser",
    "sort", "sortir", "sorti", "sortie", "entre", "entrer", "entré", "entrée",
    "répond", "répondre", "répondu", "pose", "poser", "posé", "posée",
    "attend", "attendre", "attendu", "propose", "proposer", "proposé",
    "revient", "revenir", "revenu", "revenue", "appelle", "appeler", "appelé",
    # Verbes conjugués courants (imparfait, passé, etc.)
    "pouvait", "devait", "avait", "était", "allait", "faisait", "disait", "voyait",
    "voulait", "savait", "venait", "tenait", "prenait", "mettait", "donnait",
    "perdre", "perdu", "perdue", "perdait", "perd", "gagne", "gagner", "gagné",
    "marcher", "marche", "marchait", "marché", "courir", "court", "courait",
    "tomber", "tombe", "tombé", "tombait", "monter", "monte", "monté", "montait",
    "descendre", "descend", "descendu", "descendait", "passer", "passe", "passé", "passait",
    "commencer", "commence", "commencé", "commençait", "finir", "finit", "fini", "finissait",
    "continuer", "continue", "continué", "continuait", "arrêter", "arrête", "arrêté",
    "essayer", "essaie", "essayé", "essayait", "tenter", "tente", "tenté", "tentait",
    "réussir", "réussit", "réussi", "réussissait", "échouer", "échoue", "échoué",
    "changer", "change", "changé", "changeait", "garder", "garde", "gardé", "gardait",
    "lancer", "lancé", "lançait", "ouvrir", "ouvre", "ouvert", "ouvrait",
    "fermer", "ferme", "fermé", "fermait", "suivre", "suit", "suivi", "suivait",
    # Mots tronqués et fragments
    "quelqu", "lorsqu", "puisqu", "quoiqu", "jusqu", "aujourd",

    # Mots de temps
    "ans", "année", "années", "jour", "jours", "mois", "semaine", "semaines",
    "heure", "heures", "minute", "minutes", "seconde", "secondes", "moment", "moments",
    "temps", "fois", "date", "dates", "hier", "aujourd", "demain", "soir", "matin",
    "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche",
    "janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
    "septembre", "octobre", "novembre", "décembre", "2024", "2025", "2026",

    # Mots génériques divers
    "tête", "idée", "idées", "fin", "début", "face", "côté", "suis", "sera", "serait",
    "ceux", "celle", "celles", "celui", "autres", "autre", "même", "mêmes",
    "public", "publique", "publics", "publiques", "plutôt", "encore",
    "cours", "course", "investie", "investi", "officiellement", "officiel", "officielle",
    "chose", "choses", "cas", "façon", "manière", "genre", "type", "sorte",
    "part", "parts", "partie", "parties", "place", "places", "point", "points",
    "sens", "mot", "mots", "nom", "noms", "titre", "titres", "sujet", "sujets",
    "question", "questions", "réponse", "réponses", "problème", "problèmes",
    "raison", "raisons", "cause", "causes", "effet", "effets", "résultat", "résultats",
    "fond", "forme", "formes", "niveau", "niveaux", "ligne", "lignes",
    "homme", "hommes", "femme", "femmes", "personne", "personnes", "gens",
    "monde", "vie", "vies", "mort", "pays", "état", "états",
    "grand", "grande", "grands", "grandes", "petit", "petite", "petits", "petites",
    "bon", "bonne", "bons", "bonnes", "mauvais", "mauvaise", "meilleur", "meilleure",
    "vrai", "vraie", "vrais", "vraies", "faux", "fausse", "possible", "impossible",
    "seul", "seule", "seuls", "seules", "dernier", "dernière", "derniers", "dernières",
    "prochain", "prochaine", "prochains", "prochaines", "ancien", "ancienne", "anciens",
    "haut", "haute", "hauts", "hautes", "bas", "basse", "long", "longue",
    "plein", "pleine", "pleins", "pleines", "entier", "entière", "total", "totale",

    # Prénoms et noms communs
    "anne", "éric", "eric", "yves", "pierre", "jean", "marie", "michel", "jacques",
    "nicolas", "françois", "bruno", "gérald", "gerald", "olivier", "laurent",
    "rachida", "hidalgo", "darmanin", "attal", "zohra", "dati", "sarah", "knafo",
    "emmanuel", "grégoire", "ian", "brossat", "david", "belliard", "sophia", "chikirou",
    "thierry", "mariani", "bournazel", "macron", "mélenchon", "bardella", "lepen",
    "zemmour", "ciotti", "wauquiez", "retailleau", "philippe", "hollande", "sarkozy",

    # Faits divers / bruit / hors sujet
    "fille", "fils", "enfant", "enfants", "enlèvement", "tentative", "bayonne",
    "psg", "football", "match", "sport", "sports", "équipe", "joueur", "joueurs",
    "euro", "euros", "million", "millions", "milliard", "milliards", "nombre", "chiffre",
    "prix", "coût", "budget", "argent", "somme", "montant",

    # Mots de liaison et expressions
    "alors", "donc", "ainsi", "cependant", "toutefois", "néanmoins", "pourtant",
    "ailleurs", "davantage", "désormais", "dorénavant", "notamment", "surtout",
    "vraiment", "simplement", "seulement", "justement", "exactement", "absolument",
    "totalement", "complètement", "entièrement", "parfaitement", "clairement",
    "aujourd", "hui", "maintenant", "actuellement", "récemment", "bientôt",
    "toujours", "jamais", "souvent", "parfois", "rarement", "longtemps"
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

        # Étape 2: Extraire les mots (min 4 caractères pour éviter bruit)
        words = re.findall(r'\b[a-zA-ZàâäéèêëïîôùûüçœæÀÂÄÉÈÊËÏÎÔÙÛÜÇŒÆ]{4,}\b', title_clean.lower())

        # Étape 3: Lemmatiser et filtrer
        seen_in_article = set()  # Éviter de compter plusieurs fois le même lemme dans un article
        for word in words:
            lemma = lemmatize_word(word)

            # Ignorer mots trop courts après lemmatisation
            if len(lemma) < 4:
                continue

            # Ignorer stop words, nom du candidat et noms de médias
            if lemma in STOP_WORDS or lemma in name_parts or lemma in MEDIA_NAMES:
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

    # Compter les articles par domaine pour trouver le top média
    domain_counts = Counter(art["domain"] for art in unique if art["domain"])
    top_media = domain_counts.most_common(1)[0] if domain_counts else (None, 0)

    return {
        "articles": unique,
        "count": len(unique),
        "domains": len(domains),
        "raw_count": len(all_articles),
        "date_filtered_count": len(date_filtered),
        "top_media": top_media[0],
        "top_media_count": top_media[1],
        "media_breakdown": domain_counts.most_common(5)
    }


def _fetch_google_trends_api(keywords: List[str], timeframe: str) -> Dict:
    """Appelle l'API Google Trends (fonction interne)"""
    from pytrends.request import TrendReq
    import time
    import random

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
        pivot = keywords[0]
        pivot_score = None
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

                        if pivot_score is None and pivot in df.columns:
                            pivot_score = float(df[pivot].mean())

                        for kw in batch:
                            if kw in df.columns:
                                raw_score = float(df[kw].mean())
                                if pivot_score and pivot_score > 0:
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

    return {"scores": scores, "errors": errors}


@st.cache_data(ttl=3600, show_spinner=False)  # Cache Streamlit 1h
def get_google_trends(keywords: List[str], start_date: date, end_date: date) -> Dict:
    """
    Récupère les données Google Trends avec système intelligent de cache.

    Règles:
    - 24h: Refresh autorisé avec cooldown de 2h
    - 7j/14j/30j: Max 1 refresh par jour
    - Fallback: Toujours retourner les dernières données valides (jamais 0)
    """
    if not keywords:
        return {"success": False, "scores": {}, "errors": ["Aucun mot-clé fourni"], "from_cache": False}

    # Déterminer le type de période
    period_type = get_period_type(start_date, end_date)
    timeframe = f"{start_date.strftime('%Y-%m-%d')} {end_date.strftime('%Y-%m-%d')}"
    cache_key = f"{timeframe}_{','.join(sorted(keywords))}"

    # Charger le cache
    cache = load_trends_cache()
    cached_data = cache.get("data", {}).get(cache_key)
    cache_age = get_trends_cache_age_hours(cache_key)

    # Fonction helper pour retourner des données avec fallback (JAMAIS 0)
    def return_with_fallback(reason: str):
        # 1. Essayer le cache exact de cette période
        if cached_data and any(v > 0 for v in cached_data.get("scores", {}).values()):
            return {
                "success": True,
                "scores": cached_data.get("scores", {}),
                "errors": [reason] if reason else None,
                "from_cache": True,
                "cache_age_hours": round(cache_age, 1) if cache_age != float('inf') else None
            }

        # 2. Essayer le fallback last_valid pour ce type de période
        fallback = get_trends_last_valid(period_type, keywords)
        if fallback:
            return {
                "success": True,
                "scores": fallback["scores"],
                "errors": [f"{reason} (secours)"] if reason else None,
                "from_cache": True,
                "is_fallback": True
            }

        # 3. Dernier recours: chercher dans n'importe quel last_valid
        for pt in ["24h", "7d", "14d", "30d"]:
            fallback = get_trends_last_valid(pt, keywords)
            if fallback:
                return {
                    "success": True,
                    "scores": fallback["scores"],
                    "errors": [f"{reason} (données {pt})"] if reason else None,
                    "from_cache": True,
                    "is_fallback": True
                }

        # 4. Vraiment rien disponible
        return {
            "success": False,
            "scores": {kw: 0.0 for kw in keywords},
            "errors": [reason or "Aucune donnée disponible"],
            "from_cache": False,
            "quota_exhausted": True
        }

    # Vérifier si on peut faire un refresh selon les règles par période
    can_request, quota_message = can_refresh_trends(period_type)

    if not can_request:
        return return_with_fallback(quota_message)

    # Si le cache est très frais (< 30min), l'utiliser directement
    if cached_data and cache_age < 0.5 and any(v > 0 for v in cached_data.get("scores", {}).values()):
        return {
            "success": True,
            "scores": cached_data.get("scores", {}),
            "errors": None,
            "from_cache": True,
            "cache_age_hours": round(cache_age, 1)
        }

    # Faire la requête API
    try:
        result = _fetch_google_trends_api(keywords, timeframe)
        scores = result.get("scores", {})
        errors = result.get("errors", [])

        has_valid_data = any(v > 0 for v in scores.values())

        if has_valid_data:
            # Succès! Sauvegarder dans le cache ET dans last_valid
            cache = load_trends_cache()
            if "data" not in cache:
                cache["data"] = {}
            cache["data"][cache_key] = {"scores": scores, "timestamp": datetime.now().isoformat()}
            cache["last_refresh"] = datetime.now().isoformat()
            save_trends_cache(cache)

            # Sauvegarder comme dernière donnée valide
            save_trends_last_valid(period_type, scores, keywords)

            # Incrémenter le compteur de refresh
            increment_trends_period_refresh(period_type)

            return {
                "success": True,
                "scores": scores,
                "errors": errors if errors else None,
                "from_cache": False
            }
        else:
            # API a retourné 0 - utiliser fallback sans incrémenter
            return return_with_fallback("API sans données")

    except ImportError:
        return return_with_fallback("Module pytrends manquant")
    except Exception as e:
        error_str = str(e)[:100]
        if "429" in error_str:
            return return_with_fallback("Limite Google")
        return return_with_fallback(f"Erreur: {error_str}")


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


def _get_cached_channel_id(candidate_name: str) -> Optional[str]:
    """Récupère le channel ID depuis le cache (permanent)."""
    cache = load_youtube_cache()
    return cache.get("channel_ids", {}).get(candidate_name)


def _save_channel_id_to_cache(candidate_name: str, channel_id: str, channel_name: str = None):
    """Sauvegarde le channel ID dans le cache (permanent)."""
    cache = load_youtube_cache()
    if "channel_ids" not in cache:
        cache["channel_ids"] = {}
    cache["channel_ids"][candidate_name] = {
        "id": channel_id,
        "name": channel_name,
        "cached_at": datetime.now().isoformat()
    }
    save_youtube_cache(cache)


def _search_youtube_channel(candidate_name: str, api_key: str) -> tuple[Optional[str], Optional[str]]:
    """
    Recherche la chaîne YouTube officielle d'un candidat.
    Utilise le cache si disponible pour économiser le quota.
    Retourne (channel_id, channel_name) ou (None, None).
    """
    # === OPTIMISATION: Vérifier le cache d'abord ===
    cached = _get_cached_channel_id(candidate_name)
    if cached:
        return cached.get("id"), cached.get("name")

    # === Pas en cache: faire la recherche API ===
    search_url = "https://www.googleapis.com/youtube/v3/search"
    last_name = candidate_name.split()[-1]

    params = {
        "part": "snippet",
        "q": candidate_name,
        "type": "channel",
        "maxResults": 5,  # Réduit de 10 à 5 (suffisant)
        "key": api_key
    }

    try:
        response = requests.get(search_url, params=params, timeout=10)
        if response.status_code == 200:
            items = response.json().get("items", [])

            name_lower = candidate_name.lower()
            last_name_lower = last_name.lower()

            for item in items:
                channel_title = item.get("snippet", {}).get("channelTitle", "")
                channel_title_lower = channel_title.lower()
                channel_id = item.get("snippet", {}).get("channelId", "")

                # Match exact ou partiel sur le nom de la chaîne
                if name_lower in channel_title_lower or channel_title_lower in name_lower:
                    # Sauvegarder dans le cache pour les prochaines fois
                    _save_channel_id_to_cache(candidate_name, channel_id, channel_title)
                    return channel_id, channel_title

                # Match sur le nom de famille uniquement
                if last_name_lower in channel_title_lower and len(last_name_lower) >= 4:
                    _save_channel_id_to_cache(candidate_name, channel_id, channel_title)
                    return channel_id, channel_title

            # Aucune chaîne trouvée - sauvegarder "none" pour ne pas re-chercher
            _save_channel_id_to_cache(candidate_name, "", None)

    except Exception:
        pass

    return None, None


def _get_channel_videos(channel_id: str, api_key: str, start_date: date, end_date: date) -> List[Dict]:
    """
    Récupère toutes les vidéos récentes d'une chaîne YouTube.
    Pas de filtrage par nom - toutes les vidéos de la chaîne comptent.
    """
    search_url = "https://www.googleapis.com/youtube/v3/search"
    videos = []

    published_after = start_date.strftime("%Y-%m-%dT00:00:00Z")
    published_before = (end_date + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")

    params = {
        "part": "snippet",
        "channelId": channel_id,
        "type": "video",
        "order": "date",
        "maxResults": 50,
        "publishedAfter": published_after,
        "publishedBefore": published_before,
        "key": api_key
    }

    try:
        response = requests.get(search_url, params=params, timeout=15)
        if response.status_code == 200:
            for item in response.json().get("items", []):
                vid_id = item.get("id", {}).get("videoId", "")
                if vid_id:
                    videos.append({
                        "id": vid_id,
                        "title": item.get("snippet", {}).get("title", ""),
                        "channel": item.get("snippet", {}).get("channelTitle", ""),
                        "channel_id": channel_id,
                        "published": item.get("snippet", {}).get("publishedAt", "")[:10],
                        "source": "official_channel"
                    })
    except Exception:
        pass

    return videos


def _search_videos_mentioning(candidate_name: str, api_key: str, start_date: date, end_date: date, exclude_channel_id: str = None, skip_lastname_search: bool = False) -> List[Dict]:
    """
    Recherche les vidéos mentionnant un candidat sur d'autres chaînes.
    Utilise plusieurs stratégies de recherche pour maximiser la couverture.

    OPTIMISATION: Si skip_lastname_search=True, ne fait qu'une recherche avec le nom complet
    (économise 1 appel API quand la chaîne officielle a déjà beaucoup de vidéos).
    """
    search_url = "https://www.googleapis.com/youtube/v3/search"
    videos = []
    seen_ids = set()

    published_after = start_date.strftime("%Y-%m-%dT00:00:00Z")
    published_before = (end_date + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")

    # Stratégie 1: Recherche avec le nom complet
    # Stratégie 2: Recherche avec le nom de famille seul (sauf si skip_lastname_search)
    last_name = candidate_name.split()[-1]
    search_queries = [candidate_name]
    if len(last_name) >= 4 and not skip_lastname_search:
        search_queries.append(last_name)

    for query in search_queries:
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "order": "relevance",
            "maxResults": 30,
            "regionCode": "FR",
            "relevanceLanguage": "fr",
            "publishedAfter": published_after,
            "publishedBefore": published_before,
            "key": api_key
        }

        try:
            response = requests.get(search_url, params=params, timeout=15)
            if response.status_code == 200:
                for item in response.json().get("items", []):
                    vid_id = item.get("id", {}).get("videoId", "")
                    channel_id = item.get("snippet", {}).get("channelId", "")

                    # Skip si déjà vu ou si c'est la chaîne officielle (évite les doublons)
                    if not vid_id or vid_id in seen_ids:
                        continue
                    if exclude_channel_id and channel_id == exclude_channel_id:
                        continue

                    seen_ids.add(vid_id)
                    videos.append({
                        "id": vid_id,
                        "title": item.get("snippet", {}).get("title", ""),
                        "channel": item.get("snippet", {}).get("channelTitle", ""),
                        "channel_id": channel_id,
                        "published": item.get("snippet", {}).get("publishedAt", "")[:10],
                        "source": "search"
                    })
        except Exception:
            pass

    return videos


def _filter_relevant_videos(videos: List[Dict], candidate_name: str) -> List[Dict]:
    """
    Filtre les vidéos pour ne garder que celles vraiment pertinentes.
    Les vidéos de la chaîne officielle passent automatiquement.
    Les autres doivent mentionner le candidat dans le titre OU venir d'une chaîne média reconnue.
    """
    name_parts = [p.lower() for p in candidate_name.split() if len(p) >= 3]
    last_name = candidate_name.split()[-1].lower()

    # Médias connus (les vidéos de ces chaînes sont plus fiables)
    known_media_keywords = [
        "bfm", "cnews", "lci", "tf1", "france", "rmc", "europe1", "rtl",
        "figaro", "monde", "parisien", "obs", "express", "point", "marianne",
        "public sénat", "c dans l'air", "quotidien", "touche pas", "hanouna",
        "morandini", "praud", "zemmour", "ruquier", "ardisson", "bourdin",
        "pujadas", "calvi", "elkabbach", "aphatie", "joffrin", "onfray",
        "mediapart", "brut", "konbini", "hugodecrypte", "blast", "frontières",
        "livre noir", "thinkerview", "interdit", "femelliste", "front populaire"
    ]

    filtered = []
    for v in videos:
        # Les vidéos de la chaîne officielle passent toujours
        if v.get("source") == "official_channel":
            filtered.append(v)
            continue

        title_lower = v["title"].lower()
        channel_lower = v["channel"].lower()

        # Vérifier si le nom est dans le titre
        name_in_title = any(part in title_lower for part in name_parts)
        last_name_in_title = last_name in title_lower

        # Vérifier si c'est un média connu
        is_known_media = any(media in channel_lower for media in known_media_keywords)

        # Accepter si: nom dans le titre OU (nom de famille dans titre ET média connu)
        if name_in_title or (last_name_in_title and is_known_media):
            filtered.append(v)

    return filtered


def _get_video_stats(video_ids: List[str], api_key: str) -> Dict[str, Dict]:
    """Récupère les statistiques (vues, durée) pour une liste de vidéos."""
    if not video_ids:
        return {}

    stats_url = "https://www.googleapis.com/youtube/v3/videos"
    stats_map = {}

    # L'API accepte max 50 IDs à la fois
    for i in range(0, len(video_ids), 50):
        batch_ids = video_ids[i:i+50]
        params = {
            "part": "statistics,contentDetails",
            "id": ",".join(batch_ids),
            "key": api_key
        }

        try:
            response = requests.get(stats_url, params=params, timeout=10)
            if response.status_code == 200:
                for item in response.json().get("items", []):
                    vid_id = item.get("id")
                    stats_map[vid_id] = {
                        "views": int(item.get("statistics", {}).get("viewCount", 0)),
                        "duration": item.get("contentDetails", {}).get("duration", "")
                    }
        except Exception:
            pass

    return stats_map


@st.cache_data(ttl=1800, show_spinner=False)
def get_youtube_data(search_term: str, api_key: str, start_date: date, end_date: date) -> Dict:
    """
    Récupère les données YouTube via double stratégie OPTIMISÉE:
    1. Vidéos de la chaîne officielle (channel ID en cache permanent)
    2. Vidéos mentionnant le candidat (recherche adaptative)

    OPTIMISATIONS QUOTA:
    - Channel ID en cache permanent (0 appel après 1ère recherche)
    - Recherche nom famille uniquement si peu de résultats
    - Stats en batch unique
    """
    if not api_key or not api_key.strip():
        return {"available": False, "videos": [], "total_views": 0, "error": "Clé API manquante"}

    all_videos = []
    official_channel_id = None
    official_channel_name = None

    # === ÉTAPE 1: Chercher la chaîne officielle (CACHE PERMANENT) ===
    official_channel_id, official_channel_name = _search_youtube_channel(search_term, api_key)

    if official_channel_id:
        # Récupérer les vidéos de la chaîne officielle
        channel_videos = _get_channel_videos(official_channel_id, api_key, start_date, end_date)
        if channel_videos:
            if not official_channel_name:
                official_channel_name = channel_videos[0].get("channel", "")
            all_videos.extend(channel_videos)

    # === ÉTAPE 2: Chercher les vidéos mentionnant le candidat ===
    # OPTIMISATION: Si chaîne officielle a beaucoup de vidéos, on ne fait qu'une recherche
    skip_lastname_search = len(all_videos) >= 5

    search_videos = _search_videos_mentioning(
        search_term, api_key, start_date, end_date,
        exclude_channel_id=official_channel_id,
        skip_lastname_search=skip_lastname_search
    )

    # Filtrer les vidéos de recherche pour garder les pertinentes
    filtered_search_videos = _filter_relevant_videos(search_videos, search_term)
    all_videos.extend(filtered_search_videos)

    # === ÉTAPE 3: Dédupliquer par ID ===
    seen_ids = set()
    unique_videos = []
    for v in all_videos:
        if v["id"] not in seen_ids:
            seen_ids.add(v["id"])
            unique_videos.append(v)

    if not unique_videos:
        return {"available": False, "videos": [], "total_views": 0, "error": "Aucune vidéo trouvée"}

    # === ÉTAPE 4: Récupérer les statistiques (BATCH UNIQUE) ===
    video_ids = [v["id"] for v in unique_videos]
    stats_map = _get_video_stats(video_ids, api_key)

    total_views = 0
    final_videos = []

    for v in unique_videos:
        vid_stats = stats_map.get(v["id"], {})
        views = vid_stats.get("views", 0)
        duration = vid_stats.get("duration", "")

        final_videos.append({
            "id": v["id"],
            "title": v["title"],
            "channel": v["channel"],
            "published": v["published"],
            "url": f"https://www.youtube.com/watch?v={v['id']}",
            "views": views,
            "duration": duration,
            "is_short": _is_short(duration),
            "source": v.get("source", "search"),
            "is_official": v.get("source") == "official_channel"
        })
        total_views += views

    # Trier par vues décroissantes
    final_videos.sort(key=lambda x: x.get("views", 0), reverse=True)

    return {
        "available": True,
        "videos": final_videos,
        "total_views": total_views,
        "count": len(final_videos),
        "shorts_count": sum(1 for v in final_videos if v.get("is_short", False)),
        "long_count": sum(1 for v in final_videos if not v.get("is_short", False)),
        "official_channel": official_channel_name,
        "official_videos_count": sum(1 for v in final_videos if v.get("is_official", False)),
        "other_videos_count": sum(1 for v in final_videos if not v.get("is_official", False))
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
                    period_days: int = 7, all_candidates_press: List[int] = None,
                    all_candidates_wiki: List[int] = None, all_candidates_youtube: List[int] = None) -> Dict:
    """Calcule le score de visibilité
    Pondération: Presse 30%, Trends 30%, Wikipedia 25%, YouTube 15%

    Tous les scores sont RELATIFS aux autres candidats pour garantir une différenciation.
    """

    # Score Wikipedia RELATIF : basé sur le max des candidats
    if all_candidates_wiki and max(all_candidates_wiki) > 0:
        max_wiki = max(all_candidates_wiki)
        wiki_score = (wiki_views / max_wiki) * 100
    else:
        # Fallback logarithmique si pas de données comparatives
        wiki_score = min((math.log10(wiki_views) / 5) * 100, 100) if wiki_views > 0 else 0

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
        press_score = 0

    # Trends est déjà relatif (Google Trends compare les termes entre eux)
    trends_norm = min(max(trends_score, 0), 100)

    # Score YouTube RELATIF : basé sur le max des candidats
    yt_score = 0
    if youtube_available and youtube_views > 0:
        if all_candidates_youtube and max(all_candidates_youtube) > 0:
            max_yt = max(all_candidates_youtube)
            yt_score = (youtube_views / max_yt) * 100
        else:
            # Fallback logarithmique si pas de données comparatives
            yt_score = min((math.log10(youtube_views) / 6) * 100, 100)

    total = trends_norm * 0.30 + press_score * 0.30 + wiki_score * 0.25 + yt_score * 0.15
    total = min(max(total, 0), 100)

    return {
        "total": round(total, 1),
        "trends": round(trends_norm, 1),
        "press": round(press_score, 1),
        "wiki": round(wiki_score, 1),
        "youtube": round(yt_score, 1),
        "contrib_trends": round(trends_norm * 0.30, 1),
        "contrib_press": round(press_score * 0.30, 1),
        "contrib_wiki": round(wiki_score * 0.25, 1),
        "contrib_youtube": round(yt_score * 0.15, 1),
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

    # Détecter si quota Trends épuisé
    trends_quota_exhausted = False
    if not trends.get("success", True):
        err = trends.get("error") or trends.get("errors")
        if err:
            err_str = str(err) if not isinstance(err, str) else err
            trends_quota_exhausted = trends.get("quota_exhausted") or "429" in err_str

    progress.progress(0.1)

    # Déterminer le type de période pour les règles de cache
    period_type = get_period_type(start_date, end_date)
    expected_youtube_cost = len(candidate_ids) * YOUTUBE_COST_PER_CANDIDATE if youtube_key else 0

    if youtube_key:
        # Vérifier si on peut rafraîchir YouTube selon les règles par période
        youtube_refresh_allowed, youtube_refresh_reason = can_refresh_youtube_for_period(
            period_type=period_type,
            expected_cost=expected_youtube_cost
        )
        if youtube_refresh_allowed:
            youtube_mode = "api"
        else:
            youtube_mode = "cache"
    else:
        youtube_refresh_allowed = False
        youtube_refresh_reason = "Clé API YouTube manquante"
        youtube_mode = "disabled"

    youtube_api_called = False
    total = len(candidate_ids)

    for i, cid in enumerate(candidate_ids):
        c = CANDIDATES[cid]
        name = c["name"]

        status.text(f"Analyse de {name} ({i+1}/{total})...")

        wiki = get_wikipedia_views(c["wikipedia"], start_date, end_date)
        press = get_all_press_coverage(name, c["search_terms"], start_date, end_date)
        tv_radio = get_tv_radio_mentions(name, start_date, end_date)

        # YouTube: utiliser la période sélectionnée
        yt_start = start_date
        yt_end = end_date

        if youtube_mode == "api":
            status.text(f"Analyse YouTube de {name}...")
            youtube = get_youtube_data(name, youtube_key, yt_start, yt_end)
            # Sauvegarder si données valides (le cache gère automatiquement last_valid)
            if youtube.get("total_views", 0) > 0 and not youtube.get("error"):
                set_cached_youtube_data(name, youtube, yt_start, yt_end)
            youtube_api_called = True
        elif youtube_mode == "cache":
            # Utiliser le cache avec fallback automatique (JAMAIS 0)
            cached = get_cached_youtube_data_for_period(name, yt_start, yt_end)
            if cached and cached.get("total_views", 0) > 0:
                youtube = dict(cached)
                youtube["from_cache"] = True
            else:
                # Aucun cache disponible
                youtube = {"available": False, "total_views": 0, "videos": [], "from_cache": True, "no_cache": True}
        else:
            youtube = {"available": False, "total_views": 0, "videos": [], "disabled": True}

        trends_score = trends.get("scores", {}).get(name, 0)

        # Mots-clés extraits des articles de presse
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
            "keywords": keywords
        }

        progress.progress((i + 1) / total)

    # === CALCUL DES SCORES (après collecte de tous les candidats) ===
    # Collecter tous les comptages pour calcul relatif
    all_press_counts = [results[cid]["press"]["count"] for cid in candidate_ids]
    all_wiki_views = [results[cid]["wikipedia"]["views"] for cid in candidate_ids]
    all_youtube_views = [results[cid]["youtube"].get("total_views", 0) for cid in candidate_ids]
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
            all_candidates_press=all_press_counts,
            all_candidates_wiki=all_wiki_views,
            all_candidates_youtube=all_youtube_views
        )
        results[cid]["score"] = score

    if youtube_api_called and expected_youtube_cost > 0:
        increment_youtube_period_refresh(period_type=period_type, cost=expected_youtube_cost)

    progress.empty()
    status.empty()

    # Détecter si YouTube quota épuisé (données à 0 pour tous)
    youtube_quota_exhausted = False
    if youtube_mode != "disabled":
        all_yt_zero = all(
            results[cid]["youtube"].get("total_views", 0) == 0
            for cid in candidate_ids
        )
        any_yt_error = any(
            results[cid]["youtube"].get("error") and "quota" in str(results[cid]["youtube"].get("error", "")).lower()
            for cid in candidate_ids
        )
        youtube_quota_exhausted = all_yt_zero and (any_yt_error or get_youtube_quota_remaining() == 0)

    return {
        "candidates": results,
        "youtube": {
            "mode": youtube_mode,
            "cache_age_hours": get_youtube_cache_age_hours(),
            "quota_remaining": get_youtube_quota_remaining(),
            "refresh_reason": youtube_refresh_reason if youtube_mode == "cache" else None,
            "cost": expected_youtube_cost,
            "quota_exhausted": youtube_quota_exhausted
        },
        "trends": {
            "quota_exhausted": trends_quota_exhausted
        }
    }


# =============================================================================
# INTERFACE PRINCIPALE
# =============================================================================

def main():
    # Viewport meta pour iPhone + CSS responsive
    mobile_css = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] {height: 48px; min-height: 48px; visibility: visible; padding: 4px 0; background: transparent;}
    [data-testid="collapsedControl"] {width: 60px !important; height: 60px !important;}
    [data-testid="collapsedControl"] svg {width: 30px !important; height: 30px !important;}
    .js-plotly-plot, .plotly, [data-testid="stPlotlyChart"] {touch-action: pan-y !important; -webkit-user-select: none !important; user-select: none !important;}
    .js-plotly-plot .draglayer, .js-plotly-plot .dragcover {pointer-events: none !important;}
    @media screen and (max-width: 768px) {
        h1 {font-size: 1.5rem !important; line-height: 1.2 !important;}
        h2 {font-size: 1.2rem !important;}
        h3 {font-size: 1rem !important;}
        .main .block-container {padding: 1rem 0.5rem !important;}
        [data-testid="column"] {width: 100% !important; flex: 100% !important; min-width: 100% !important;}
        [data-testid="stMetric"] {padding: 0.5rem !important;}
        [data-testid="stMetricValue"] {font-size: 1.2rem !important;}
        [data-testid="stMetricLabel"] {font-size: 0.7rem !important;}
        [data-testid="stDataFrame"] {font-size: 0.8rem !important;}
        .stTabs [data-baseweb="tab-list"] {gap: 0 !important; flex-wrap: nowrap !important; overflow-x: auto !important;}
        .stTabs [data-baseweb="tab"] {padding: 0.3rem 0.5rem !important; font-size: 0.75rem !important; white-space: nowrap !important;}
        [data-testid="stExpander"] {margin-bottom: 0.5rem !important;}
        [data-testid="stPlotlyChart"] {width: 100% !important; touch-action: pan-y !important;}
        [data-testid="stSidebar"] {min-width: 220px !important; width: 220px !important;}
        .stButton > button {min-height: 48px !important; font-size: 0.9rem !important;}
        [data-testid="stMultiSelect"], [data-testid="stSelectbox"] {min-height: 48px !important;}
        [data-testid="stDataFrame"] > div {overflow-x: auto !important; -webkit-overflow-scrolling: touch !important;}
    }
    @media screen and (max-width: 380px) {
        h1 {font-size: 1.2rem !important;}
        .stTabs [data-baseweb="tab"] {padding: 0.2rem 0.3rem !important; font-size: 0.65rem !important;}
    }
    </style>
    """
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
            period_label = st.selectbox("Durée", list(period_options.keys()), index=2)  # 14 jours par défaut
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
        st.caption("Presse 30% · Trends 30% · Wikipedia 25% · YouTube 15%")

        st.markdown("---")
        st.caption("Kléothime Bourdon · bourdonkleothime@gmail.com")

    if not selected:
        st.warning("Veuillez sélectionner au moins un candidat")
        return

    result = collect_data(selected, start_date, end_date, YOUTUBE_API_KEY)
    data = result["candidates"]
    sorted_data = sorted(data.items(), key=lambda x: x[1]["score"]["total"], reverse=True)

    # === SAUVEGARDE AUTOMATIQUE HISTORIQUE (fiable, tous les 3-4 jours) ===
    history = load_history()

    # 1. Vérifier l'intervalle minimum (3 jours depuis la dernière entrée)
    min_interval_days = 3
    last_entry_date = None
    if history:
        last_entry_date = max(h.get("date") for h in history)
        days_since_last = (end_date - datetime.strptime(last_entry_date, "%Y-%m-%d").date()).days
        interval_ok = days_since_last >= min_interval_days
    else:
        interval_ok = True  # Pas d'historique = première entrée OK

    # 2. Vérifier que TOUTES les données sont complètes (pas de quotas épuisés)
    trends_ok = not result.get("trends", {}).get("quota_exhausted", False)
    youtube_ok = not result.get("youtube", {}).get("quota_exhausted", False)

    # 3. Vérifier les données réelles pour TOUS les candidats
    all_wiki_ok = all(d["wikipedia"]["views"] > 0 for _, d in sorted_data)
    # Trends: au moins 1 candidat avec score > 0 (certains peuvent légitimement être à 0)
    any_trends_ok = any(d["trends_score"] > 0 for _, d in sorted_data)
    # YouTube: au moins 1 candidat avec vues > 0
    any_youtube_ok = any(d["youtube"].get("total_views", 0) > 0 for _, d in sorted_data)

    # 4. Toutes les conditions doivent être réunies
    data_complete = all([
        trends_ok,           # Pas de quota Trends épuisé
        youtube_ok,          # Pas de quota YouTube épuisé
        all_wiki_ok,         # Wikipedia OK pour tous
        any_trends_ok,       # Au moins 1 candidat avec Trends
        any_youtube_ok,      # Au moins 1 candidat avec YouTube
    ])

    # Sauvegarder seulement si intervalle OK ET données complètes
    if interval_ok and data_complete:
        period_label = f"{start_date} à {end_date}"
        add_to_history(data, period_label, end_date)

    # === CLASSEMENT ===
    st.markdown("---")
    st.markdown("## Classement général")

    rows = []
    for rank, (cid, d) in enumerate(sorted_data, 1):
        # Mots-clés extraits des articles de presse
        top_keywords = d.get('keywords', [])[:3]
        themes_str = ' · '.join([word for word, count, arts in top_keywords]) if top_keywords else '-'

        # Top média
        top_media = d['press'].get('top_media', '-')
        top_media_count = d['press'].get('top_media_count', 0)
        top_media_str = f"{top_media} ({top_media_count})" if top_media else '-'

        trends_val = d['trends_score']
        yt_views = d['youtube'].get('total_views', 0)

        row = {
            'Rang': rank,
            'Candidat': d['info']['name'],
            'Parti': d['info']['party'],
            'Score': round(d['score']['total'], 1),
            'Thèmes': themes_str,
            'Top Média': top_media_str,
            'Articles': d['press']['count'],
            'Trends': f"{trends_val:.1f}" if trends_val > 0 else "-",
            'Wikipedia': format_number(d['wikipedia']['views']),
            'Vues YT': format_number(yt_views) if yt_views > 0 else "-",
        }
        rows.append(row)

    df = pd.DataFrame(rows)

    # Styler pour mettre Sarah Knafo en gras
    def highlight_knafo(row):
        if row['Candidat'] == 'Sarah Knafo':
            return ['font-weight: bold; background-color: rgba(30, 58, 95, 0.15)'] * len(row)
        return [''] * len(row)

    styled_df = df.style.apply(highlight_knafo, axis=1).format({
        'Score': '{:.1f}'
    })

    st.dataframe(styled_df, hide_index=True, use_container_width=True)

    # Message quota si données à 0 et quota épuisé
    all_trends_zero = all(d['trends_score'] == 0 for _, d in sorted_data)
    all_yt_zero = all(d['youtube'].get('total_views', 0) == 0 for _, d in sorted_data)
    trends_quota = result.get("trends", {}).get("quota_exhausted", False)
    yt_quota = result.get("youtube", {}).get("quota_exhausted", False)

    quota_messages = []
    if all_trends_zero and trends_quota:
        quota_messages.append("Google Trends")
    if all_yt_zero and yt_quota:
        quota_messages.append("YouTube")

    if quota_messages:
        wait_time = get_time_until_quota_reset()
        sources_str = " et ".join(quota_messages)
        st.warning(f"⏳ {sources_str} : quota épuisé. Données disponibles dans {wait_time}")

    # Metriques
    leader = sorted_data[0][1]
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric('Leader', leader['info']['name'])
    with col2:
        st.metric('Score du leader', f"{leader['score']['total']:.1f} / 100")
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
    # Noms avec Sarah Knafo en gras (HTML pour Plotly)
    names_html = [f"<b>{n}</b>" if n == "Sarah Knafo" else n for n in names]

    # Config Plotly pour mobile (graphiques statiques = pas de capture du scroll)
    plotly_config = {
        'displayModeBar': False,  # Cache la barre d'outils
        'staticPlot': False,      # Permet le hover
        'scrollZoom': False,      # Désactive zoom molette
        'doubleClick': False,     # Désactive double-clic
        'responsive': True,
        'dragmode': False,        # Désactive drag/selection
    }

    # TAB 1: SCORES
    with tab1:
        col1, col2 = st.columns(2)

        with col1:
            scores = [d['score']['total'] for _, d in sorted_data]
            fig = px.bar(x=names_html, y=scores, color=names, color_discrete_sequence=colors,
                        title='Score de visibilite')
            fig.update_layout(
                showlegend=False,
                yaxis=dict(range=[0, 100], title='Score', fixedrange=True),
                xaxis=dict(title='', tickangle=-45, fixedrange=True),
                margin=dict(b=100),
                dragmode=False,
            )
            fig.update_traces(
                hovertemplate='<b>%{x}</b><br>Score: %{y:.1f}<extra></extra>'
            )
            st.plotly_chart(fig, use_container_width=True, config=plotly_config)

        with col2:
            decomp_data = []
            for _, d in sorted_data:
                s = d['score']
                name = d['info']['name']
                name_display = f"<b>{name}</b>" if name == "Sarah Knafo" else name
                decomp_data.append({
                    'Candidat': name_display,
                    'Presse (30%)': s['contrib_press'],
                    'Trends (30%)': s['contrib_trends'],
                    'Wikipedia (25%)': s['contrib_wiki'],
                    'YouTube (15%)': s['contrib_youtube'],
                })

            df_decomp = pd.DataFrame(decomp_data)
            fig = px.bar(df_decomp, x='Candidat',
                        y=['Presse (30%)', 'Trends (30%)', 'Wikipedia (25%)', 'YouTube (15%)'],
                        barmode='stack', title='Decomposition du score',
                        color_discrete_map={
                            'Presse (30%)': '#2563eb',
                            'Trends (30%)': '#16a34a',
                            'Wikipedia (25%)': '#eab308',
                            'YouTube (15%)': '#dc2626'
                        })
            fig.update_layout(
                yaxis=dict(range=[0, 100], title='Points', fixedrange=True),
                xaxis=dict(title='', tickangle=-45, fixedrange=True),
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
        st.markdown('### Thèmes dans la presse')
        st.markdown('*Mots-clés extraits des articles de presse pour chaque candidat*')

        for rank, (cid, d) in enumerate(sorted_data, 1):
            keywords = d.get('keywords', [])
            name = d['info']['name']
            # Sarah Knafo en gras dans le titre
            expander_title = f'{rank}. **{name}**' if name == "Sarah Knafo" else f'{rank}. {name}'
            is_knafo = name == "Sarah Knafo"

            with st.expander(expander_title, expanded=(rank <= 3 or is_knafo)):
                if keywords:
                    for word, count, articles in keywords:
                        st.markdown(f"**{word}** ({count} mentions)")
                        if articles:
                            for art in articles[:5]:
                                st.caption(f"- [{art.get('title', 'Sans titre')}]({art.get('url', '#')}) - {art.get('domain', '')}")
                else:
                    st.info('Aucun thème détecté')

        # === TABLEAU RECAPITULATIF ===
        st.markdown('---')
        st.markdown('### Tableau récapitulatif')

        recap_data = []
        for _, d in sorted_data:
            keywords = d.get('keywords', [])[:3]
            top_3 = [word for word, count, _ in keywords]

            recap_data.append({
                'Candidat': d['info']['name'],
                'Thème 1': top_3[0] if len(top_3) > 0 else '-',
                'Thème 2': top_3[1] if len(top_3) > 1 else '-',
                'Thème 3': top_3[2] if len(top_3) > 2 else '-',
            })

        df_recap = pd.DataFrame(recap_data)
        # Styler pour Sarah Knafo en gras
        def highlight_knafo_recap(row):
            if row['Candidat'] == 'Sarah Knafo':
                return ['font-weight: bold; background-color: rgba(30, 58, 95, 0.15)'] * len(row)
            return [''] * len(row)
        st.dataframe(df_recap.style.apply(highlight_knafo_recap, axis=1), use_container_width=True, hide_index=True)
    # TAB 3: SONDAGES
    with tab3:
        st.markdown("### Sondages d'intentions de vote")

        # Recharger les sondages
        sondages_actuels = load_sondages()

        if sondages_actuels:
            # === DERNIER SONDAGE (le plus recent) ===
            latest_sondage = sondages_actuels[0]  # Deja trie par date decroissante

            st.markdown(f"#### Dernier sondage : {latest_sondage['institut']} ({latest_sondage['date']})")
            st.caption(f"Commanditaire: {latest_sondage.get('commanditaire', 'N/A')} · Echantillon: {latest_sondage.get('echantillon', 'N/A')} personnes")

            # Preparer les donnees du dernier sondage
            latest_data = []
            for candidat, score in latest_sondage["scores"].items():
                latest_data.append({
                    "Candidat": candidat,
                    "Intentions": score
                })

            latest_data.sort(key=lambda x: x["Intentions"], reverse=True)
            color_map = {c["name"]: c["color"] for c in CANDIDATES.values()}

            # Graphique du dernier sondage
            fig_latest = go.Figure()
            for item in latest_data:
                candidat = item["Candidat"]
                color = color_map.get(candidat, "#888")
                # Sarah Knafo en gras sur l'axe X
                x_label = f"<b>{candidat}</b>" if candidat == "Sarah Knafo" else candidat
                fig_latest.add_trace(go.Bar(
                    name=candidat,
                    x=[x_label],
                    y=[item["Intentions"]],
                    marker_color=color,
                    text=[f"{item['Intentions']}%"],
                    textposition='outside',
                    hovertemplate=f'<b>{candidat}</b><br>{item["Intentions"]}%<extra></extra>'
                ))

            fig_latest.update_layout(
                title=f"Intentions de vote - {latest_sondage['institut']} ({latest_sondage['date']})",
                showlegend=False,
                yaxis=dict(title="Intentions de vote (%)", range=[0, max(item["Intentions"] for item in latest_data) + 10], fixedrange=True),
                xaxis=dict(title="", fixedrange=True),
                dragmode=False
            )
            st.plotly_chart(fig_latest, use_container_width=True, config=plotly_config)

            # Tableau du dernier sondage avec Sarah Knafo en gras
            df_latest = pd.DataFrame(latest_data)
            def highlight_knafo_sondage(row):
                if row['Candidat'] == 'Sarah Knafo':
                    return ['font-weight: bold; background-color: rgba(30, 58, 95, 0.15)'] * len(row)
                return [''] * len(row)
            st.dataframe(
                df_latest.style.apply(highlight_knafo_sondage, axis=1),
                use_container_width=True,
                hide_index=True
            )

            if latest_sondage.get("source_url"):
                st.markdown(f"[Source: {latest_sondage['institut']}]({latest_sondage['source_url']})")

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
                yaxis=dict(range=[0, 45], title="Intentions de vote (%)", fixedrange=True),
                xaxis=dict(title="", fixedrange=True),
                legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5),
                height=500,
                margin=dict(b=100),
                dragmode=False
            )
            fig_evolution.update_traces(
                hovertemplate='<b>%{fullData.name}</b><br>%{x}<br>%{y}%<extra></extra>'
            )
            st.plotly_chart(fig_evolution, use_container_width=True, config=plotly_config)

            st.markdown("---")

            # === DETAIL PAR SONDAGE ===
            st.markdown("#### Detail par sondage")

            for sondage in sorted(sondages_actuels, key=lambda x: x["date"], reverse=True):
                with st.expander(f"{sondage['institut']} - {sondage['date']} - {sondage['hypothese'][:50]}...", expanded=(sondage == sondages_actuels[0])):
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
                            yaxis=dict(title="%", range=[0, 40], fixedrange=True),
                            xaxis=dict(title="", fixedrange=True),
                            height=300,
                            margin=dict(t=10),
                            dragmode=False
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
            name = d["info"]["name"]

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

            # Sarah Knafo en gras dans le HTML
            candidat_html = f"<b>{name}</b>" if name == "Sarah Knafo" else name
            tv_data.append({
                "Candidat": candidat_html,
                "Mentions": tv.get("count", 0),
                "Top médias": top_media_html if top_media_html else "-"
            })

        st.markdown(pd.DataFrame(tv_data).to_html(escape=False, index=False), unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### Détails des mentions")

        for cid, d in sorted_data:
            tv = d.get("tv_radio", {})
            mentions = tv.get("mentions", [])
            name = d["info"]["name"]

            if mentions:
                # Sarah Knafo en gras dans le titre de l'expander
                expander_title = f"**{name}** - {len(mentions)} mention(s)" if name == "Sarah Knafo" else f"{name} - {len(mentions)} mention(s)"
                with st.expander(expander_title):
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
                yaxis=dict(title="Mentions", fixedrange=True),
                xaxis=dict(title="", fixedrange=True),
                dragmode=False
            )
            fig.update_traces(
                hovertemplate='<b>%{x}</b><br>%{y} mentions<extra></extra>'
            )
            st.plotly_chart(fig, use_container_width=True, config=plotly_config)

    # TAB 5: HISTORIQUE
    with tab5:
        st.markdown("### Évolution des scores de visibilité")
        # st.caption("Sauvegarde auto tous les 3+ jours, uniquement si toutes les données sont complètes")

        # Charger l'historique existant
        history = load_history()

        # Debug: afficher les dates chargées (masqué)
        # if history:
        #     dates_loaded = sorted([h.get("date") for h in history])
        #     st.caption(f"📊 Données chargées: {dates_loaded}")

        if history and len(history) >= 1:
            # Dédupliquer par semaine (garder 1 entrée par semaine ISO)
            from datetime import datetime as dt
            week_entries = {}
            for entry in history:
                entry_date = dt.strptime(entry["date"], "%Y-%m-%d")
                week_key = entry_date.isocalendar()[:2]  # (year, week)
                if week_key not in week_entries or entry["date"] > week_entries[week_key]["date"]:
                    week_entries[week_key] = entry
            history = list(week_entries.values())

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

                # D'abord ajouter tous les concurrents (couleurs originales des candidats)
                for candidate_name in color_map.keys():
                    if candidate_name == "Sarah Knafo":
                        continue  # On l'ajoute après pour qu'elle soit au premier plan

                    candidate_data = df_hist[df_hist["Candidat"] == candidate_name]
                    if not candidate_data.empty:
                        color = color_map.get(candidate_name, "#888888")
                        fig.add_trace(go.Scatter(
                            x=candidate_data["Date"],
                            y=candidate_data["Score"],
                            name=candidate_name,
                            mode='lines+markers',
                            line=dict(color=color, width=2),
                            marker=dict(symbol='circle', size=6, color=color),
                            opacity=0.7,
                            hovertemplate='<b>%{fullData.name}</b><br>Date: %{x}<br>Score: %{y:.1f}<extra></extra>'
                        ))

                # Sarah Knafo : trait ÉPAIS, rouge vif, diamants
                knafo_data = df_hist[df_hist["Candidat"] == "Sarah Knafo"]
                if not knafo_data.empty:
                    fig.add_trace(go.Scatter(
                        x=knafo_data["Date"],
                        y=knafo_data["Score"],
                        name="Sarah Knafo",
                        mode='lines+markers',
                        line=dict(color="#E63946", width=6),  # ÉPAIS
                        marker=dict(symbol='diamond', size=14, color="#E63946", line=dict(color='white', width=2)),
                        hovertemplate='<b>Sarah Knafo</b><br>Date: %{x}<br>Score: %{y:.1f}<extra></extra>'
                    ))

                fig.update_layout(
                    title="Évolution temporelle",
                    yaxis=dict(range=[0, 100], title="Score", fixedrange=True),
                    xaxis=dict(title="", fixedrange=True),
                    dragmode=False,
                    legend=dict(
                        orientation="v",
                        yanchor="top",
                        y=1,
                        xanchor="left",
                        x=1.02,
                        font=dict(size=10),
                        itemsizing="constant"
                    ),
                    height=400,
                    margin=dict(l=40, r=120, t=40, b=40)
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
            st.warning("Wikipedia requiert une période de 48h minimum. Les données affichées sont incomplètes.")

        col1, col2 = st.columns(2)

        with col1:
            wiki_views = [d["wikipedia"]["views"] for _, d in sorted_data]
            fig = px.bar(
                x=names_html,
                y=wiki_views,
                color=names,
                color_discrete_sequence=colors,
                title="Vues Wikipedia"
            )
            fig.update_layout(
                showlegend=False,
                yaxis=dict(title="Vues", fixedrange=True),
                xaxis=dict(title="", fixedrange=True),
                dragmode=False
            )
            fig.update_traces(
                hovertemplate='<b>%{x}</b><br>%{y} vues<extra></extra>'
            )
            st.plotly_chart(fig, use_container_width=True, config=plotly_config)

        with col2:
            variations = [max(min(d["wikipedia"]["variation"], 100), -100) for _, d in sorted_data]
            fig = px.bar(
                x=names_html,
                y=variations,
                color=variations,
                color_continuous_scale=["#dc2626", "#6b7280", "#16a34a"],
                range_color=[-100, 100],
                title=f"Variation vs {days_in_period} jours précédents"
            )
            fig.update_layout(
                yaxis=dict(range=[-100, 100], title="Variation (%)", fixedrange=True),
                xaxis=dict(title="", fixedrange=True),
                dragmode=False
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
                x=names_html,
                y=articles,
                color=names,
                color_discrete_sequence=colors,
                title="Nombre d'articles de presse"
            )
            fig.update_layout(
                showlegend=False,
                yaxis=dict(title="Articles", fixedrange=True),
                xaxis=dict(title="", fixedrange=True),
                dragmode=False
            )
            fig.update_traces(
                hovertemplate='<b>%{x}</b><br>%{y} articles<extra></extra>'
            )
            st.plotly_chart(fig, use_container_width=True, config=plotly_config)

        with col2:
            fig = px.pie(
                names=names_html,
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
        name = d['info']['name']
        expander_title = f"{rank}. **{name}** — {len(arts)} article(s)" if name == "Sarah Knafo" else f"{rank}. {name} — {len(arts)} article(s)"
        with st.expander(expander_title):
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
            name = d['info']['name']
            if yt.get("available") and yt.get("videos"):
                expander_title = f"{rank}. **{name}** — {format_number(yt['total_views'])} vues" if name == "Sarah Knafo" else f"{rank}. {name} — {format_number(yt['total_views'])} vues"
                with st.expander(expander_title):
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

