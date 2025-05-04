
# Dashboard Législatives 2024 - Paris (Version 2)

## Fonctionnalités
- Résultats électoraux par quartier avec couleurs des partis.
- Résultats en pourcentage (arrondi à 1 décimale).
- Filtre par partis, indicateur social et quartiers.
- Coloration des quartiers selon l'indicateur social sélectionné (plus l'indicateur est élevé, plus la couleur est foncée).

## Fichiers
- app_legislatives_2024_version2.py : Code Streamlit version 2.
- requirements.txt : Liste des bibliothèques nécessaires.
- README.md : Ce guide.

## Installation locale
1. Installer Python 3.
2. Installer les dépendances :
```bash
pip install -r requirements.txt
```
3. Placer votre fichier Excel `Législatives 2024 Geo v1.0.xlsx` dans le même dossier.
4. Lancer l'application :
```bash
streamlit run app_legislatives_2024_version2.py
```

## Déploiement Streamlit Cloud
1. Créer un dépôt GitHub.
2. Ajouter :
    - app_legislatives_2024_version2.py
    - requirements.txt
    - Législatives 2024 Geo v1.0.xlsx
3. Connecter le dépôt à Streamlit Cloud et déployer.
