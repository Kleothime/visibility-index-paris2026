# Visibility Index - Paris 2026

Application web interactive pour suivre la visibilité médiatique des candidats aux municipales de Paris 2026.

## Déploiement en ligne (Streamlit Cloud)

### Méthode 1 : Déploiement rapide

1. **Créer un compte GitHub** (si pas déjà fait) : https://github.com/signup

2. **Créer un nouveau repository** :
   - Aller sur https://github.com/new
   - Nom : `visibility-index-paris2026`
   - Cocher "Public"
   - Cliquer "Create repository"

3. **Uploader les fichiers** :
   - Sur la page du repo, cliquer "uploading an existing file"
   - Glisser-déposer tous les fichiers de ce dossier
   - Cliquer "Commit changes"

4. **Déployer sur Streamlit Cloud** :
   - Aller sur https://share.streamlit.io/
   - Se connecter avec GitHub
   - Cliquer "New app"
   - Sélectionner votre repository
   - Main file path : `app.py`
   - Cliquer "Deploy!"

5. **C'est prêt !** Vous aurez un lien du type :
   `https://votre-nom-visibility-index-paris2026.streamlit.app`

### Méthode 2 : En local

```bash
# Installer les dépendances
pip install -r requirements.txt

# Lancer l'application
streamlit run app.py
```

L'application sera accessible sur http://localhost:8501

## Fonctionnalités

- **Sélection de période** : Choisissez la plage de dates à analyser (7, 14 ou 30 jours)
- **Multi-candidats** : Sélectionnez les candidats à comparer
- **Score de visibilité** : Indice composite basé sur Google Trends, presse et Wikipedia
- **Sondages officiels** : Intégration des sondages IFOP, Elabe et autres instituts reconnus
- **Graphiques interactifs** : Visualisations Plotly optimisées
- **Analyse TV/Radio** : Détection automatique des passages médias avec liens
- **Suivi Instagram** : Recherche de posts publics par hashtag mentionnant les candidats
- **Historique** : Suivi temporel avec sauvegarde cloud optionnelle

## Sources de données

| Source | Description | Pondération |
|--------|-------------|-------------|
| **Presse** | Articles GDELT + Google News | 40% |
| **Google Trends** | Intérêt de recherche France | 35% |
| **Wikipedia** | Vues des pages françaises | 15% |
| **YouTube** | Vidéos mentionnant les candidats | 10% |

## Personnalisation

Pour ajouter/modifier des candidats, éditez le dictionnaire `CANDIDATES` dans [app.py](app.py) :

```python
CANDIDATES = {
    "nouveau_candidat": {
        "name": "Nom Complet",
        "party": "Parti politique",
        "color": "#HEXCOLOR",
        "wikipedia": "Page_Wikipedia",
        "search_terms": ["Terme 1", "Terme 2"],
    },
}
```

Pour ajouter des sondages, éditez la liste `SONDAGES` dans [app.py](app.py) :

```python
SONDAGES = [
    {
        "date": "2024-11-04",
        "institut": "IFOP-Fiducial",
        "commanditaire": "Le Figaro / Sud Radio",
        "echantillon": 1037,
        "methode": "Questionnaire auto-administré en ligne",
        "hypothese": "Description de l'hypothèse",
        "url": "https://lien-vers-le-sondage.com",
        "scores": {
            "Candidat 1": 27,
            "Candidat 2": 18,
        }
    },
]
```

## Nouveautés v9.0

- **Suivi Instagram** : Nouvel onglet pour suivre les posts Instagram mentionnant les candidats
- Recherche par hashtag avec détection automatique des mentions
- Métriques d'engagement (likes + commentaires)
- Graphiques comparatifs entre candidats
- Listes détaillées avec boutons "Voir plus"

## Nouveautés v8.0

- Interface 100% francophone
- Suppression de tous les émojis
- Format français pour les nombres (espaces entre milliers)
- Amélioration de la fiabilité Google Trends
- Section "Vidéos YouTube les mentionnant" renommée
- Sondages officiels complets (IFOP, Elabe)
- Période 48h supprimée pour garantir la fiabilité
- Section TV/Radio améliorée avec liens cliquables
- Tooltips simplifiés sur tous les graphiques

## Licence

Usage libre pour analyse politique et journalistique.
