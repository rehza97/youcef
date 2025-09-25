# Documentation Complète - Backend FastAPI Youcef

## Table des Matières

1. [Vue d&#39;ensemble](#vue-densemble)
2. [Architecture](#architecture)
3. [Configuration](#configuration)
4. [Authentification et Autorisation](#authentification-et-autorisation)
5. [Endpoints API](#endpoints-api)
6. [Modèles de Données](#modèles-de-données)
7. [Services](#services)
8. [Système ETL](#système-etl)
9. [WebSocket](#websocket)
10. [Gestion des Fichiers](#gestion-des-fichiers)
11. [Système de Messagerie](#système-de-messagerie)
12. [Notifications](#notifications)
13. [Gestion des Rôles et Permissions](#gestion-des-rôles-et-permissions)
14. [Traitement des Données d&#39;Encaissement](#traitement-des-données-dencaissement)
15. [Gestion des Parcs Télécom](#gestion-des-parcs-télécom)
16. [Système de Traitement en Arrière-plan](#système-de-traitement-en-arrière-plan)
17. [Système ETL (Extract, Transform, Load)](#système-etl-extract-transform-load)
18. [Système d'Analytics et de Reporting](#système-danalytics-et-de-reporting)
19. [Sécurité](#sécurité)
20. [Déploiement](#déploiement)

---

## Vue d'ensemble

Le backend FastAPI Youcef est une API REST complète avec des fonctionnalités temps réel, conçue pour gérer :

- **Authentification et autorisation** avec système RBAC (Role-Based Access Control)
- **Messagerie en temps réel** avec WebSocket
- **Gestion des fichiers** avec prévisualisation et traitement
- **Système de notifications** temps réel
- **Traitement des données d'encaissement** avec analytics
- **Système ETL complet** pour le traitement de données
- **Gestion des parcs télécom** avec modèles DOT et Park
- **Traitement des données Algérie Télécom** (NGBSS, Parc Corporate)
- **Gestion des utilisateurs** et des rôles
- **Système de blocage d'utilisateurs**
- **Traitement asynchrone** avec WebSocket pour les mises à jour

### Technologies Utilisées

- **FastAPI** : Framework web moderne et rapide
- **SQLAlchemy** : ORM pour la base de données
- **PostgreSQL** : Base de données principale
- **WebSocket** : Communication temps réel
- **JWT** : Authentification par tokens
- **Pandas** : Traitement des données
- **Pydantic** : Validation des données

---

## Architecture

### Structure du Projet

```
fastapi_backend/
├── main.py                 # Point d'entrée de l'application
├── websocket_manager.py    # Gestionnaire WebSocket
├── core/                   # Configuration et sécurité
│   ├── config.py          # Paramètres de l'application
│   ├── security.py        # Authentification et autorisation
│   └── rate_limiter.py    # Limitation du taux de requêtes
├── api/                    # Endpoints API
│   ├── auth.py            # Authentification
│   ├── users_management.py # Gestion des utilisateurs
│   ├── user_role_assignments.py # Assignation des rôles
│   ├── user_blocks.py     # Blocage d'utilisateurs
│   ├── notifications.py   # Notifications
│   ├── conversations.py   # Conversations
│   ├── message_crud.py    # CRUD des messages
│   ├── message_attachments.py # Pièces jointes des messages
│   ├── message_reactions.py # Réactions aux messages
│   ├── file_upload.py     # Upload de fichiers
│   ├── file_management.py # Gestion des fichiers
│   ├── file_preview.py    # Prévisualisation des fichiers
│   ├── file_processing.py # Traitement des fichiers
│   ├── role_management.py # Gestion des rôles
│   ├── permission_management.py # Gestion des permissions
│   ├── encaissement_upload.py # Upload des encaissements
│   ├── encaissement_analytics.py # Analytics des encaissements
│   ├── etl_processing.py  # Traitement ETL
│   ├── park_management.py # Gestion des parcs télécom
│   └── health.py          # Santé de l'application
├── models/                 # Modèles de données
│   ├── user.py            # Modèle utilisateur
│   ├── role.py            # Modèle rôle
│   ├── permission.py      # Modèle permission
│   ├── conversation.py    # Modèle conversation
│   ├── message.py         # Modèle message
│   ├── notification.py    # Modèle notification
│   ├── file_upload.py     # Modèle fichier
│   ├── user_block.py      # Modèle blocage utilisateur
│   ├── dot.py             # Modèle DOT
│   └── park.py            # Modèle Park
├── services/              # Logique métier
│   ├── encaissement_processor.py # Processeur d'encaissement
│   ├── file_service.py    # Service de gestion des fichiers
│   ├── file_processing_service.py # Service de traitement des fichiers
│   ├── notification_service.py # Service de notifications
│   ├── permission_service.py # Service de permissions
│   ├── park_processing.py # Service de traitement des parcs
│   ├── background_processor.py # Processeur en arrière-plan
│   ├── processing_websocket.py # WebSocket de traitement
│   └── etl/               # Services ETL
│       ├── base.py        # Classes de base ETL
│       ├── utils.py       # Utilitaires ETL
│       ├── encaissement_etl.py # ETL Encaissement
│       ├── performance_kpi_etl.py # ETL Performance KPI
│       ├── subscriber_park_etl.py # ETL Parc d'abonnés
│       └── parc_corporate_ngbss_etl.py # ETL Parc Corporate NGBSS
├── database/              # Configuration de la base de données
│   └── connection.py      # Connexion à la base de données
├── alembic/               # Migrations de base de données
│   ├── env.py            # Configuration Alembic
│   └── versions/         # Versions des migrations
└── uploads/               # Stockage des fichiers
    ├── excel/            # Fichiers Excel
    ├── csv/              # Fichiers CSV
    └── temp/             # Fichiers temporaires
```

### Flux de Données

1. **Requête HTTP** → **Middleware** → **Router** → **Service** → **Modèle** → **Base de données**
2. **WebSocket** → **Manager** → **Notification/Message** → **Client**

---

## Configuration

### Variables d'Environnement

```python
# Application
APP_NAME = "Youcef Backend API"
APP_VERSION = "1.0.0"
DEBUG = True

# Serveur
HOST = "0.0.0.0"
PORT = 8000

# Base de données
DATABASE_URL = "postgresql://postgres:123456789@localhost:5432/youcef_db"

# Sécurité
SECRET_KEY = "your-secret-key-change-in-production"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Limitation du taux
RATE_LIMIT_LOGIN = "5/minute"
RATE_LIMIT_REGISTER = "3/minute"

# Fichiers
MAX_FILE_SIZE = 10GB  # Limite très élevée pour les gros fichiers
UPLOAD_DIR = "uploads"

# Redis
REDIS_URL = "redis://localhost:6379"

# WebSocket
WS_MESSAGE_QUEUE_SIZE = 1000

# Logging
LOG_LEVEL = "INFO"
LOG_FILE = "fastapi.log"
```

---

## Authentification et Autorisation

### Système d'Authentification

- **JWT Tokens** : Access token (30 min) + Refresh token (7 jours)
- **Hachage des mots de passe** : bcrypt
- **Validation de la force** : 8 caractères minimum, majuscules, minuscules, chiffres

### Rôles et Permissions

#### Rôles Système

- **ADMIN** : Accès complet à toutes les fonctionnalités
- **SUPER_USER** : Accès étendu (mot de passe fixe par politique)
- **DOT_USER** : Accès limité à son DOT spécifique

#### Permissions

- `view_users`, `edit_users`, `delete_users`
- `manage_roles`, `manage_permissions`
- `send_messages`, `view_messages`
- `manage_notifications`, `upload_files`

---

## Endpoints API

### 1. Authentification (`/api/auth`)

#### POST `/register`

**Description** : Inscription d'un nouvel utilisateur
**Paramètres** :

```json
{
  "username": "string",
  "email": "string",
  "password": "string",
  "first_name": "string",
  "last_name": "string",
  "bio": "string",
  "avatar_url": "string"
}
```

**Réponse** :

```json
{
  "success": true,
  "message": "User registered successfully",
  "data": {
    "id": 1,
    "username": "user123",
    "email": "user@example.com"
  }
}
```

#### POST `/login`

**Description** : Connexion utilisateur
**Paramètres** :

```json
{
  "username": "string", // username ou email
  "password": "string"
}
```

**Réponse** :

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": 1,
    "username": "user123",
    "email": "user@example.com",
    "is_active": true,
    "is_staff": false,
    "is_superuser": false
  }
}
```

#### POST `/refresh-token`

**Description** : Renouvellement du token d'accès
**Paramètres** :

```json
{
  "refresh_token": "string"
}
```

#### POST `/logout`

**Description** : Déconnexion utilisateur

#### GET `/protected`

**Description** : Test d'endpoint protégé

### 2. Gestion des Utilisateurs (`/api/users`)

#### POST `/`

**Description** : Créer un utilisateur (Admin uniquement)
**Autorisation** : Admin

#### GET `/`

**Description** : Lister tous les utilisateurs (Admin uniquement)
**Autorisation** : Admin

#### GET `/me`

**Description** : Obtenir le profil de l'utilisateur connecté

#### PUT `/me`

**Description** : Mettre à jour le profil de l'utilisateur connecté

#### GET `/search?q={query}`

**Description** : Rechercher des utilisateurs par nom ou email

#### GET `/{user_id}`

**Description** : Obtenir un utilisateur par ID

#### PUT `/{user_id}`

**Description** : Mettre à jour un utilisateur (Admin ou propriétaire)

#### DELETE `/{user_id}`

**Description** : Supprimer un utilisateur (Admin uniquement)

### 3. Notifications (`/api/notifications`)

#### GET `/`

**Description** : Obtenir les notifications de l'utilisateur
**Paramètres de requête** :

- `skip` : Nombre d'éléments à ignorer (pagination)
- `limit` : Nombre maximum d'éléments (défaut: 50)
- `unread_only` : Filtrer uniquement les non lues

#### PUT `/{notification_id}/read`

**Description** : Marquer une notification comme lue

#### PUT `/read-all`

**Description** : Marquer toutes les notifications comme lues

#### GET `/stats`

**Description** : Obtenir les statistiques des notifications

#### GET `/preferences`

**Description** : Obtenir les préférences de notification

#### PUT `/preferences`

**Description** : Mettre à jour les préférences de notification

#### POST `/`

**Description** : Créer une nouvelle notification

#### GET `/{notification_id}`

**Description** : Obtenir une notification spécifique

#### PUT `/{notification_id}`

**Description** : Mettre à jour une notification

#### DELETE `/{notification_id}`

**Description** : Supprimer une notification

### 4. Conversations (`/api/conversations`)

#### GET `/`

**Description** : Obtenir toutes les conversations de l'utilisateur

#### POST `/`

**Description** : Créer une nouvelle conversation
**Paramètres** :

```json
{
  "name": "string",
  "conversation_type": "group",
  "conversation_metadata": {},
  "participant_ids": [1, 2, 3]
}
```

#### GET `/{conversation_id}`

**Description** : Obtenir une conversation spécifique

#### PUT `/{conversation_id}`

**Description** : Mettre à jour une conversation (créateur uniquement)

#### DELETE `/{conversation_id}`

**Description** : Supprimer une conversation (créateur uniquement)

### 5. Messages (`/api/messages`)

#### GET `/conversations/{conversation_id}/messages`

**Description** : Obtenir tous les messages d'une conversation

#### POST `/conversations/{conversation_id}/messages`

**Description** : Envoyer un message dans une conversation
**Paramètres** :

```json
{
  "content": "string",
  "message_type": "text",
  "message_metadata": {}
}
```

#### GET `/messages/{message_id}`

**Description** : Obtenir un message spécifique

#### DELETE `/messages/{message_id}`

**Description** : Supprimer un message (expéditeur uniquement)

### 6. Réactions aux Messages (`/api/messages`)

#### POST `/messages/{message_id}/reactions`

**Description** : Ajouter une réaction à un message
**Paramètres** :

```json
{
  "emoji": "👍"
}
```

#### DELETE `/messages/{message_id}/reactions/{reaction_id}`

**Description** : Supprimer une réaction

#### GET `/messages/{message_id}/reactions`

**Description** : Obtenir toutes les réactions d'un message

#### GET `/messages/{message_id}/with-reactions`

**Description** : Obtenir un message avec ses réactions

### 7. Pièces Jointes (`/api/messages`)

#### POST `/send-file`

**Description** : Envoyer un fichier comme message
**Paramètres** : Form-data avec `conversation_id` et `file`

#### GET `/messages/{message_id}/download-file`

**Description** : Télécharger un fichier attaché à un message

#### GET `/messages/{message_id}/file-info`

**Description** : Obtenir les informations d'un fichier attaché

### 8. Gestion des Fichiers (`/api/files`)

#### POST `/upload`

**Description** : Télécharger un fichier (Admin uniquement)
**Paramètres** : Form-data avec `file`

#### POST `/upload-batch`

**Description** : Télécharger plusieurs fichiers (Admin uniquement)
**Paramètres** : Form-data avec `files[]`

#### GET `/`

**Description** : Lister les fichiers avec pagination
**Paramètres de requête** :

- `page` : Numéro de page (défaut: 1)
- `page_size` : Taille de page (défaut: 25, max: 100)
- `search` : Terme de recherche
- `file_type` : Type de fichier

#### GET `/{file_id}`

**Description** : Obtenir les détails d'un fichier avec prévisualisations

#### PUT `/{file_id}`

**Description** : Mettre à jour les métadonnées d'un fichier

#### DELETE `/{file_id}`

**Description** : Supprimer un fichier

#### GET `/user/{user_id}`

**Description** : Obtenir les fichiers d'un utilisateur spécifique (Admin uniquement)

### 9. Prévisualisation des Fichiers (`/api/files`)

#### GET `/{file_id}/previews`

**Description** : Obtenir les prévisualisations d'un fichier

#### POST `/{file_id}/preview`

**Description** : Générer une nouvelle prévisualisation
**Paramètres** :

```json
{
  "max_rows": 10,
  "sheet_name": "Sheet1"
}
```

#### DELETE `/{file_id}/previews/{preview_id}`

**Description** : Supprimer une prévisualisation

#### GET `/{file_id}/previews/{preview_id}/data`

**Description** : Obtenir les données de prévisualisation

### 10. Traitement des Fichiers (`/api/files`)

#### POST `/{file_id}/process`

**Description** : Démarrer le traitement d'un fichier en arrière-plan

#### GET `/{file_id}/status`

**Description** : Obtenir le statut de traitement d'un fichier

#### POST `/{file_id}/cancel-processing`

**Description** : Annuler le traitement d'un fichier

#### GET `/{file_id}/results`

**Description** : Obtenir les résultats du traitement

### 11. Gestion des Rôles (`/api/roles`)

#### GET `/roles/`

**Description** : Obtenir tous les rôles

#### GET `/roles/{role_id}`

**Description** : Obtenir un rôle par ID

#### POST `/roles/`

**Description** : Créer un nouveau rôle (Admin uniquement)

#### PUT `/roles/{role_id}`

**Description** : Mettre à jour un rôle (Admin uniquement)

#### DELETE `/roles/{role_id}`

**Description** : Supprimer un rôle (Admin uniquement)

#### GET `/roles/{role_id}/users`

**Description** : Obtenir tous les utilisateurs d'un rôle (Admin uniquement)

### 12. Gestion des Permissions (`/api/permissions`)

#### GET `/permissions/`

**Description** : Obtenir toutes les permissions

#### GET `/permissions/{permission_id}`

**Description** : Obtenir une permission par ID

#### POST `/permissions/`

**Description** : Créer une nouvelle permission (Admin uniquement)

#### PUT `/permissions/{permission_id}`

**Description** : Mettre à jour une permission (Admin uniquement)

#### DELETE `/permissions/{permission_id}`

**Description** : Supprimer une permission (Admin uniquement)

#### GET `/permissions/{permission_id}/roles`

**Description** : Obtenir tous les rôles ayant une permission (Admin uniquement)

#### POST `/permissions/bulk-create`

**Description** : Créer plusieurs permissions en une fois (Admin uniquement)

### 13. Assignation des Rôles (`/api/user-role-assignments`)

#### POST `/assign-role`

**Description** : Assigner un rôle à un utilisateur (Admin uniquement)

#### DELETE `/remove-role`

**Description** : Retirer un rôle d'un utilisateur (Admin uniquement)

#### GET `/user/{user_id}/roles`

**Description** : Obtenir les rôles d'un utilisateur

#### GET `/role/{role_id}/users`

**Description** : Obtenir les utilisateurs d'un rôle

### 14. Blocage d'Utilisateurs (`/api/blocks`)

#### POST `/`

**Description** : Bloquer un utilisateur
**Paramètres** :

```json
{
  "blocked_user_id": 1,
  "reason": "string"
}
```

#### POST `/unblock`

**Description** : Débloquer un utilisateur
**Paramètres** :

```json
{
  "blocked_user_id": 1
}
```

#### GET `/`

**Description** : Obtenir tous les utilisateurs bloqués par l'utilisateur connecté

#### GET `/blocked_users`

**Description** : Obtenir tous les utilisateurs qui ont bloqué l'utilisateur connecté

### 15. Encaissement - Upload (`/api/encaissement`)

#### POST `/upload-data`

**Description** : Télécharger et traiter des données d'encaissement
**Paramètres** : Form-data avec fichier Excel/CSV

#### POST `/validate-structure`

**Description** : Valider la structure d'un fichier avant traitement

#### GET `/template`

**Description** : Télécharger un modèle Excel pour les données d'encaissement

### 16. Encaissement - Analytics (`/api/encaissement`)

#### GET `/overview`

**Description** : Obtenir un aperçu des données d'encaissement

#### GET `/by-organisation`

**Description** : Obtenir les données groupées par organisation
**Paramètres de requête** :

- `limit` : Limite du nombre de résultats
- `sort_by` : Champ de tri (name, factures, montant, encaissement, encaisse_rate)
- `order` : Ordre de tri (asc, desc)

#### GET `/by-date`

**Description** : Obtenir les données groupées par période
**Paramètres de requête** :

- `period` : Période (day, week, month, quarter, year)

#### GET `/by-encaisse-rate`

**Description** : Obtenir les données groupées par taux d'encaissement

#### GET `/performance-metrics`

**Description** : Obtenir les indicateurs de performance clés

#### GET `/export-report`

**Description** : Exporter un rapport d'analytics
**Paramètres de requête** :

- `format` : Format d'export (excel, csv, pdf)
- `include_charts` : Inclure les graphiques

### 17. Traitement ETL (`/api/etl`)

#### POST `/encaissement/process`

**Description** : Traiter des données d'encaissement avec ETL
**Paramètres** : Form-data avec fichiers Excel/CSV (max 10 fichiers)
**Autorisation** : Admin uniquement
**Réponse** :

```json
{
  "success": true,
  "kpi_name": "encaissement",
  "duration_seconds": 45.2,
  "input_records": 1500,
  "output_records": 1450,
  "anomaly_records": 50,
  "summary_metrics": {...},
  "steps": [...],
  "output_files": [...],
  "anomaly_files": [...]
}
```

#### POST `/subscriber-park/process`

**Description** : Traiter des données de parc d'abonnés télécom
**Paramètres** : Form-data avec fichiers CSV/TSV (max 5 fichiers)
**Autorisation** : Admin uniquement
**Colonnes requises** :

- `extraction_date_date_d_extraction`
- `dot`
- `actel_code_code_d_actel`
- `customer_code_ncli`
- `service_number_nd`
- `subscriber_status_status_de_l_abonne`

#### POST `/parc-corporate-ngbss/process`

**Description** : Traiter des données Parc Corporate NGBSS d'Algérie Télécom
**Paramètres** : Form-data avec fichiers CSV/Excel (max 5 fichiers)
**Autorisation** : Admin uniquement
**Colonnes requises** :

- `dot`
- `actel_code`
- `code_customer_l2`
- `code_customer_l3`
- `subscriber_status`
- `telecom_type`
- `offer_name`

#### GET `/encaissement/results/{file_path}`

**Description** : Télécharger les résultats d'un traitement ETL
**Paramètres** :

- `file_path` : Chemin du fichier de résultat
  **Autorisation** : Admin ou Super User

#### GET `/encaissement/history`

**Description** : Obtenir l'historique des traitements ETL
**Paramètres de requête** :

- `limit` : Limite du nombre de résultats (défaut: 50)
  **Autorisation** : Admin uniquement

#### GET `/parc-corporate-ngbss/views/{result_file}`

**Description** : Obtenir différentes vues des données Parc Corporate traitées
**Paramètres** :

- `result_file` : Fichier de résultat
- `view_type` : Type de vue (overview, by_dot, by_telecom_type, by_customer_l2, by_customer_l3, preview_data)
- `dot_filter` : Filtre par DOT
- `actel_filter` : Filtre par code Actel
- `subscriber_filter` : Filtre par statut d'abonné
- `limit` : Limite des résultats (défaut: 100)
- `offset` : Décalage pour pagination (défaut: 0)
  **Autorisation** : Admin ou Super User

#### POST `/validate-etl-files`

**Description** : Valider des fichiers avant traitement ETL
**Paramètres** : Form-data avec fichiers
**Autorisation** : Admin uniquement
**Réponse** :

```json
{
  "total_files": 3,
  "valid_files": 2,
  "invalid_files": 1,
  "results": [
    {
      "filename": "data.xlsx",
      "valid": true,
      "issues": []
    }
  ]
}
```

### 18. Santé de l'Application (`/api`)

#### GET `/health`

**Description** : Vérification de santé simple

#### GET `/health/detailed`

**Description** : Vérification de santé détaillée avec base de données

#### GET `/info`

**Description** : Informations sur l'API

---

## Modèles de Données

### User (Utilisateur)

```python
{
  "id": 1,
  "username": "string",
  "email": "string",
  "hashed_password": "string",
  "first_name": "string",
  "last_name": "string",
  "is_active": true,
  "is_staff": false,
  "is_superuser": false,
  "date_joined": "2024-01-01T00:00:00Z",
  "last_login": "2024-01-01T00:00:00Z",
  "bio": "string",
  "avatar_url": "string"
}
```

### Role (Rôle)

```python
{
  "id": 1,
  "name": "admin",
  "description": "Administrateur système",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Permission (Permission)

```python
{
  "id": 1,
  "codename": "view_users",
  "name": "Voir les utilisateurs",
  "description": "Permission de visualiser la liste des utilisateurs",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Conversation (Conversation)

```python
{
  "id": 1,
  "name": "Groupe de travail",
  "conversation_type": "group",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z",
  "conversation_metadata": {},
  "participant_count": 3
}
```

### Message (Message)

```python
{
  "id": 1,
  "conversation_id": 1,
  "sender_id": 1,
  "content": "Bonjour tout le monde !",
  "message_type": "text",
  "is_edited": false,
  "is_deleted": false,
  "message_metadata": {},
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z",
  "sender_username": "user123",
  "reactions_count": 2
}
```

### Notification (Notification)

```python
{
  "id": 1,
  "user_id": 1,
  "title": "Nouveau message",
  "message": "Vous avez reçu un nouveau message",
  "notification_type": "info",
  "is_read": false,
  "data": {},
  "created_at": "2024-01-01T00:00:00Z",
  "read_at": null
}
```

### FileUpload (Téléchargement de Fichier)

```python
{
  "id": 1,
  "filename": "uuid-filename.xlsx",
  "original_filename": "data.xlsx",
  "file_path": "/uploads/excel/uuid-filename.xlsx",
  "file_size": 1024000,
  "file_type": "excel",
  "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "uploaded_by": 1,
  "is_processed": true,
  "processing_status": "completed",
  "error_message": null,
  "file_metadata": "{}",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### FilePreview (Prévisualisation de Fichier)

```python
{
  "id": 1,
  "file_upload_id": 1,
  "sheet_name": "Sheet1",
  "preview_data": "[{\"col1\": \"value1\", \"col2\": \"value2\"}]",
  "total_rows": 1000,
  "total_columns": 5,
  "preview_rows": 10,
  "created_at": "2024-01-01T00:00:00Z"
}
```

### UserBlock (Blocage d'Utilisateur)

```python
{
  "id": 1,
  "blocker_id": 1,
  "blocked_id": 2,
  "reason": "Comportement inapproprié",
  "created_at": "2024-01-01T00:00:00Z",
  "blocker_username": "user1",
  "blocked_username": "user2"
}
```

### DOT (Direction Opérationnelle Territoriale)

```python
{
  "id": 1,
  "name": "DOT ALGER",
  "description": "Direction Opérationnelle Territoriale d'Alger",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Park (Parc d'Abonnés)

```python
{
  "id": 1,
  "extraction_date": "2024-01-01",
  "dot_id": 1,
  "actel_code": "01A",
  "customer_l1_code": "L1_001",
  "customer_l1_description": "Client Niveau 1",
  "customer_l2_code": "L2_001",
  "customer_l2_description": "Client Niveau 2",
  "customer_l3_code": "L3_001",
  "customer_l3_description": "Client Niveau 3",
  "telecom_type": "Mobile",
  "offer_type": "Standard",
  "offer_name": "Offre Mobile Standard",
  "rental_fees": 1500.00,
  "customer_code": "CUST_001",
  "service_number": "0555123456",
  "related_service_number": "0555123457",
  "username": "user123",
  "subscriber_status": "Active",
  "status_date": "2024-01-01",
  "creation_date": "2023-12-01",
  "active_date": "2023-12-15",
  "csr_name": "CSR Alger",
  "department_name": "Département Mobile",
  "state": "Alger",
  "area": "Centre",
  "town": "Alger Centre",
  "grid": "GRID_001",
  "street": "Rue Didouche Mourad",
  "street_number": "123",
  "building_no": "B001",
  "unit": "U001",
  "floor": "1",
  "house_no": "H001",
  "additional_address_info": "Près de la poste",
  "customer_full_name": "Ahmed BENALI",
  "province": "Alger",
  "district": "Alger Centre",
  "city": "Alger",
  "postal_code": "16000",
  "expiry_date": "2025-01-01",
  "iccid": "ICCID123456789",
  "imsi": "IMSI123456789",
  "contact_number": "0555123456",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

---

## Services

### FileService

**Responsabilités** :

- Validation et sauvegarde des fichiers
- Traitement des fichiers Excel/CSV
- Génération de prévisualisations
- Gestion des métadonnées

**Méthodes principales** :

- `save_uploaded_file()` : Sauvegarder un fichier
- `process_excel_file()` : Traiter un fichier Excel
- `process_csv_file()` : Traiter un fichier CSV
- `get_file_previews()` : Obtenir les prévisualisations

### NotificationService

**Responsabilités** :

- Envoi de notifications en temps réel
- Gestion des préférences utilisateur
- Intégration WebSocket

**Méthodes principales** :

- `send_notification()` : Envoyer une notification
- `send_websocket_notification()` : Notification via WebSocket
- `notify_new_message()` : Notification de nouveau message
- `notify_file_uploaded()` : Notification de fichier téléchargé

### PermissionService

**Responsabilités** :

- Vérification des permissions
- Gestion des rôles
- Contrôle d'accès
- Gestion des accès aux fichiers
- Validation des permissions ETL

**Méthodes principales** :

- `check_admin_permissions()` : Vérifier les permissions admin
- `has_permission()` : Vérifier une permission spécifique
- `get_user_roles()` : Obtenir les rôles d'un utilisateur
- `require_upload_access()` : Vérifier l'accès aux uploads
- `require_admin_or_super_user()` : Vérifier les permissions admin/super user
- `check_etl_permissions()` : Vérifier les permissions ETL

### EncaissementProcessor

**Responsabilités** :

- Traitement des données d'encaissement
- Validation de la structure des données
- Calculs de taux d'encaissement
- Génération d'analytics
- Nettoyage des noms d'organisations

**Méthodes principales** :

- `validate_data_structure()` : Valider la structure
- `process_encaissement_data()` : Traiter les données
- `calculate_encaisse_rate()` : Calculer les taux
- `get_overview_data()` : Obtenir les données d'aperçu
- `clean_org_name()` : Nettoyer les noms d'organisations
- `get_by_organisation_data()` : Données groupées par organisation
- `get_by_date_data()` : Données groupées par date
- `get_encaisse_rate_data()` : Données groupées par taux d'encaissement

**Règles de nettoyage** :

- Suppression d'`AT_SIEGE`
- Remplacement de `DOT_` par chaîne vide
- Remplacement de `-` et `_` par espaces
- Suppression des lignes avec noms d'organisation vides

### ETLService

**Responsabilités** :

- Orchestration des processus ETL
- Gestion des tâches asynchrones
- Validation des données d'entrée
- Traitement des fichiers Excel/CSV
- Génération de rapports

**Méthodes principales** :

- `process_encaissement_file()` : Traiter un fichier d'encaissement
- `process_performance_kpi_file()` : Traiter un fichier de performance KPI
- `process_subscriber_park_file()` : Traiter un fichier de parc d'abonnés
- `process_parc_corporate_ngbss_file()` : Traiter un fichier Parc Corporate NGBSS
- `validate_file_structure()` : Valider la structure d'un fichier
- `get_task_status()` : Obtenir le statut d'une tâche
- `get_task_results()` : Obtenir les résultats d'une tâche
- `cancel_task()` : Annuler une tâche en cours

### ParkProcessingService

**Responsabilités** :

- Traitement des données de parc télécom
- Validation et nettoyage des données d'abonnés
- Application des règles métier Algérie Télécom
- Génération d'analytics et rapports
- Gestion des uploads de fichiers de parc

**Méthodes principales** :

- `process_park_data()` : Traiter les données de parc
- `validate_park_structure()` : Valider la structure des données
- `apply_business_rules()` : Appliquer les règles métier
- `generate_analytics()` : Générer les analytics
- `export_park_data()` : Exporter les données

### BackgroundProcessor

**Responsabilités** :

- Gestion des tâches en arrière-plan
- Traitement asynchrone des fichiers
- Suivi des tâches avec WebSocket
- Gestion des erreurs et retry
- Orchestration des processus ETL

**Méthodes principales** :

- `start_task()` : Démarrer une tâche
- `update_task_status()` : Mettre à jour le statut
- `complete_task()` : Terminer une tâche
- `fail_task()` : Marquer une tâche comme échouée
- `get_task_progress()` : Obtenir la progression

### ProcessingWebSocketManager

**Responsabilités** :

- Gestion des connexions WebSocket de traitement
- Diffusion des mises à jour de progression
- Gestion des abonnements aux tâches
- Communication temps réel avec les clients

**Méthodes principales** :

- `connect()` : Connecter un client
- `disconnect()` : Déconnecter un client
- `subscribe_to_task()` : S'abonner à une tâche
- `broadcast_update()` : Diffuser une mise à jour
- `send_progress_update()` : Envoyer une mise à jour de progression

---

## Système ETL

### Architecture ETL

Le système ETL (Extract, Transform, Load) est conçu pour traiter efficacement les données d'encaissement et de performance KPI avec une architecture modulaire et extensible.

### Classes de Base ETL

#### BaseETLProcessor

**Responsabilités** :

- Interface commune pour tous les processeurs ETL
- Gestion des tâches asynchrones
- Validation des données
- Gestion des erreurs

**Méthodes principales** :

- `validate_data()` : Validation des données
- `extract_data()` : Extraction des données
- `transform_data()` : Transformation des données
- `load_data()` : Chargement des données
- `process_async()` : Traitement asynchrone

#### BaseETLValidator

**Responsabilités** :

- Validation de la structure des fichiers
- Vérification des colonnes requises
- Validation des types de données
- Détection d'anomalies

**Méthodes principales** :

- `validate_structure()` : Validation de la structure
- `validate_columns()` : Validation des colonnes
- `validate_data_types()` : Validation des types
- `detect_anomalies()` : Détection d'anomalies

### Processeurs ETL Spécialisés

#### EncaissementETLProcessor

**Responsabilités** :

- Traitement des données d'encaissement
- Calcul des taux d'encaissement
- Validation des montants
- Génération de rapports

**Colonnes requises** :

- `Org Name` : Nom de l'organisation
- `N FACT` : Nombre de factures
- `Montant Ttc` : Montant TTC
- `Encaissement` : Montant encaissé

**Métriques calculées** :

- Taux d'encaissement par organisation
- Totaux globaux
- Évolution temporelle
- Performance vs objectifs

#### PerformanceKPIETLProcessor

**Responsabilités** :

- Traitement des données de performance KPI
- Calcul des indicateurs de performance
- Analyse comparative
- Génération de tableaux de bord

**Colonnes requises** :

- `KPI Name` : Nom de l'indicateur
- `Value` : Valeur actuelle
- `Target` : Objectif
- `Period` : Période

**Métriques calculées** :

- Écart vs objectif
- Taux de réalisation
- Évolution temporelle
- Classement des performances

#### SubscriberParkETLProcessor

**Responsabilités** :

- Traitement des données de parc d'abonnés télécom
- Nettoyage et standardisation des données d'abonnés
- Classification des services et clients
- Calcul des métriques de revenus

**Colonnes requises** :

- `extraction_date_date_d_extraction` : Date d'extraction
- `dot` : Direction Opérationnelle Territoriale
- `actel_code_code_d_actel` : Code Actel
- `customer_code_ncli` : Code client
- `service_number_nd` : Numéro de service
- `subscriber_status_status_de_l_abonne` : Statut de l'abonné

**Métriques calculées** :

- Distribution par DOT
- Classification des clients (Standard, Medium Enterprise, Large Enterprise)
- Revenus mensuels moyens
- Distribution des types de services
- Abonnés actifs vs inactifs

#### ParcCorporateNGBSSETLProcessor

**Responsabilités** :

- Traitement des données Parc Corporate NGBSS d'Algérie Télécom
- Application des règles métier spécifiques
- Mapping DOT-Actel
- Filtrage des données selon les critères d'exclusion

**Colonnes requises** :

- `dot` : Direction Opérationnelle Territoriale
- `actel_code` : Code Actel
- `code_customer_l2` : Code client niveau 2
- `code_customer_l3` : Code client niveau 3
- `subscriber_status` : Statut de l'abonné
- `telecom_type` : Type de télécom
- `offer_name` : Nom de l'offre

**Règles métier appliquées** :

- **Mapping DOT-Actel** :

  - `2B|Centre Algérie Télécom HASSI MESSAOUD` → `DOT OUARGLA`
  - `99|Grand Compte` → `DOT SIEGE`

- **Exclusions** :

  - Catégories client L3 : 5, 57
  - Statuts d'abonné : "Predeactivated"
  - Types d'offre : "Supplementary Offer"
  - Noms d'offre : "Moohtarif", "Solutions Hébergements"

**Métriques calculées** :

- Vue d'ensemble par DOT
- Distribution par type de télécom
- Analyse par niveau client (L2, L3)
- Détection d'anomalies métier

### Utilitaires ETL

#### Fonctions de Validation

- `validate_file_type()` : Validation du type de fichier
- `validate_file_size()` : Validation de la taille
- `validate_encoding()` : Validation de l'encodage
- `validate_sheet_structure()` : Validation de la structure des feuilles

#### Fonctions de Transformation

- [ ] `normalize_text()` : Normalisation du texte
- [ ] `convert_currency()` : Conversion des devises
- [ ] `parse_dates()` : Parsing des dates
- [ ] `clean_numeric_data()` : Nettoyage des données numériques

#### Fonctions de Détection d'Anomalies

- `detect_outliers()` : Détection des valeurs aberrantes
- `detect_missing_data()` : Détection des données manquantes
- `detect_duplicates()` : Détection des doublons
- `detect_inconsistencies()` : Détection des incohérences

### Gestion des Tâches ETL

#### Statuts des Tâches

- **pending** : Tâche en attente
- **processing** : Tâche en cours de traitement
- **completed** : Tâche terminée avec succès
- **failed** : Tâche échouée
- **cancelled** : Tâche annulée

#### Suivi des Tâches

- ID unique pour chaque tâche
- Horodatage de début et fin
- Progression en temps réel
- Logs détaillés des erreurs
- Résultats structurés

### Sécurité ETL

#### Contrôles d'Accès

- Seuls les administrateurs et super utilisateurs peuvent lancer des tâches ETL
- Validation des permissions avant traitement
- Audit trail complet des opérations

#### Validation des Données

- Validation stricte des types de fichiers
- Limitation de la taille des fichiers
- Sanitisation des données d'entrée
- Protection contre les injections

#### Gestion des Erreurs

- Gestion gracieuse des erreurs
- Logs détaillés pour le débogage
- Notifications en cas d'échec
- Récupération automatique quand possible

---

## WebSocket

### Connexions WebSocket

#### `/ws/notifications/?user_id={id}&token={token}`

**Description** : Connexion pour les notifications temps réel
**Paramètres** :

- `user_id` : ID de l'utilisateur
- `token` : Token JWT d'authentification

**Messages reçus** :

```json
{
  "type": "ping"
}
```

**Messages envoyés** :

```json
{
  "type": "connection",
  "message": "Connected to notifications",
  "user_id": 1,
  "timestamp": "2024-01-01T00:00:00Z"
}
```

```json
{
  "type": "notification",
  "data": {
    "id": 1,
    "title": "Nouveau message",
    "message": "Vous avez reçu un nouveau message",
    "notification_type": "info",
    "created_at": "2024-01-01T00:00:00Z",
    "is_read": false
  }
}
```

#### `/ws/chat/?conversation_id={id}&token={token}`

**Description** : Connexion pour le chat temps réel
**Paramètres** :

- `conversation_id` : ID de la conversation
- `token` : Token JWT d'authentification

**Messages reçus** :

```json
{
  "type": "message",
  "content": "Bonjour !"
}
```

**Messages envoyés** :

```json
{
  "type": "connection",
  "message": "Connected to chat",
  "conversation_id": 1,
  "user_id": 1,
  "timestamp": "2024-01-01T00:00:00Z"
}
```

```json
{
  "type": "message",
  "content": "Bonjour !",
  "user_id": 1,
  "username": "user123",
  "conversation_id": 1,
  "timestamp": "2024-01-01T00:00:00Z"
}
```

#### `/ws/processing/?user_id={id}&token={token}`

**Description** : Connexion pour les mises à jour de traitement en temps réel
**Paramètres** :

- `user_id` : ID de l'utilisateur
- `token` : Token JWT d'authentification

**Messages reçus** :

```json
{
  "type": "subscribe_task",
  "task_id": "task_123"
}
```

**Messages envoyés** :

```json
{
  "type": "connection",
  "message": "Connected to processing updates",
  "user_id": 1,
  "timestamp": "2024-01-01T00:00:00Z"
}
```

```json
{
  "type": "processing_update",
  "task_id": "task_123",
  "status": "processing",
  "progress": 45.5,
  "message": "Processing file 2 of 5"
}
```

#### `/ws/test`

**Description** : Connexion de test (sans authentification)

### WebSocket Manager

**Responsabilités** :

- Gestion des connexions actives
- Diffusion des messages
- Gestion des déconnexions

**Méthodes principales** :

- `connect()` : Établir une connexion
- `disconnect()` : Fermer une connexion
- `send_personal_message()` : Envoyer un message personnel
- `broadcast_to_conversation()` : Diffuser à une conversation

---

## Gestion des Fichiers

### Types de Fichiers Supportés

- **Excel** : .xlsx, .xls
- **CSV** : .csv

### Structure de Stockage

```
uploads/
├── excel/          # Fichiers Excel
├── csv/            # Fichiers CSV
├── temp/           # Fichiers temporaires
└── messages/       # Pièces jointes des messages
    └── {conversation_id}/
```

### Processus de Traitement

1. **Upload** : Validation et sauvegarde
2. **Prévisualisation** : Génération automatique
3. **Traitement** : En arrière-plan si nécessaire
4. **Notification** : Confirmation à l'utilisateur

### Sécurité des Fichiers

- Validation du type MIME
- Limitation de taille (100MB max)
- Noms de fichiers uniques (UUID)
- Accès restreint par utilisateur/rôle

---

## Système de Messagerie

### Types de Messages

- **text** : Message texte simple
- **file** : Message avec pièce jointe
- **image** : Message avec image
- **audio** : Message audio
- **video** : Message vidéo

### Fonctionnalités

- **Conversations** : Directes et de groupe
- **Réactions** : Emojis sur les messages
- **Pièces jointes** : Fichiers de tout type
- **Temps réel** : Via WebSocket
- **Notifications** : Automatiques pour nouveaux messages

### Contrôles d'Accès

- Seuls les participants peuvent voir les messages
- Seul l'expéditeur peut supprimer ses messages
- Les administrateurs peuvent voir toutes les conversations

---

## Notifications

### Types de Notifications

- **info** : Information générale
- **success** : Succès d'opération
- **warning** : Avertissement
- **error** : Erreur
- **message** : Nouveau message
- **file_upload** : Fichier téléchargé
- **conversation** : Nouvelle conversation

### Préférences Utilisateur

- **email_notifications** : Notifications par email
- **push_notifications** : Notifications push
- **in_app_notifications** : Notifications dans l'application
- **message_notifications** : Notifications de messages
- **system_notifications** : Notifications système

### Diffusion

- **Temps réel** : Via WebSocket
- **Persistance** : Stockage en base de données
- **Historique** : Consultation des anciennes notifications

---

## Gestion des Rôles et Permissions

### Système RBAC

- **Rôles** : Groupes de permissions
- **Permissions** : Actions spécifiques
- **Assignations** : Utilisateur ↔ Rôle

### Rôles par Défaut

- **admin** : Accès complet
- **user** : Utilisateur standard
- **moderator** : Modérateur

### Permissions Système

- **view_users** : Voir les utilisateurs
- **edit_users** : Modifier les utilisateurs
- **delete_users** : Supprimer les utilisateurs
- **manage_roles** : Gérer les rôles
- **send_messages** : Envoyer des messages
- **upload_files** : Télécharger des fichiers

### Contrôle d'Accès

- Vérification automatique sur chaque endpoint
- Middleware d'authentification
- Service de permissions centralisé

---

## Traitement des Données d'Encaissement

### Structure de Données Attendue

```csv
Org Name,N FACT,Montant Ttc,Encaissement
DOT_ALGER,100,125000.50,100000.40
DOT_ORAN,150,187500.75,150000.60
```

### Processus de Traitement

1. **Validation** : Vérification de la structure
2. **Nettoyage** : Normalisation des données
3. **Calculs** : Taux d'encaissement, totaux
4. **Analytics** : Génération de rapports

### Métriques Calculées

- **Taux d'encaissement** : (Encaissement / Montant TTC) × 100
- **Totaux par organisation**
- **Évolution temporelle**
- **Performance vs objectifs**

### Analytics Disponibles

- **Vue d'ensemble** : KPIs principaux
- **Par organisation** : Performance comparative
- **Par période** : Évolution temporelle
- **Par taux** : Distribution des performances

---

## Gestion des Parcs Télécom

### Vue d'ensemble

Le système de gestion des parcs télécom permet de traiter et analyser les données d'abonnés d'Algérie Télécom, incluant les informations sur les DOT (Directions Opérationnelles Territoriales) et les parcs d'abonnés.

### Modèles de Données

#### DOT (Direction Opérationnelle Territoriale)

```python
{
  "id": 1,
  "name": "DOT ALGER",
  "description": "Direction Opérationnelle Territoriale d'Alger",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

#### Park (Parc d'Abonnés)

```python
{
  "id": 1,
  "extraction_date": "2024-01-01",
  "dot_id": 1,
  "actel_code": "01A",
  "customer_l1_code": "L1_001",
  "customer_l1_description": "Client Niveau 1",
  "customer_l2_code": "L2_001",
  "customer_l2_description": "Client Niveau 2",
  "customer_l3_code": "L3_001",
  "customer_l3_description": "Client Niveau 3",
  "telecom_type": "Mobile",
  "offer_type": "Standard",
  "offer_name": "Offre Mobile Standard",
  "rental_fees": 1500.00,
  "customer_code": "CUST_001",
  "service_number": "0555123456",
  "related_service_number": "0555123457",
  "username": "user123",
  "subscriber_status": "Active",
  "status_date": "2024-01-01",
  "creation_date": "2023-12-01",
  "active_date": "2023-12-15",
  "csr_name": "CSR Alger",
  "department_name": "Département Mobile",
  "state": "Alger",
  "area": "Centre",
  "town": "Alger Centre",
  "grid": "GRID_001",
  "street": "Rue Didouche Mourad",
  "street_number": "123",
  "building_no": "B001",
  "unit": "U001",
  "floor": "1",
  "house_no": "H001",
  "additional_address_info": "Près de la poste",
  "customer_full_name": "Ahmed BENALI",
  "province": "Alger",
  "district": "Alger Centre",
  "city": "Alger",
  "postal_code": "16000",
  "expiry_date": "2025-01-01",
  "iccid": "ICCID123456789",
  "imsi": "IMSI123456789",
  "contact_number": "0555123456",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Endpoints API

#### GET `/api/parks/`

**Description** : Lister les parcs avec pagination et filtres
**Paramètres de requête** :

- `page` : Numéro de page (défaut: 1)
- `page_size` : Taille de page (défaut: 50, max: 1000)
- `dot_id` : Filtrer par DOT
- `telecom_type` : Filtrer par type de télécom
- `subscriber_status` : Filtrer par statut d'abonné
- `customer_l2_code` : Filtrer par code client L2
- `customer_l3_code` : Filtrer par code client L3
- `extraction_date_from` : Date d'extraction depuis
- `extraction_date_to` : Date d'extraction jusqu'à
- `search` : Recherche textuelle

#### GET `/api/parks/{park_id}`

**Description** : Obtenir un parc spécifique par ID

#### POST `/api/parks/upload`

**Description** : Télécharger et traiter des données de parc
**Paramètres** : Form-data avec fichier CSV/Excel
**Autorisation** : Admin uniquement

#### GET `/api/parks/analytics/overview`

**Description** : Obtenir un aperçu des données de parc
**Métriques** :

- Total des abonnés
- Distribution par DOT
- Distribution par type de télécom
- Distribution par statut d'abonné
- Revenus moyens

#### GET `/api/parks/analytics/by-dot`

**Description** : Obtenir les données groupées par DOT
**Paramètres de requête** :

- `limit` : Limite du nombre de résultats
- `sort_by` : Champ de tri
- `order` : Ordre de tri (asc, desc)

#### GET `/api/parks/analytics/by-telecom-type`

**Description** : Obtenir les données groupées par type de télécom

#### GET `/api/parks/analytics/by-customer-level`

**Description** : Obtenir les données groupées par niveau client (L2, L3)

#### GET `/api/parks/analytics/revenue-analysis`

**Description** : Obtenir l'analyse des revenus
**Métriques** :

- Revenus totaux par DOT
- Revenus moyens par abonné
- Distribution des revenus par type d'offre

#### GET `/api/parks/export`

**Description** : Exporter les données de parc
**Paramètres de requête** :

- `format` : Format d'export (excel, csv)
- `filters` : Filtres à appliquer
- `columns` : Colonnes à inclure

### Traitement des Données

#### Processus d'Upload

1. **Validation** : Vérification du format et de la structure
2. **Nettoyage** : Normalisation des données
3. **Mapping DOT** : Application des règles de mapping
4. **Filtrage** : Application des critères d'exclusion
5. **Enregistrement** : Sauvegarde en base de données

#### Règles de Mapping DOT

- `2B|Centre Algérie Télécom HASSI MESSAOUD (2B)` → `DOT OUARGLA`
- `99|Grand Compte` → `DOT SIEGE`

#### Critères d'Exclusion

- **Catégories client L3** : 5, 57
- **Statuts d'abonné** : "Predeactivated"
- **Types d'offre** : "Supplementary Offer"
- **Noms d'offre** : "Moohtarif", "Solutions Hébergements"

### Analytics et Rapports

#### Métriques Calculées

- **Distribution géographique** : Par DOT, province, ville
- **Classification des clients** : Standard, Medium Enterprise, Large Enterprise
- **Analyse des revenus** : Totaux, moyens, par type d'offre
- **Statuts d'abonnés** : Actifs, inactifs, en cours d'activation
- **Types de services** : Mobile, Fixe, Internet, Data

#### Vues Disponibles

- **Vue d'ensemble** : KPIs principaux
- **Par DOT** : Performance par direction
- **Par type de télécom** : Distribution des services
- **Par niveau client** : Segmentation des clients
- **Analyse des revenus** : Performance financière

---

## Système de Traitement en Arrière-plan

### Vue d'ensemble

Le système de traitement en arrière-plan est conçu pour gérer efficacement le traitement de gros volumes de données avec des performances élevées. Il utilise le multi-threading et le multi-processing pour traiter les fichiers Excel/CSV volumineux de manière asynchrone.

### Architecture du Système

#### BackgroundProcessor

**Responsabilités** :

- Traitement asynchrone de gros fichiers
- Gestion des tâches avec suivi de progression
- Traitement par chunks pour optimiser la mémoire
- Sauvegarde en base de données par lots
- Gestion des erreurs et retry automatique

**Caractéristiques** :

- **Multi-threading** : Jusqu'à 32 workers pour le traitement
- **Multi-processing** : Jusqu'à 4 processus pour les opérations CPU-intensives
- **Traitement par chunks** : 2,500 lignes par chunk pour les mises à jour de progression
- **Sauvegarde par lots** : 10,000 enregistrements par batch
- **Limite configurable** : Maximum de lignes à traiter (défaut: 10,000 pour les tests)

#### ProcessingWebSocketManager

**Responsabilités** :

- Gestion des connexions WebSocket pour les mises à jour temps réel
- Diffusion des mises à jour de progression
- Gestion des abonnements aux tâches spécifiques
- Communication temps réel avec les clients

### Endpoints de Gestion

#### POST `/api/parks/set-max-rows-limit`

**Description** : Définir la limite maximale de lignes à traiter
**Autorisation** : Admin uniquement
**Paramètres** :

```json
{
  "limit": 50000
}
```

#### POST `/api/parks/cancel-all-tasks`

**Description** : Annuler toutes les tâches de traitement actives
**Autorisation** : Admin uniquement

#### GET `/api/parks/processing-status/{task_id}`

**Description** : Obtenir le statut d'une tâche de traitement
**Réponse** :

```json
{
  "task_id": "uuid-task-id",
  "status": "processing",
  "progress": 45.5,
  "total_rows": 10000,
  "processed_rows": 4550,
  "filtered_rows": 200,
  "saved_rows": 4350,
  "errors": [],
  "anomalies": [],
  "statistics": {
    "by_dot": {...},
    "by_telecom_type": {...}
  },
  "start_time": "2024-01-01T10:00:00Z",
  "end_time": null
}
```

#### GET `/api/parks/processing-tasks`

**Description** : Obtenir toutes les tâches de traitement actives

#### POST `/api/parks/cancel-processing/{task_id}`

**Description** : Annuler une tâche de traitement spécifique

#### POST `/api/parks/cleanup-tasks`

**Description** : Nettoyer les anciennes tâches terminées
**Paramètres** :

```json
{
  "max_age_hours": 24
}
```

### Statuts des Tâches

- **pending** : Tâche en attente
- **processing** : Tâche en cours de traitement
- **completed** : Tâche terminée avec succès
- **failed** : Tâche échouée
- **cancelled** : Tâche annulée

### WebSocket de Traitement

#### Connexion

```
ws://localhost:8000/ws/processing/?user_id={id}&token={token}
```

#### Messages reçus

```json
{
  "type": "subscribe_task",
  "task_id": "uuid-task-id"
}
```

#### Messages envoyés

```json
{
  "type": "processing_update",
  "task_id": "uuid-task-id",
  "data": {
    "status": "processing",
    "progress": 45.5,
    "message": "Processing... 4550 rows processed, 4350 saved",
    "saved_count": 4350,
    "errors_count": 0,
    "statistics": {
      "total_rows": 10000,
      "processed_rows": 4550,
      "errors": 0
    }
  }
}
```

### Optimisations de Performance

#### Traitement par Chunks

- **Taille de chunk** : 2,500 lignes pour un équilibre entre mémoire et progression
- **Taille de batch** : 10,000 enregistrements pour les opérations de base de données
- **Traitement parallèle** : Multi-threading pour les opérations I/O

#### Sauvegarde en Base de Données

- **Bulk insert** : Utilisation de `pandas.to_sql()` avec `method='multi'`
- **Fallback individuel** : Sauvegarde ligne par ligne en cas d'échec
- **Commit par batches** : Commit tous les 1,000 enregistrements

#### Gestion de la Mémoire

- **Streaming** : Lecture des fichiers par chunks
- **Nettoyage automatique** : Libération de la mémoire après chaque chunk
- **Limite configurable** : Contrôle du nombre maximum de lignes traitées

### Gestion des Erreurs

#### Types d'Erreurs

- **Erreurs de fichier** : Format non supporté, fichier corrompu
- **Erreurs de données** : Données manquantes, format invalide
- **Erreurs de base de données** : Connexion perdue, contraintes violées
- **Erreurs de mémoire** : Fichier trop volumineux

#### Stratégies de Récupération

- **Retry automatique** : Nouvelle tentative pour les erreurs temporaires
- **Fallback** : Méthodes alternatives en cas d'échec
- **Logging détaillé** : Enregistrement de toutes les erreurs pour le débogage
- **Notification** : Alertes en temps réel via WebSocket

### Métriques et Statistiques

#### Métriques de Performance

- **Durée de traitement** : Temps total et par étape
- **Débit** : Lignes traitées par seconde
- **Utilisation mémoire** : Pic de mémoire utilisé
- **Taux d'erreur** : Pourcentage d'erreurs par type

#### Statistiques de Données

- **Distribution par DOT** : Nombre d'enregistrements par direction
- **Types de télécom** : Répartition des services
- **Niveaux clients** : Classification L2/L3
- **Statuts d'abonnés** : Actifs vs inactifs

### Configuration

#### Variables d'Environnement

```python
# Performance
MAX_WORKERS = 32  # Nombre de workers pour le threading
MAX_PROCESSES = 4  # Nombre de processus pour le multiprocessing
CHUNK_SIZE = 2500  # Taille des chunks de traitement
BATCH_SIZE = 10000  # Taille des batches de sauvegarde
MAX_ROWS_LIMIT = 10000  # Limite de lignes pour les tests
```

#### Paramètres de Base de Données

```python
# Pool de connexions haute performance
POOL_SIZE = 20
MAX_OVERFLOW = 30
POOL_PRE_PING = True
POOL_RECYCLE = 300
```

---

## Système ETL (Extract, Transform, Load)

### Vue d'ensemble

Le système ETL est conçu pour traiter et transformer les données de différentes sources (Encaissement, Parc d'Abonnés, Parc Corporate NGBSS) selon des règles métier spécifiques à Algérie Télécom. Il suit une architecture modulaire avec des étapes standardisées.

### Architecture ETL

#### BaseETLProcessor

**Classe de base** pour tous les processeurs ETL avec :

- **Étapes standardisées** : Ingestion, Nettoyage, Validation, Transformation, Détection d'anomalies, Génération de vues
- **Gestion des erreurs** : Suivi détaillé des erreurs et warnings
- **Métriques** : Temps d'exécution, nombre d'enregistrements traités
- **Limitation** : Possibilité de limiter le nombre de lignes pour les tests

#### Types d'Étapes ETL

```python
class ETLStepType(str, Enum):
    INGEST = "ingest"
    CLEAN = "clean"
    VALIDATE = "validate"
    TRANSFORM = "transform"
    ANOMALY_DETECTION = "anomaly_detection"
    OUTPUT = "output"
    VIEW_GENERATION = "view_generation"
```

### Processeurs ETL Spécialisés

#### EncaissementETL

**Objectif** : Traitement des données d'encaissement avec calcul de KPIs

**Étapes** :

1. **Ingestion** : Lecture des fichiers Excel/CSV
2. **Nettoyage** : Standardisation des noms d'organisations
3. **Validation** : Vérification de la cohérence des données
4. **Transformation** : Calcul des taux d'encaissement
5. **Détection d'anomalies** : Identification des valeurs aberrantes
6. **Génération de vues** : Création de vues analytiques

**Règles métier** :

- Nettoyage des noms d'organisations (suppression "AT*SIEGE", "DOT*")
- Calcul des taux d'encaissement par organisation
- Détection des anomalies de montants

#### SubscriberParkETL

**Objectif** : Traitement des données du parc d'abonnés

**Étapes** :

1. **Ingestion** : Lecture des fichiers CSV/TSV
2. **Nettoyage** : Standardisation des codes DOT, Actel, clients
3. **Validation** : Vérification des formats de numéros de service
4. **Transformation** : Ajout de champs dérivés (catégorie client, type de service)
5. **Détection d'anomalies** : Identification des données incohérentes

**Règles métier** :

- Résolution des DOTs à partir des codes Actel
- Catégorisation des codes clients (Corporate, Particulier, etc.)
- Classification des types de services
- Validation des numéros de service

#### ParcCorporateNGBSSETL

**Objectif** : Traitement des données du parc corporate NGBSS avec règles spécifiques Algérie Télécom

**Étapes** :

1. **Ingestion** : Lecture et standardisation des colonnes
2. **Nettoyage** : Nettoyage des champs texte et conversion des codes
3. **Application des règles métier** : Mapping DOT-Actel spécifique
4. **Filtrage** : Exclusion des catégories non pertinentes
5. **Détection d'anomalies** : Identification des patterns suspects
6. **Génération de vues** : Création de vues analytiques détaillées

**Règles métier spécifiques** :

- **Mapping DOT-Actel** : Correspondance précise entre codes Actel et DOTs
- **Exclusions** : Filtrage des catégories clients, statuts, offres non pertinents
- **Détection d'anomalies** : Identification des patterns "Moohtarif" et autres anomalies

### Endpoints ETL

#### POST `/api/etl/encaissement/process`

**Description** : Traitement des fichiers d'encaissement
**Autorisation** : Admin uniquement
**Paramètres** :

```json
{
  "file_path": "uploads/encaissement_2024.xlsx",
  "limit_rows": 10000
}
```

**Réponse** :

```json
{
  "success": true,
  "duration": 45.2,
  "input_count": 10000,
  "output_count": 9500,
  "steps": [
    {
      "step_type": "ingest",
      "status": "completed",
      "duration": 2.1,
      "records_processed": 10000,
      "warnings": [],
      "errors": []
    }
  ],
  "anomalies": [],
  "summary_metrics": {
    "total_organizations": 150,
    "total_invoices": 9500,
    "total_amount": 2500000.0,
    "average_encaisse_rate": 85.5
  }
}
```

#### POST `/api/etl/subscriber-park/process`

**Description** : Traitement des fichiers du parc d'abonnés
**Autorisation** : Admin uniquement

#### POST `/api/etl/parc-corporate-ngbss/process`

**Description** : Traitement des fichiers Parc Corporate NGBSS
**Autorisation** : Admin uniquement

#### GET `/api/etl/encaissement/results/{file_path:path}`

**Description** : Téléchargement des résultats ETL
**Autorisation** : Admin ou Super User

#### GET `/api/etl/parc-corporate-ngbss/views/{result_file:path}`

**Description** : Accès aux vues analytiques des données traitées
**Paramètres de requête** :

- `view_type` : overview, by_dot, by_telecom_type, by_customer_l2, by_customer_l3, preview_data
- `page` : Numéro de page (défaut: 1)
- `size` : Taille de page (défaut: 100)
- `filters` : Filtres JSON pour les données

**Exemple de réponse** :

```json
{
  "view_type": "overview",
  "data": {
    "total_records": 50000,
    "by_dot": {
      "DOT OUARGLA": 15000,
      "DOT SIEGE": 20000
    },
    "by_telecom_type": {
      "FIXE": 30000,
      "MOBILE": 20000
    }
  },
  "pagination": {
    "page": 1,
    "size": 100,
    "total_pages": 500
  }
}
```

#### POST `/api/etl/validate-etl-files`

**Description** : Validation des fichiers avant traitement ETL
**Paramètres** :

```json
{
  "files": [
    {
      "filename": "data.xlsx",
      "file_size": 1024000,
      "file_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    }
  ]
}
```

### Gestion des Erreurs ETL

#### Types d'Erreurs

- **Erreurs d'ingestion** : Fichier non trouvé, format non supporté
- **Erreurs de validation** : Colonnes manquantes, types incorrects
- **Erreurs de transformation** : Données incohérentes, calculs impossibles
- **Erreurs de sauvegarde** : Problèmes de base de données

#### Stratégies de Récupération

- **Validation préalable** : Vérification des fichiers avant traitement
- **Traitement par chunks** : Isolation des erreurs par lot
- **Logging détaillé** : Enregistrement de toutes les erreurs
- **Notifications** : Alertes en temps réel via WebSocket

### Métriques et Monitoring

#### Métriques de Performance

- **Durée totale** : Temps d'exécution complet
- **Durée par étape** : Temps d'exécution de chaque étape
- **Débit** : Enregistrements traités par seconde
- **Taux de succès** : Pourcentage d'enregistrements traités avec succès

#### Métriques de Qualité

- **Taux d'anomalies** : Pourcentage d'enregistrements avec anomalies
- **Taux d'erreurs** : Pourcentage d'erreurs par type
- **Complétude** : Pourcentage de champs remplis
- **Cohérence** : Validation des règles métier

### Configuration ETL

#### Variables d'Environnement

```python
# ETL Configuration
ETL_CHUNK_SIZE = 2500
ETL_BATCH_SIZE = 10000
ETL_MAX_ROWS_LIMIT = 100000
ETL_TIMEOUT = 3600  # 1 heure
```

#### Règles Métier Configurables

```python
# Mapping DOT-Actel (exemple)
DOT_ACTEL_MAPPING = {
    "HASSI MESSAOUD": "DOT OUARGLA",
    "OUARGLA": "DOT OUARGLA",
    "SIEGE": "DOT SIEGE"
}

# Exclusions configurables
EXCLUDED_CUSTOMER_L3 = ["EXCLUDED_CATEGORY"]
EXCLUDED_SUBSCRIBER_STATUS = ["INACTIVE", "SUSPENDED"]
```

---

## Système d'Analytics et de Reporting

### Vue d'ensemble

Le système d'analytics et de reporting fournit des vues détaillées et des métriques de performance pour les données traitées. Il inclut des endpoints spécialisés pour l'encaissement et le parc d'abonnés avec des capacités de filtrage, de tri et d'export.

### Analytics Encaissement

#### GET `/api/encaissement-analytics/overview`

**Description** : Vue d'ensemble des données d'encaissement
**Autorisation** : DOT_USER minimum
**Réponse** :

```json
{
  "total_organizations": 150,
  "total_invoices": 50000,
  "total_amount": 25000000.0,
  "average_encaisse_rate": 85.5,
  "period_range": {
    "start_date": "2024-01-01",
    "end_date": "2024-12-31"
  },
  "top_performers": [
    {
      "organization": "DOT OUARGLA",
      "encaisse_rate": 92.3,
      "total_amount": 5000000.0
    }
  ]
}
```

#### GET `/api/encaissement-analytics/by-organisation`

**Description** : Données groupées par organisation avec filtrage
**Paramètres de requête** :

- `sort_by` : encaisse_rate, total_amount, invoice_count
- `sort_order` : asc, desc
- `limit` : Nombre de résultats (défaut: 100)
- `filters` : Filtres JSON

**Réponse** :

```json
{
  "organizations": [
    {
      "organization": "DOT OUARGLA",
      "invoice_count": 15000,
      "total_amount": 7500000.0,
      "encaisse_rate": 92.3,
      "performance_trend": "improving"
    }
  ],
  "pagination": {
    "page": 1,
    "size": 100,
    "total": 150
  }
}
```

#### GET `/api/encaissement-analytics/by-date`

**Description** : Données groupées par période temporelle
**Paramètres de requête** :

- `group_by` : day, week, month, quarter, year
- `start_date` : Date de début
- `end_date` : Date de fin

#### GET `/api/encaissement-analytics/by-encaisse-rate`

**Description** : Distribution des taux d'encaissement
**Réponse** :

```json
{
  "rate_buckets": [
    {
      "range": "90-100%",
      "count": 45,
      "percentage": 30.0
    },
    {
      "range": "80-90%",
      "count": 60,
      "percentage": 40.0
    }
  ]
}
```

#### GET `/api/encaissement-analytics/performance-metrics`

**Description** : Métriques de performance clés
**Autorisation** : DOT_USER minimum
**Réponse** :

```json
{
  "kpis": {
    "overall_encaisse_rate": 85.5,
    "target_achievement": 95.2,
    "month_over_month_growth": 2.3,
    "top_performing_dot": "DOT OUARGLA",
    "areas_for_improvement": ["DOT SIEGE", "DOT ALGER"]
  },
  "trends": {
    "encaisse_rate_trend": "improving",
    "volume_trend": "stable",
    "revenue_trend": "growing"
  }
}
```

#### GET `/api/encaissement-analytics/export-report`

**Description** : Export des rapports d'analytics
**Autorisation** : Admin ou Super User
**Paramètres de requête** :

- `format` : excel, csv, pdf
- `report_type` : overview, detailed, performance
- `filters` : Filtres à appliquer

### Analytics Parc d'Abonnés

#### GET `/api/parks/analytics/overview`

**Description** : Vue d'ensemble du parc d'abonnés
**Réponse** :

```json
{
  "total_subscribers": 100000,
  "active_subscribers": 85000,
  "by_telecom_type": {
    "FIXE": 60000,
    "MOBILE": 40000
  },
  "by_dot": {
    "DOT OUARGLA": 40000,
    "DOT SIEGE": 60000
  },
  "revenue_summary": {
    "total_monthly_revenue": 5000000.0,
    "average_revenue_per_subscriber": 50.0
  }
}
```

#### GET `/api/parks/analytics/by-dot`

**Description** : Analytics par direction opérationnelle
**Paramètres de requête** :

- `dot_id` : ID de la DOT (optionnel)
- `include_details` : Inclure les détails (booléen)

**Réponse** :

```json
{
  "dots": [
    {
      "dot_id": 1,
      "dot_name": "DOT OUARGLA",
      "subscriber_count": 40000,
      "active_count": 35000,
      "revenue": 2000000.0,
      "growth_rate": 5.2
    }
  ]
}
```

#### GET `/api/parks/analytics/by-telecom-type`

**Description** : Analytics par type de télécom
**Réponse** :

```json
{
  "telecom_types": [
    {
      "type": "FIXE",
      "subscriber_count": 60000,
      "revenue": 3000000.0,
      "market_share": 60.0
    },
    {
      "type": "MOBILE",
      "subscriber_count": 40000,
      "revenue": 2000000.0,
      "market_share": 40.0
    }
  ]
}
```

#### GET `/api/parks/analytics/by-customer-l2`

**Description** : Analytics par niveau client L2
**Réponse** :

```json
{
  "customer_l2": [
    {
      "level": "CORPORATE",
      "subscriber_count": 30000,
      "revenue": 2500000.0,
      "average_revenue": 83.33
    },
    {
      "level": "PARTICULIER",
      "subscriber_count": 70000,
      "revenue": 2500000.0,
      "average_revenue": 35.71
    }
  ]
}
```

#### GET `/api/parks/analytics/by-customer-l3`

**Description** : Analytics par niveau client L3
**Réponse** :

```json
{
  "customer_l3": [
    {
      "level": "GRAND_COMPTE",
      "subscriber_count": 5000,
      "revenue": 1000000.0,
      "average_revenue": 200.0
    },
    {
      "level": "PME",
      "subscriber_count": 25000,
      "revenue": 1500000.0,
      "average_revenue": 60.0
    }
  ]
}
```

### Système de Filtrage Avancé

#### GET `/api/parks/filters/options`

**Description** : Obtenir les options de filtrage disponibles
**Réponse** :

```json
{
  "dots": [
    { "id": 1, "name": "DOT OUARGLA" },
    { "id": 2, "name": "DOT SIEGE" }
  ],
  "telecom_types": ["FIXE", "MOBILE"],
  "customer_l2": ["CORPORATE", "PARTICULIER"],
  "customer_l3": ["GRAND_COMPTE", "PME", "PARTICULIER"],
  "offer_types": ["INTERNET", "VOICE", "DATA"],
  "statuses": ["ACTIVE", "INACTIVE", "SUSPENDED"]
}
```

#### GET `/api/parks/filtered`

**Description** : Données filtrées avec pagination
**Paramètres de requête** :

- `search` : Recherche textuelle
- `dot_id` : Filtre par DOT
- `telecom_type` : Filtre par type de télécom
- `customer_l2` : Filtre par niveau client L2
- `customer_l3` : Filtre par niveau client L3
- `offer_type` : Filtre par type d'offre
- `status` : Filtre par statut
- `page` : Numéro de page
- `size` : Taille de page
- `sort_by` : Champ de tri
- `sort_order` : Ordre de tri (asc/desc)

**Réponse** :

```json
{
  "data": [
    {
      "id": 1,
      "service_number": "1234567890",
      "dot_name": "DOT OUARGLA",
      "telecom_type": "FIXE",
      "customer_l2": "CORPORATE",
      "customer_l3": "PME",
      "offer_type": "INTERNET",
      "status": "ACTIVE",
      "monthly_fee": 100.0
    }
  ],
  "pagination": {
    "page": 1,
    "size": 100,
    "total": 100000,
    "total_pages": 1000
  },
  "filters_applied": {
    "dot_id": 1,
    "telecom_type": "FIXE"
  }
}
```

### Statistiques et Métriques

#### GET `/api/parks/data/stats`

**Description** : Statistiques détaillées des données sauvegardées
**Réponse** :

```json
{
  "total_records": 100000,
  "by_dot": {
    "DOT OUARGLA": 40000,
    "DOT SIEGE": 60000
  },
  "by_telecom_type": {
    "FIXE": 60000,
    "MOBILE": 40000
  },
  "by_status": {
    "ACTIVE": 85000,
    "INACTIVE": 10000,
    "SUSPENDED": 5000
  },
  "revenue_metrics": {
    "total_monthly_revenue": 5000000.0,
    "average_revenue_per_subscriber": 50.0,
    "revenue_by_dot": {
      "DOT OUARGLA": 2000000.0,
      "DOT SIEGE": 3000000.0
    }
  }
}
```

#### GET `/api/parks/stats/summary`

**Description** : Résumé des statistiques du parc
**Réponse** :

```json
{
  "summary": {
    "total_subscribers": 100000,
    "active_subscribers": 85000,
    "total_dots": 2,
    "total_revenue": 5000000.0,
    "last_updated": "2024-01-01T10:00:00Z"
  },
  "growth_metrics": {
    "month_over_month_growth": 2.3,
    "year_over_year_growth": 15.7,
    "churn_rate": 2.1
  }
}
```

### Export et Reporting

#### Fonctionnalités d'Export

- **Formats supportés** : Excel, CSV, PDF
- **Filtrage** : Export des données filtrées
- **Pagination** : Export par lots pour les gros volumes
- **Templates** : Modèles de rapports prédéfinis

#### Types de Rapports

- **Rapport d'overview** : Vue d'ensemble des métriques clés
- **Rapport détaillé** : Données complètes avec filtres
- **Rapport de performance** : Métriques de performance et tendances
- **Rapport personnalisé** : Rapports avec filtres spécifiques

### Configuration Analytics

#### Variables d'Environnement

```python
# Analytics Configuration
ANALYTICS_CACHE_TTL = 3600  # 1 heure
ANALYTICS_MAX_RESULTS = 10000
ANALYTICS_EXPORT_LIMIT = 100000
ANALYTICS_REAL_TIME_UPDATES = True
```

#### Paramètres de Performance

```python
# Optimisations
ANALYTICS_USE_CACHE = True
ANALYTICS_BATCH_SIZE = 1000
ANALYTICS_PARALLEL_PROCESSING = True
ANALYTICS_INDEX_OPTIMIZATION = True
```

---

## Sécurité

### Authentification

- **JWT Tokens** : Sécurisés avec secret
- **Expiration** : Tokens avec durée de vie limitée
- **Refresh** : Renouvellement automatique

### Autorisation

- **RBAC** : Contrôle d'accès basé sur les rôles
- **Permissions granulaires** : Actions spécifiques
- **Vérification systématique** : Sur chaque endpoint

### Protection des Données

- **Hachage des mots de passe** : bcrypt
- **Validation des entrées** : Pydantic
- **Sanitisation** : Nettoyage des données

### Limitation du Taux

- **Login** : 5 tentatives par minute
- **Register** : 3 inscriptions par minute
- **Général** : 100 requêtes par heure (anonymes)

### Sécurité des Fichiers

- **Validation du type** : Vérification MIME
- **Taille limitée** : 100MB maximum
- **Stockage sécurisé** : Chemins uniques
- **Accès contrôlé** : Par utilisateur/rôle

---

## Déploiement

### Prérequis

- **Python 3.8+**
- **PostgreSQL 12+**
- **Redis** (pour le cache et WebSocket)
- **Alembic** (pour les migrations)

### Installation

```bash
# Cloner le projet
git clone <repository>
cd fastapi_backend

# Installer les dépendances
pip install -r requirements.txt

# Dépendances principales :
# - FastAPI 0.104.1
# - SQLAlchemy 2.0.23
# - PostgreSQL (psycopg2-binary 2.9.9)
# - Redis (redis 5.0.1)
# - Pandas 2.1.4 (traitement de données)
# - OpenPyXL 3.1.2 (fichiers Excel)
# - JWT (python-jose 3.3.0)
# - WebSocket (websockets 12.0)

# Configurer la base de données
# Créer la base PostgreSQL
# Configurer les variables d'environnement

# Exécuter les migrations
alembic upgrade head

# Démarrer l'application
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Variables d'Environnement

```bash
# Base de données
DATABASE_URL=postgresql://user:password@localhost:5432/youcef_db

# Sécurité
SECRET_KEY=your-very-secure-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Application
DEBUG=False
HOST=0.0.0.0
PORT=8000
```

### Docker (Optionnel)

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Monitoring

- **Logs** : Fichiers de log détaillés
- **Santé** : Endpoints de vérification
- **Métriques** : Performance et utilisation

---

## Conclusion

Le backend FastAPI Youcef est une solution complète et robuste pour la gestion d'applications modernes avec :

- **API REST complète** avec documentation automatique
- **Communication temps réel** via WebSocket (notifications, chat, traitement)
- **Système de sécurité avancé** avec RBAC
- **Gestion des fichiers** avec prévisualisation et traitement asynchrone
- **Messagerie intégrée** avec notifications et réactions
- **Système ETL complet** pour le traitement de données
- **Traitement de données** spécialisé pour les encaissements et KPI
- **Gestion des parcs télécom** avec modèles DOT et Park
- **Traitement des données Algérie Télécom** (NGBSS, Parc Corporate)
- **Système de blocage d'utilisateurs**
- **Architecture modulaire** et extensible
- **Traitement asynchrone** des tâches lourdes avec WebSocket
- **Détection d'anomalies** automatique
- **Validation robuste** des données
- **Support PostgreSQL** avec migrations Alembic

### Nouvelles Fonctionnalités ETL

- **Processeurs ETL modulaires** pour différents types de données :
  - **EncaissementETL** : Traitement des données d'encaissement
  - **PerformanceKPIETL** : Traitement des indicateurs de performance
  - **SubscriberParkETL** : Traitement des données de parc d'abonnés télécom
  - **ParcCorporateNGBSSETL** : Traitement des données Parc Corporate NGBSS
- **Validation automatique** de la structure des fichiers
- **Détection d'anomalies** en temps réel avec règles métier
- **Traitement asynchrone** avec suivi des tâches via WebSocket
- **Gestion des erreurs** robuste avec logs détaillés
- **Sécurité renforcée** avec contrôles d'accès granulaires
- **Règles métier intégrées** pour Algérie Télécom
- **Mapping automatique** DOT-Actel
- **Filtrage intelligent** selon critères d'exclusion
- **Vues multiples** des données traitées avec pagination
- **Validation préalable** des fichiers avant traitement

### Nouvelles Fonctionnalités Système

- **Gestion des parcs télécom** avec modèles DOT et Park complets
- **Système de blocage d'utilisateurs** avec gestion des relations
- **WebSocket de traitement** pour les mises à jour en temps réel
- **Traitement asynchrone** avec background processor
- **Support PostgreSQL** avec migrations Alembic
- **Système de notifications** avec préférences utilisateur
- **Messagerie avancée** avec réactions et pièces jointes
- **Gestion des rôles et permissions** complète
- **Analytics avancées** pour les données d'encaissement et parcs
- **Export de données** en multiple formats

### Règles Métier Algérie Télécom

Le système intègre des règles métier spécifiques pour le traitement des données d'Algérie Télécom :

#### Mapping DOT-Actel

- `2B|Centre Algérie Télécom HASSI MESSAOUD (2B)` → `DOT OUARGLA`
- `99|Grand Compte` → `DOT SIEGE`

#### Critères d'Exclusion Parc Corporate

- **Catégories client L3** : 5, 57
- **Statuts d'abonné** : "Predeactivated"
- **Types d'offre** : "Supplementary Offer"
- **Noms d'offre** : "Moohtarif", "Solutions Hébergements"

#### Classification des Clients

- **Standard Customer** : Codes < 7e12
- **Medium Enterprise** : Codes 7e12 - 7e13
- **Large Enterprise** : Codes ≥ 7e13

#### Types de Services Télécom

- **Fixed Line** : PSTN
- **Mobile** : Mobile, GSM
- **Internet** : Internet, ADSL
- **Data Services** : Data
- **Other** : Autres types

Cette documentation couvre tous les aspects techniques nécessaires pour comprendre, utiliser et maintenir le système, y compris les nouvelles fonctionnalités ETL avancées et les règles métier spécifiques à Algérie Télécom.
