# Guide de déploiement

## Configuration des secrets (IMPORTANT)

### En local

1. Créez le fichier `.streamlit/secrets.toml` (déjà créé)
2. Ajoutez votre clé API YouTube :
```toml
YOUTUBE_API_KEY = "VOTRE_CLE_API_ICI"
```

**ATTENTION** : Ce fichier ne doit JAMAIS être commité sur Git (déjà dans .gitignore)

### Sur Streamlit Cloud

1. Allez dans les paramètres de votre app sur Streamlit Cloud
2. Cliquez sur "Secrets"
3. Ajoutez :
```toml
YOUTUBE_API_KEY = "VOTRE_CLE_API_ICI"
```

## Obtenir une clé API YouTube

1. Allez sur https://console.cloud.google.com/
2. Créez un nouveau projet ou sélectionnez-en un
3. Activez "YouTube Data API v3"
4. Créez des identifiants API
5. Copiez la clé et ajoutez-la dans les secrets

**Quotas gratuits** : 10 000 unités/jour (suffisant pour cette application)

## Sécurité

✅ La clé API est maintenant sécurisée via `st.secrets`
✅ Le fichier `.gitignore` empêche de commiter les secrets
✅ L'ancienne clé exposée dans le code doit être **révoquée** sur Google Cloud Console

## Prochaines étapes recommandées

1. **URGENT** : Révoquez l'ancienne clé API (`AIzaSyCu27YMexJiCrzagkCnawkECG7WA1_wzDI`) sur Google Cloud Console
2. Générez une nouvelle clé API
3. Ajoutez-la dans `.streamlit/secrets.toml` localement
4. Ajoutez-la dans les secrets Streamlit Cloud
5. Testez l'application

## Notes

- L'application fonctionne sans clé YouTube mais n'affichera pas les données YouTube
- Toutes les autres sources de données (Wikipedia, GDELT, Google News, Trends) fonctionnent sans API key
