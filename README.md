# RiskMap-SMCA

Application web de gestion et de cartographie des risques dans le cadre d'un
Système de Management de la Continuité d'Activité (SMCA).

## 1. Présentation du projet

RiskMap-SMCA est une application destinée à aider une organisation à identifier,
évaluer, cartographier et traiter les risques pouvant affecter ses processus
critiques et la continuité de ses activités.

L'objectif est de centraliser les informations relatives aux processus,
aux actifs, aux risques et aux plans de traitement dans une interface web.

## 2. Objectifs

- Identifier les risques liés aux processus métiers.
- Recenser les actifs associés aux processus.
- Évaluer les risques selon leur probabilité et leur impact.
- Visualiser les risques dans une matrice de criticité 5×5.
- Définir et suivre les mesures de traitement.
- Calculer le niveau de risque résiduel après traitement.
- Contrôler les accès selon les rôles des utilisateurs.

## 3. Fonctionnalités

### Gestion des processus
- Création, consultation, modification et suppression des processus.
- Définition de la criticité.
- Définition des paramètres de continuité :
  - MTPD : durée maximale d'interruption tolérable.
  - RTO : objectif de temps de reprise.
  - RPO : objectif de point de reprise.
- Association des actifs aux processus.

### Gestion des actifs
- Enregistrement des actifs de l'organisation.
- Gestion des types d'actifs : serveur, application, local,
  personnel et fournisseur.
- Association des actifs aux processus et aux risques.

### Gestion des risques
- Création et suivi des risques.
- Identification des menaces et vulnérabilités.
- Évaluation de la probabilité et de l'impact sur une échelle de 1 à 5.
- Calcul automatique du score et du niveau de risque.

### Cartographie des risques
- Matrice de criticité 5×5.
- Visualisation des risques selon leur probabilité et leur impact.
- Répartition des risques par niveau de criticité.

### Traitement des risques
- Définition d'une stratégie de traitement :
  - Réduire
  - Accepter
  - Transférer
  - Éviter
- Description des actions à réaliser.
- Affectation d'un responsable et d'une échéance.
- Suivi du statut : à faire, en cours ou terminé.
- Évaluation du risque résiduel.

## 4. Méthode d'évaluation des risques

Le score du risque est calculé selon la formule :

**Score = Probabilité × Impact**

La probabilité et l'impact sont évalués sur une échelle de 1 à 5.

| Score | Niveau |
|---|---|
| 1 à 4 | Faible |
| 5 à 9 | Moyen |
| 10 à 15 | Élevé |
| 16 à 25 | Critique |

Le risque résiduel est évalué à partir de la probabilité et de l'impact
estimés après la mise en œuvre des mesures de traitement.

## 5. Architecture technique

L'application repose sur une architecture composée de plusieurs services :

- **Frontend** : HTML, CSS et JavaScript.
- **Backend** : Python et FastAPI.
- **Base de données** : PostgreSQL 16.
- **Reverse proxy et serveur web** : Nginx.
- **Conteneurisation** : Docker et Docker Compose.
- **Authentification** : JWT et hachage des mots de passe.

### Architecture logique

```text
             Utilisateur
                  |
                  v
          Interface Web
          HTML / CSS / JS
                  |
                  v
             Nginx
          Reverse Proxy
                  |
                  v
          Backend FastAPI
                  |
          -----------------
          |               |
          v               v
     PostgreSQL       API REST
      Database
```

## 6. Installation et lancement

### Prérequis

- Linux ou environnement compatible Docker.
- Docker Engine.
- Docker Compose.
- Git.

### Récupération du projet

```bash
git clone git@github-riskmap:oumayma-naffeti/riskmap-smca.git
cd riskmap-smca
```

### Configuration

Configurer les variables d'environnement nécessaires au backend et à
PostgreSQL dans le fichier `.env`, conformément à la configuration du projet.

**Important :** ne jamais publier le fichier `.env` ni ses secrets sur GitHub.

### Démarrage

```bash
docker compose up -d --build
```

### Vérification des conteneurs

```bash
docker compose ps
```

### Consultation des logs

```bash
docker compose logs -f
```

## 7. Accès à l'application

Après le démarrage des services :

| Service | Adresse |
|---|---|
| Application web | http://localhost:8080 |
| API Backend | http://localhost:8000 |
| Documentation Swagger | http://localhost:8000/docs |
| Vérification de santé | http://localhost:8000/api/health |

Pour accéder à l'application depuis un autre poste, remplacer `localhost`
par l'adresse IP de la machine qui héberge les conteneurs, si le réseau
et le pare-feu l'autorisent.

## 8. Structure du projet

```text
riskmap-smca/
├── backend/
│   └── app/
│       ├── routers/
│       │   ├── assets.py
│       │   ├── auth.py
│       │   ├── processes.py
│       │   ├── risks.py
│       │   ├── treatments.py
│       │   └── users.py
│       ├── config.py
│       ├── database.py
│       ├── deps.py
│       ├── main.py
│       ├── models.py
│       ├── schemas.py
│       ├── scoring.py
│       └── security.py
├── frontend/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   ├── api.js
│   │   └── app.js
│   ├── nginx/
│   │   └── default.conf
│   └── index.html
├── docker-compose.yaml
├── README.md
└── .gitignore
```

## 9. Sécurité

Le projet intègre notamment :

- Une authentification basée sur JWT.
- Le hachage des mots de passe.
- Une gestion des rôles et des autorisations.
- Une séparation entre frontend, backend et base de données.
- Une configuration des secrets à travers les variables d'environnement.

Les secrets et données sensibles ne doivent jamais être ajoutés au dépôt Git.

## 10. Technologies

| Domaine | Technologies |
|---|---|
| Backend | Python, FastAPI |
| Frontend | HTML, CSS, JavaScript |
| Base de données | PostgreSQL 16 |
| Conteneurisation | Docker, Docker Compose |
| Serveur web | Nginx |
| Authentification | JWT, bcrypt |
| Documentation API | Swagger / OpenAPI |

---

**RiskMap-SMCA** — Projet académique consacré à l'identification,
l'évaluation, la cartographie et au traitement des risques dans un SMCA.
