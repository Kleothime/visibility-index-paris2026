# 🗳️ Visibility Index - Paris 2026

Application web interactive pour suivre la visibilité des candidats aux municipales de Paris 2026.

## 🚀 Déploiement en ligne (Streamlit Cloud)

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

## 📊 Fonctionnalités

- **Sélection de période** : Choisissez la plage de dates à analyser (3, 7, 14 ou 30 jours)
- **Multi-candidats** : Sélectionnez les candidats à comparer
- **Score de visibilité** : Indice composite basé sur Wikipedia, presse et Google Trends
- **Graphiques interactifs** : Visualisations Plotly zoomables
- **Export** : Téléchargez les données en CSV ou le résumé en texte

## 📈 Sources de données

| Source | Description | Fiabilité |
|--------|-------------|-----------|
| **Wikipedia** | Pageviews des pages des candidats | ⭐⭐⭐⭐⭐ |
| **GDELT** | Articles de presse française | ⭐⭐⭐⭐ |
| **Google Trends** | Intérêt de recherche | ⭐⭐⭐ |

## 🔧 Personnalisation

Pour ajouter/modifier des candidats, éditez le dictionnaire `CANDIDATES` dans `app.py` :

```python
CANDIDATES = {
    "nouveau_candidat": {
        "name": "Nom Complet",
        "party": "Parti politique",
        "color": "#HEX",
        "wikipedia": "Page_Wikipedia",
        "search_terms": ["Terme de recherche"],
        "emoji": "👤"
    },
    ...
}
```

## 📝 Licence

Usage libre pour analyse politique et journalistique.
