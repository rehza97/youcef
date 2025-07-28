# 🚀 Backend System Documentation

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Project Structure](#project-structure)
4. [Core Applications](#core-applications)
5. [API Endpoints](#api-endpoints)
6. [Security Features](#security-features)
7. [Database Configuration](#database-configuration)
8. [Real-time Features](#real-time-features)
9. [Performance & Caching](#performance--caching)
10. [Development Setup](#development-setup)
11. [Deployment](#deployment)
12. [Troubleshooting](#troubleshooting)

---

## 🏗️ System Overview

The backend is built using **Django 5.0.2** with a comprehensive API-first architecture designed for modern web applications. It features real-time communication, role-based access control, and scalable architecture.

### 🎯 Key Features

- **REST API** with Django REST Framework
- **Real-time WebSocket** support via Django Channels
- **Role-Based Access Control (RBAC)** system
- **Token-based Authentication** with security features
- **CORS** configuration for frontend integration
- **Rate limiting** and security protection
- **Multi-database** support (SQLite/PostgreSQL)
- **Real-time messaging** and notifications

---

## 🏛️ Architecture

### Technology Stack

| Component          | Technology                       | Version |
| ------------------ | -------------------------------- | ------- |
| **Framework**      | Django                           | 5.0.2   |
| **API**            | Django REST Framework            | 3.15.1  |
| **Real-time**      | Django Channels                  | 4.0.0   |
| **Database**       | SQLite (dev) / PostgreSQL (prod) | -       |
| **Caching**        | Redis                            | 5.0.1   |
| **Authentication** | Token-based                      | -       |
| **CORS**           | django-cors-headers              | 4.3.1   |

### System Architecture Diagram

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   Database      │
│   (React/Vite)  │◄──►│   (Django)      │◄──►│   (SQLite/PG)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   WebSocket     │
                       │   (Channels)    │
                       └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   Redis Cache   │
                       └─────────────────┘
```

---

## 📁 Project Structure

```
backend/
├── backend/                     # Main Django project
│   ├── __init__.py
│   ├── settings.py             # Configuration & CORS settings
│   ├── urls.py                # Main URL routing
│   ├── asgi.py                # ASGI for WebSocket support
│   ├── wsgi.py                # WSGI for HTTP
│   └── routing.py             # WebSocket routing
├── api/                        # Core API application
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── views.py               # Authentication & core endpoints
│   ├── urls.py                # API URL patterns
│   ├── test_cors_view.py      # CORS testing endpoint
│   └── migrations/
├── users/                      # User management app
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py              # User & Role models
│   ├── views.py               # User management endpoints
│   ├── urls.py                # User URL patterns
│   └── migrations/
├── notifications/              # Notification system
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py              # Notification models
│   ├── views.py               # Notification endpoints
│   ├── urls.py                # Notification URL patterns
│   └── migrations/
├── messaging/                  # Real-time messaging
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py              # Message & Conversation models
│   ├── views.py               # Messaging endpoints
│   ├── urls.py                # Messaging URL patterns
│   └── migrations/
├── manage.py                   # Django management
├── requirements.txt            # Dependencies
├── db.sqlite3                 # SQLite database
├── django.log                 # Application logs
├── run_server.py              # Development server script
├── run_https_server.py        # HTTPS development server
├── start_http_server.py       # HTTP server with custom settings
├── test_cors_detailed.py      # CORS testing script
├── test_working.py            # Working test script
├── test_fixes.py              # Fixes test script
├── test_final.py              # Final test script
├── test_api.py                # API testing script
├── simple_server.py           # Simple server script
├── routing.py                 # WebSocket routing
└── SERVER_SETUP.md           # Server setup documentation
```

---

## 🔧 Core Applications

### 1. API Application (`api/`)

The core API application handles authentication, health checks, and system information.

#### **Key Features:**

- **Authentication endpoints** (login, register, logout)
- **Token management** and refresh
- **Rate limiting** for security
- **Health monitoring** and system info
- **CORS testing** endpoints

#### **Rate Limiting Configuration:**

```python
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'login': '5/minute',
        'register': '3/minute',
    }
}
```

### 2. Users Application (`users/`)

Manages user accounts, roles, and permissions with a comprehensive RBAC system.

#### **Key Features:**

- **User management** and profiles
- **Role-based access control** (RBAC)
- **Permission system** with granular control
- **Role assignment** and management
- **Permission checking** endpoints

### 3. Notifications Application (`notifications/`)

Handles real-time notifications with WebSocket support.

#### **Key Features:**

- **Real-time notifications** via WebSocket
- **Notification preferences** management
- **Read status tracking**
- **Notification statistics**
- **Multi-channel delivery**

### 4. Messaging Application (`messaging/`)

Provides real-time messaging capabilities with advanced features.

#### **Key Features:**

- **Real-time messaging** via WebSocket
- **Conversation management**
- **Message reactions** and emojis
- **User blocking** functionality
- **File sharing** support
- **Message history** persistence

---

## 📡 API Endpoints

### Authentication Endpoints

| Method | Endpoint              | Description             | Rate Limit |
| ------ | --------------------- | ----------------------- | ---------- |
| `POST` | `/api/register/`      | User registration       | 3/minute   |
| `POST` | `/api/login/`         | User login              | 5/minute   |
| `POST` | `/api/logout/`        | User logout             | -          |
| `POST` | `/api/refresh-token/` | Token refresh           | -          |
| `GET`  | `/api/health/`        | Health check            | -          |
| `GET`  | `/api/info/`          | API information         | -          |
| `GET`  | `/api/protected/`     | Protected endpoint test | -          |
| `GET`  | `/api/test-cors/`     | CORS testing            | -          |

### User Management Endpoints

| Method | Endpoint                                | Description             |
| ------ | --------------------------------------- | ----------------------- |
| `GET`  | `/users/users/`                         | List all users          |
| `GET`  | `/users/roles/`                         | List all roles          |
| `GET`  | `/users/permissions/`                   | List all permissions    |
| `POST` | `/users/permissions/`                   | Create permission       |
| `POST` | `/users/assign-role/`                   | Assign role to user     |
| `GET`  | `/users/check-role/{role_name}/`        | Check user role         |
| `GET`  | `/users/check-permission/{codename}/`   | Check user permission   |
| `POST` | `/users/roles/{id}/update-permissions/` | Update role permissions |

### Notification Endpoints

| Method | Endpoint                                              | Description            |
| ------ | ----------------------------------------------------- | ---------------------- |
| `GET`  | `/api/notifications/notifications/`                   | Get notifications      |
| `POST` | `/api/notifications/notifications/{id}/mark_as_read/` | Mark as read           |
| `POST` | `/api/notifications/notifications/mark_all_as_read/`  | Mark all as read       |
| `POST` | `/api/notifications/preferences/update_preferences/`  | Update preferences     |
| `GET`  | `/api/notifications/notifications/stats/`             | Get notification stats |

### Messaging Endpoints

| Method | Endpoint                                      | Description         |
| ------ | --------------------------------------------- | ------------------- |
| `GET`  | `/api/messaging/conversations/`               | Get conversations   |
| `GET`  | `/api/messaging/conversations/{id}/messages/` | Get messages        |
| `POST` | `/api/messaging/conversations/{id}/messages/` | Send message        |
| `POST` | `/api/messaging/conversations/`               | Create conversation |
| `POST` | `/api/messaging/messages/{id}/react/`         | Add reaction        |
| `POST` | `/api/messaging/blocks/`                      | Block user          |
| `POST` | `/api/messaging/blocks/unblock/`              | Unblock user        |
| `GET`  | `/api/messaging/blocks/blocked_users/`        | Get blocked users   |
| `POST` | `/api/messaging/send-multi/`                  | Send multi-message  |

### WebSocket Endpoints

| Endpoint                                          | Description             |
| ------------------------------------------------- | ----------------------- |
| `ws://localhost:8000/ws/notifications/{user_id}/` | Real-time notifications |
| `ws://localhost:8000/ws/chat/{conversation_id}/`  | Real-time messaging     |

---

## 🔒 Security Features

### CORS Configuration

```python
# Development CORS settings
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
    CORS_ALLOW_ALL_HEADERS = True
    CORS_ALLOW_ALL_METHODS = True
    CORS_ALLOWED_ORIGIN_REGEXES = [
        r"^http://localhost:\d+$",
        r"^http://127\.0\.0\.1:\d+$",
    ]
```

### CSRF Protection

```python
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
]
```

### Authentication Security

- **Token-based authentication** with secure token management
- **Session management** with configurable settings
- **Password validation** with strong requirements
- **Rate limiting** to prevent brute force attacks
- **Input sanitization** and XSS protection

### Security Headers

```python
# Development security settings
if DEBUG:
    SECURE_SSL_REDIRECT = False
    SECURE_HSTS_SECONDS = 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
```

---

## 🗄️ Database Configuration

### Development (SQLite)

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
```

### Production (PostgreSQL)

```python
# Automatic PostgreSQL detection and configuration
# Requires PostgreSQL 14+ for Django 5.0 compatibility
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'youcef_db'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', '123456789'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}
```

### Database Models

#### User Models

- **User**: Extended user model with additional fields
- **Role**: Role-based access control
- **Permission**: Granular permission system

#### Notification Models

- **Notification**: Notification content and metadata
- **NotificationPreference**: User notification preferences

#### Messaging Models

- **Conversation**: Chat conversations
- **Message**: Individual messages
- **MessageReaction**: Message reactions
- **UserBlock**: User blocking system

---

## 📡 Real-time Features

### Django Channels Configuration

```python
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer" if DEBUG else "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [os.environ.get('REDIS_URL', 'redis://localhost:6379')],
        } if not DEBUG else {},
    }
}
```

### WebSocket Consumers

#### Notification Consumer

- **Real-time notifications** delivery
- **User-specific** notification channels
- **Automatic reconnection** handling

#### Chat Consumer

- **Real-time messaging** in conversations
- **Message broadcasting** to participants
- **Typing indicators** and status updates

### WebSocket Routing

```python
# routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/notifications/(?P<user_id>\w+)/$', consumers.NotificationConsumer.as_asgi()),
    re_path(r'ws/chat/(?P<conversation_id>\w+)/$', consumers.ChatConsumer.as_asgi()),
]
```

---

## ⚡ Performance & Caching

### Redis Caching Configuration

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache' if not DEBUG else 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
    }
}
```

### File Upload Settings

```python
FILE_UPLOAD_MAX_MEMORY_SIZE = 1000 * 1024 * 1024  # 1000MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 1000 * 1024 * 1024  # 1000MB
```

### Performance Optimizations

- **Database query optimization** with select_related and prefetch_related
- **Caching** for frequently accessed data
- **Pagination** for large datasets
- **Background tasks** with Celery (configured but not implemented)

---

## 🛠️ Development Setup

### Prerequisites

- Python 3.8+
- pip (Python package manager)
- Git

### Installation Steps

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd backend
   ```

2. **Create virtual environment**

   ```bash
   python -m venv env
   source env/bin/activate  # On Windows: env\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Run migrations**

   ```bash
   python manage.py migrate
   ```

5. **Create superuser**

   ```bash
   python manage.py createsuperuser
   ```

6. **Start development server**
   ```bash
   python manage.py runserver
   ```

### Environment Variables

```bash
# Django settings
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Database (for production)
DB_NAME=youcef_db
DB_USER=postgres
DB_PASSWORD=123456789
DB_HOST=localhost
DB_PORT=5432

# Redis (for production)
REDIS_URL=redis://localhost:6379
```

### Development Scripts

| Script                 | Description                      |
| ---------------------- | -------------------------------- |
| `run_server.py`        | Standard HTTP development server |
| `run_https_server.py`  | HTTPS development server         |
| `start_http_server.py` | HTTP server with custom settings |
| `simple_server.py`     | Simple server for testing        |

---

## 🚀 Deployment

### Production Checklist

- [ ] Set `DEBUG = False`
- [ ] Configure production database (PostgreSQL)
- [ ] Set up Redis for caching and WebSocket
- [ ] Configure static files collection
- [ ] Set up SSL/HTTPS
- [ ] Configure logging
- [ ] Set environment variables
- [ ] Run security checks

### Docker Deployment

```dockerfile
# Dockerfile (example)
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

### Environment Configuration

```python
# Production settings
DEBUG = False
ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com']

# Security settings
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. CORS Errors

**Problem**: Frontend can't connect to backend
**Solution**: Check CORS settings in `settings.py`

```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
```

#### 2. Database Connection Issues

**Problem**: Database connection fails
**Solution**: Check database configuration and migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

#### 3. WebSocket Connection Issues

**Problem**: Real-time features not working
**Solution**: Check ASGI configuration and Redis

```python
# Ensure ASGI is properly configured
ASGI_APPLICATION = "backend.asgi.application"
```

#### 4. Rate Limiting Issues

**Problem**: Too many requests error
**Solution**: Check rate limiting configuration

```python
# Adjust rate limits if needed
'login': '10/minute',  # Increase from 5/minute
```

### Debug Mode

Enable debug mode for detailed error messages:

```python
DEBUG = True
```

### Logging

Check application logs in `django.log` for detailed error information.

---

## 📊 API Response Formats

### Success Response

```json
{
  "success": true,
  "data": {
    "id": 1,
    "username": "user123",
    "email": "user@example.com"
  },
  "message": "Operation successful"
}
```

### Error Response

```json
{
  "success": false,
  "error": "Invalid credentials",
  "code": "INVALID_CREDENTIALS",
  "details": []
}
```

### Pagination Response

```json
{
    "count": 100,
    "next": "http://api.example.com/users/?page=2",
    "previous": null,
    "results": [...]
}
```

---

## 📈 Monitoring & Logging

### Logging Configuration

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'django.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'INFO',
    },
}
```

### Health Check Endpoint

```bash
GET /api/health/
```

Response:

```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "version": "1.0.0",
  "database": "connected",
  "cache": "connected"
}
```

---

## 🔄 Version History

### v1.0.0 (Current)

- ✅ Complete authentication system
- ✅ Real-time messaging
- ✅ Notification system
- ✅ Role-based access control
- ✅ WebSocket support
- ✅ CORS configuration
- ✅ Rate limiting
- ✅ Security features

### Planned Features

- 🔄 Background task processing (Celery)
- 🔄 File upload optimization
- 🔄 Advanced caching strategies
- 🔄 API documentation (Swagger/OpenAPI)
- 🔄 Unit and integration tests
- 🔄 Docker containerization

---

## 📞 Support

For issues and questions:

1. **Check the logs**: `django.log`
2. **Review this documentation**
3. **Test endpoints**: Use the provided test scripts
4. **Check CORS**: Use `/api/test-cors/` endpoint

### Useful Commands

```bash
# Check Django configuration
python manage.py check

# Run tests
python manage.py test

# Check for security issues
python manage.py check --deploy

# Collect static files
python manage.py collectstatic

# Create database backup
python manage.py dumpdata > backup.json

# Load database backup
python manage.py loaddata backup.json
```

---

## 📄 License

This backend system is part of the Youcef project. All rights reserved.

---

_Last updated: January 2024_
_Version: 1.0.0_
