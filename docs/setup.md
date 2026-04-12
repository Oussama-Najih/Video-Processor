# Configuration de l'environnement de développement sur Windows

## 1. Installation de Node.js

Téléchargez Node.js depuis le [site officiel](https://nodejs.org/en/download/), choisissez la version LTS recommandée pour la plupart des utilisateurs, puis installez-le en suivant l’assistant d’installation.

### 1.1 Vérifier l'installation

Ouvrez **PowerShell** ou **cmd** :

```cmd
node -v
npm -v
```

---

## 2. Installation de Python 3 et Pipenv

### 2.1 Installer Python

Téléchargez Python depuis le [site officiel](https://www.python.org/downloads/windows/).  
Lors de l’installation, cochez **“Add Python to PATH”**.

### 2.2 Vérifier si Python est installé

```cmd
python --version
```

### 2.3 Installer ou mettre à jour pip

```cmd
python -m ensurepip --upgrade
```

### 2.4 Installer Pipenv

```cmd
pip install pipenv
```

---

## 3. Configurer l'environnement virtuel Python

### 3.1 Clonez le dépôt du projet

```cmd
git clone <URL_DU_DEPOT> VideoFlix
cd VideoFlix
```

### 3.2 Créer un environnement virtuel

```cmd
pipenv --python 3
```

### 3.3 Vérifier l'environnement virtuel

```cmd
pipenv --venv
```

### 3.4 Activer l'environnement virtuel

```cmd
pipenv shell
```

---

## 4. Installer les dépendances JavaScript et Python

### 4.1 Installer les dépendances Node.js

```cmd
npm install
```

### 4.2 Installer les dépendances Python (depuis Pipfile)

```cmd
pipenv install
```

---

## 5. Génération et traitement des fichiers

### 5.1 Générer les feuilles de calcul et le fichier de mapping (detection.json)

```cmd
node frames/generateSprite.js
```

### 5.2 Tester et filtrer les feuilles

```cmd
python detector/filter_frames.py
```

### 5.3 Générer les scores élevés

```cmd
python highscore/confident.py
```
---

## Résumé du flux de travail

1. Installez Node.js via le site officiel (version LTS).
2. Installez Python et Pipenv.
3. Créez et activez l'environnement virtuel Python avec Pipenv.
4. Installez les dépendances Node (`npm install`) et Python (`pipenv install`).
5. Ajouter une vidéo de test dans le dossier `videos_test` et mettez à jour le chemin dans `frames/generateSprite.js` (ligne 4).
6. Générez les sprite sheets et un fichier `metadata.json` de mapping (`node frames/generateSprite.js`).
7. Naviguez vers l'environnement virtuel et filtrez les résultats (`python detector/filter_frames.py`), puis vérifiez les résultats dans `detector/detections.json`.
8. Générez les scores élevés avec `python highscore/confident.py` et vérifiez les résultats dans `highscore/high_score_frames.json` et visualisez les frames correspondantes dans le dossier `high_score/high_score_sheets`.

---
