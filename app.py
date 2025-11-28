"""
Visibility Index - Application Web Interactive
Tableau de bord de visibilité pour les municipales Paris 2026
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
    
    .metric-card h2 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: bold;
    }
    
    .metric-card p {
        margin: 5px 0 0 0;
        opacity: 0.9;
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
    
    /* Sidebar */
    .css-1d391kg {
        background-color: #f8f9fa;
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 10px 20px;
    }
    
    /* Positive/Negative indicators */
    .positive { color: #10b981; font-weight: bold; }
    .negative { color: #ef4444; font-weight: bold; }
    
    /* Hide Streamlit branding */
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
        "color": "#0066CC",
        "wikipedia": "Rachida_Dati",
        "search_terms": ["Rachida Dati"],
        "emoji": "👩‍⚖️"
    },
    "pierre_yves_bournazel": {
        "name": "Pierre-Yves Bournazel",
        "party": "Horizons",
        "color": "#FF6B35",
        "wikipedia": "Pierre-Yves_Bournazel",
        "search_terms": ["Pierre-Yves Bournazel"],
        "emoji": "👨‍💼"
    },
    "emmanuel_gregoire": {
        "name": "Emmanuel Grégoire",
        "party": "PS",
        "color": "#FF69B4",
        "wikipedia": "Emmanuel_Grégoire",
        "search_terms": ["Emmanuel Grégoire"],
        "emoji": "👨‍💼"
    },
    "david_belliard": {
        "name": "David Belliard",
        "party": "EELV",
        "color": "#00A86B",
        "wikipedia": "David_Belliard",
        "search_terms": ["David Belliard"],
        "emoji": "🌿"
    },
    "sophia_chikirou": {
        "name": "Sophia Chikirou",
        "party": "LFI",
        "color": "#C9462C",
        "wikipedia": "Sophia_Chikirou",
        "search_terms": ["Sophia Chikirou"],
        "emoji": "👩‍💼"
    },
    "thierry_mariani": {
        "name": "Thierry Mariani",
        "party": "RN",
        "color": "#0D2C54",
        "wikipedia": "Thierry_Mariani",
        "search_terms": ["Thierry Mariani"],
        "emoji": "👨‍💼"
    }
}

# =============================================================================
# FONCTIONS DE COLLECTE DE DONNÉES
# =============================================================================

@st.cache_data(ttl=3600, show_spinner=False)
def get_wikipedia_pageviews(page_title: str, start_date: date, end_date: date) -> dict:
    """
    Récupère les pageviews Wikipedia via l'API Wikimedia.
    API fiable et gratuite.
    """
    try:
        # Format dates pour l'API
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")
        
        url = (
            f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
            f"fr.wikipedia/all-access/user/{page_title}/daily/{start_str}/{end_str}"
        )
        
        headers = {"User-Agent": "VisibilityIndex/2.0 (contact@example.com)"}
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            
            # Construire le timeseries
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
        st.warning(f"Erreur Wikipedia pour {page_title}: {e}")
        return {"total_views": 0, "daily_avg": 0, "timeseries": {}, "success": False}


@st.cache_data(ttl=3600, show_spinner=False)
def get_gdelt_articles(search_term: str, start_date: date, end_date: date) -> dict:
    """
    Récupère les articles de presse via GDELT API.
    """
    try:
        # Format dates pour GDELT
        start_str = start_date.strftime("%Y%m%d%H%M%S")
        end_str = (datetime.combine(end_date, datetime.max.time())).strftime("%Y%m%d%H%M%S")
        
        # Construire la requête - plus simple et plus fiable
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
                
                # Dédupliquer par titre
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
                    "articles": unique_articles[:20],  # Top 20 pour affichage
                    "success": True
                }
            except json.JSONDecodeError:
                # GDELT retourne parfois une réponse vide
                return {"article_count": 0, "domain_count": 0, "articles": [], "success": True}
        else:
            return {"article_count": 0, "domain_count": 0, "articles": [], "success": False}
            
    except Exception as e:
        return {"article_count": 0, "domain_count": 0, "articles": [], "success": False}


@st.cache_data(ttl=7200, show_spinner=False)
def get_google_trends_data(keywords: list, geo: str = "FR") -> dict:
    """
    Récupère les données Google Trends via pytrends.
    Note: Cette API est instable, on gère les erreurs gracieusement.
    """
    try:
        from pytrends.request import TrendReq
        
        pytrends = TrendReq(hl='fr-FR', tz=60, timeout=(10, 25))
        
        # Construire le payload
        pytrends.build_payload(
            kw_list=keywords[:5],  # Max 5 keywords
            cat=0,
            timeframe='today 3-m',
            geo=geo,
            gprop=''
        )
        
        # Récupérer les données
        df = pytrends.interest_over_time()
        
        if df.empty:
            return {"success": False, "data": {}}
        
        # Supprimer la colonne isPartial si présente
        if 'isPartial' in df.columns:
            df = df.drop(columns=['isPartial'])
        
        # Convertir en dict
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


def calculate_visibility_score(wiki_views: int, press_articles: int, trends_score: float) -> float:
    """
    Calcule un score de visibilité composite (0-100).
    
    Pondérations:
    - Wikipedia: 40% (proxy fiable de l'attention publique)
    - Presse: 35% (couverture médiatique)
    - Trends: 25% (intérêt de recherche)
    """
    # Normalisation logarithmique pour Wikipedia (évite que les gros chiffres écrasent)
    import math
    wiki_norm = min(math.log10(max(wiki_views, 1)) / 5, 1) * 100  # log10(100000) = 5
    
    # Normalisation linéaire pour la presse (0-50 articles = 0-100)
    press_norm = min(press_articles / 50, 1) * 100
    
    # Trends déjà sur 0-100
    trends_norm = min(trends_score, 100)
    
    # Score pondéré
    score = (wiki_norm * 0.40) + (press_norm * 0.35) + (trends_norm * 0.25)
    
    return round(min(score, 100), 1)


# =============================================================================
# INTERFACE UTILISATEUR
# =============================================================================

def main():
    # Header principal
    st.markdown("""
    <div class="main-header">
        <h1>🗳️ Visibility Index</h1>
        <p>Tableau de bord de visibilité • Municipales Paris 2026</p>
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
        
        # Bouton de rafraîchissement
        st.markdown("---")
        if st.button("🔄 Actualiser les données", use_container_width=True, type="primary"):
            st.cache_data.clear()
            st.rerun()
        
        # Infos
        st.markdown("---")
        st.markdown("""
        ### 📊 Sources de données
        - **Wikipedia** : Pageviews (API Wikimedia)
        - **Presse** : Articles (GDELT)
        - **Recherches** : Google Trends
        
        *Données mises à jour toutes les heures*
        """)
    
    # Vérification qu'au moins un candidat est sélectionné
    if not selected_candidates:
        st.warning("⚠️ Veuillez sélectionner au moins un candidat dans la barre latérale.")
        return
    
    # Collecte des données
    with st.spinner("📊 Collecte des données en cours..."):
        all_data = collect_all_data(selected_candidates, start_date, end_date)
    
    # Affichage des résultats
    display_results(all_data, start_date, end_date)


def collect_all_data(candidates: list, start_date: date, end_date: date) -> dict:
    """Collecte toutes les données pour les candidats sélectionnés."""
    
    all_data = {}
    
    # Progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Collecter les données Google Trends pour tous les candidats en une fois
    status_text.text("📈 Récupération Google Trends...")
    all_keywords = [CANDIDATES[c]["name"] for c in candidates]
    trends_data = get_google_trends_data(all_keywords)
    progress_bar.progress(20)
    
    # Collecter les données par candidat
    for i, cand_id in enumerate(candidates):
        cand = CANDIDATES[cand_id]
        status_text.text(f"📊 Analyse de {cand['name']}...")
        
        # Wikipedia
        wiki_data = get_wikipedia_pageviews(
            cand["wikipedia"],
            start_date,
            end_date
        )
        
        # GDELT (Presse)
        press_data = get_gdelt_articles(
            cand["name"],
            start_date,
            end_date
        )
        
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
            press_data.get("article_count", 0),
            trends_score
        )
        
        all_data[cand_id] = {
            "info": cand,
            "wikipedia": wiki_data,
            "press": press_data,
            "trends": {
                "score": trends_score,
                "timeseries": trends_timeseries,
                "success": trends_data.get("success", False)
            },
            "visibility_score": visibility_score
        }
        
        progress_bar.progress(20 + int(80 * (i + 1) / len(candidates)))
    
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
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_wiki = sum(d["wikipedia"]["total_views"] for _, d in sorted_candidates)
    total_press = sum(d["press"]["article_count"] for _, d in sorted_candidates)
    avg_score = sum(d["visibility_score"] for _, d in sorted_candidates) / len(sorted_candidates)
    leader = sorted_candidates[0] if sorted_candidates else None
    
    with col1:
        st.metric(
            label="🏆 Leader",
            value=leader[1]["info"]["name"] if leader else "N/A",
            delta=f"{leader[1]['visibility_score']:.1f} pts" if leader else None
        )
    
    with col2:
        st.metric(
            label="📚 Total Wikipedia",
            value=f"{total_wiki:,}",
            help="Total des pageviews Wikipedia"
        )
    
    with col3:
        st.metric(
            label="📰 Articles presse",
            value=f"{total_press}",
            help="Total des articles trouvés"
        )
    
    with col4:
        st.metric(
            label="📊 Score moyen",
            value=f"{avg_score:.1f}",
            help="Score de visibilité moyen"
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
            "Trends": round(data["trends"]["score"], 1)
        })
    
    df_ranking = pd.DataFrame(ranking_data)
    
    # Affichage avec style
    st.dataframe(
        df_ranking,
        column_config={
            "Rang": st.column_config.NumberColumn("🏅 Rang", format="%d"),
            "Candidat": st.column_config.TextColumn("👤 Candidat"),
            "Parti": st.column_config.TextColumn("🏛️ Parti"),
            "Score": st.column_config.ProgressColumn(
                "📊 Score",
                min_value=0,
                max_value=100,
                format="%.1f"
            ),
            "Wikipedia": st.column_config.NumberColumn("📚 Wikipedia", format="%d"),
            "Presse": st.column_config.NumberColumn("📰 Presse", format="%d"),
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
    
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Scores", "📚 Wikipedia", "📰 Presse", "📈 Évolution"])
    
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
            title="Score de visibilité par candidat"
        )
        fig_scores.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig_scores, use_container_width=True)
    
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
            title="Pageviews Wikipedia"
        )
        fig_wiki.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig_wiki, use_container_width=True)
    
    with tab3:
        # Presse - Pie chart
        fig_press = px.pie(
            df_ranking,
            values="Presse",
            names="Candidat",
            title="Répartition de la couverture presse",
            color="Candidat",
            color_discrete_map={
                f"{CANDIDATES[cid]['emoji']} {CANDIDATES[cid]['name']}": CANDIDATES[cid]["color"]
                for cid in CANDIDATES
            }
        )
        fig_press.update_layout(height=400)
        st.plotly_chart(fig_press, use_container_width=True)
    
    with tab4:
        # Évolution temporelle Wikipedia
        st.markdown("### 📈 Évolution des pageviews Wikipedia")
        
        # Construire le dataframe d'évolution
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
        with st.expander(f"{data['info']['emoji']} **{data['info']['name']}** - Score: {data['visibility_score']:.1f}", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("### 📚 Wikipedia")
                st.metric("Pageviews", f"{data['wikipedia']['total_views']:,}")
                st.metric("Moyenne/jour", f"{data['wikipedia']['daily_avg']:.0f}")
            
            with col2:
                st.markdown("### 📰 Presse")
                st.metric("Articles", data['press']['article_count'])
                st.metric("Sources", data['press']['domain_count'])
            
            with col3:
                st.markdown("### 📈 Google Trends")
                st.metric("Score moyen", f"{data['trends']['score']:.1f}")
                status = "✅ OK" if data['trends']['success'] else "⚠️ Limité"
                st.caption(f"Statut: {status}")
            
            # Afficher les derniers articles
            if data['press']['articles']:
                st.markdown("#### 📰 Derniers articles")
                for article in data['press']['articles'][:5]:
                    title = article.get('title', 'Sans titre')
                    url = article.get('url', '#')
                    domain = article.get('domain', 'Source inconnue')
                    st.markdown(f"- [{title[:80]}...]({url}) *({domain})*")
    
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
    with st.expander("📋 Voir le résumé (copier-coller)"):
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
        "📊 MÉTRIQUES:",
        f"• Wikipedia total: {sum(d['wikipedia']['total_views'] for _, d in sorted_candidates):,} vues",
        f"• Articles presse: {sum(d['press']['article_count'] for _, d in sorted_candidates)}",
        "",
        f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}"
    ])
    
    return "\n".join(lines)


if __name__ == "__main__":
    main()
