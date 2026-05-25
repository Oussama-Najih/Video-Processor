## VideoFlow - Présentation de la plateforme

**VideoFlow** est une plateforme de gestion et de diffusion de vidéos basée sur une architecture **microservices**.  
Elle permet à un utilisateur de :

- s’**authentifier** via Keycloak,
- **uploader** une vidéo (upload multipart, avec reprise),
- déclencher automatiquement le **traitement vidéo** (transcodage + génération HLS),
- **lire** la vidéo en streaming (**HLS**, multi-résolutions),
- **rechercher** des vidéos via une recherche full-text (Elasticsearch),
- recevoir des **notifications** (ex: email) lors des événements importants (fin de traitement).

### Architecture globale (3 dépôts)

La plateforme est répartie en **3 projets complémentaires** :

1) **Frontend (React + TypeScript)** — `Oussama-Najih/videoflow_f`  
   Interface utilisateur : upload, lecture HLS, recherche, pagination/scroll infini, etc.

2) **Backend Microservices (Java / Spring Boot)** — `Oussama-Najih/Microservices-VideoFlow`  
   Ensemble de microservices Spring Boot (API Gateway + services métier : vidéo, utilisateurs, recherche, notifications) et orchestration du pipeline via **Kafka / Kafka Streams**.

3) **Backend Processing (Python) — Microservices** — `Oussama-Najih/Video-Processor`  
   Un ensemble de **microservices Python** dédiés au traitement vidéo :
   - transcodage / génération des rendus (**HLS**)
   - détection de contenu NSFW (analyse des frames + scoring)
   - génération de **miniatures** (sprites + VTT)


### Parcours typique d’une vidéo

1. L’utilisateur se connecte (Keycloak) depuis le frontend.
2. Il upload la vidéo (multipart résumable) via l’API backend.
3. Le backend enregistre les métadonnées et stocke la vidéo (MinIO/S3).
4. Des événements Kafka déclenchent le **processing** côté Python.
5. Le processing génère les fichiers HLS (résolutions + segments).
6. Le backend expose au frontend les manifests/index avec des URLs présignées.
7. La vidéo devient consultable et indexée pour la recherche (Elasticsearch).

---

# Video-Processor : Backend Processing (Python Microservices)

Ce dépôt contient la partie **processing vidéo** de la plateforme **VideoFlow**.  

Il s’agit d’un ensemble de **microservices Python** qui consomment des événements Kafka pour traiter les vidéos (**HLS**, **thumbnails**, **détection NSFW**) puis publier l’état/résultat du pipeline.

---

## Rôle dans l’architecture VideoFlow

Le backend **Java (Spring Boot)** gère l’API, les métadonnées, la sécurité et la recherche.  
Ce projet intervient **après l’upload** pour exécuter les traitements asynchrones lourds (encodage, génération HLS, analyse NSFW…).

### Flux simplifié

1. Le backend Java publie un événement Kafka : `videos.uploaded`
2. Les microservices Python consomment cet événement en parallèle
3. Chaque microservice produit un événement : `videos.pipeline.done`
4. Le backend Java orchestre la suite (indexation, notifications, disponibilité du streaming HLS…)

---

## Microservices Python

Le lanceur `src/run.py` démarre **3 services** :

### 1) Thumbnail Service (`src/thumbnail_service.py`)
- Génère des **spritesheets** + fichier **VTT** (thumbnails timeline)
- Extrait des frames avec **ffmpeg/ffprobe**
- Upload les résultats vers **S3/MinIO**
- Publie `videos.pipeline.done`

### 2) Transcode Service (`src/transcode_service.py`)
- Génère le streaming **HLS** multi-résolutions (actuellement : **360p**, **720p**)
- Crée un `master.m3u8`, des playlists variants `index.m3u8` et des segments `.ts`
- Upload les résultats vers **S3/MinIO**
- Publie `videos.pipeline.done`

### 3) NSFW Service (`src/nsfw_service.py`)
- Détecte le contenu explicite (OpenNSFW / Caffe)
- Analyse des frames vidéo et retourne des scores + frames “sensibles”
- Utilise **Docker** pour exécuter le modèle (container `nsfw_detect_service`)
- Publie `videos.pipeline.done`

---

## Prérequis

- Docker (obligatoire pour le service NSFW)
- `ffmpeg` + `ffprobe`
- Kafka et MinIO démarrés 

---

## Installation (avec Pipenv)

```bash
pipenv install
pipenv shell
```
---

## Démarrage

Lancer le point d’entrée (démarre les 3 microservices) :

```bash
python3 -m src.run
```

Ce script :
- lance les 3 microservices,
- supervise leur exécution,
- arrête proprement les processus,
- stoppe le container Docker NSFW (`nsfw_detect_service`) à la fermeture.

---

## Topics Kafka

- **Input** : `videos.uploaded`
- **Output** : `videos.pipeline.done`

---

## Structure du projet

- `src/run.py` : orchestrateur/superviseur des services
- `src/transcode_service.py` : encodage HLS + upload des résultats
- `src/thumbnail_service.py` : sprites + VTT + upload des résultats
- `src/nsfw_service.py` : détection NSFW + orchestration Docker
- `src/nsfw_detect.py` : logique de scoring NSFW
- `src/threshold.py` : filtrage / seuil sur les résultats
- `utils/` : helpers Kafka + S3/MinIO + nettoyage
- `open_nsfw/` : modèle/ressources OpenNSFW

---

## Notes

- Les fichiers temporaires sont gérés automatiquement (nettoyage des dossiers de travail).
- Le service NSFW utilise un conteneur Docker dédié : `nsfw_detect_service`.

---

## Licence

- Le code du projet : **MIT**
- Le dossier `open_nsfw/` contient du code sous licence de type **BSD (Yahoo Inc.)**.

### Licences tierces (Third‑party licenses)

Ce projet inclut du code provenant de tiers :

- **`open_nsfw/`** — Licence de type **BSD (Yahoo Inc., 2016)**  
  Copyright 2016, Yahoo Inc.  
  Les conditions de redistribution et la clause de non‑responsabilité s’appliquent à ce dossier.  
  Voir le fichier `open_nsfw/LICENSE` pour le texte complet de la licence.