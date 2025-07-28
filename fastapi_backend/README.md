# 🚀 FastAPI Backend System

A comprehensive FastAPI backend with real-time features, role-based access control (RBAC), and messaging capabilities.

## 📋 Table of Contents

1. [Features](#features)
2. [Architecture](#architecture)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [API Endpoints](#api-endpoints)
6. [Database Models](#database-models)
7. [Security](#security)
8. [Development](#development)
9. [Deployment](#deployment)

---

## ✨ Features

### 🔐 Authentication & Authorization

- **JWT Token-based authentication**
- **Role-Based Access Control (RBAC)**
- **Password hashing with bcrypt**
- **Rate limiting for security**
- **Token refresh mechanism**

### 💬 Real-time Messaging

- **WebSocket support for real-time communication**
- **Conversation management**
- **Message reactions and emojis**
- **User blocking functionality**
- **File sharing support**

### 🔔 Notification System

- **Real-time notifications**
- **Notification preferences**
- **Read status tracking**
- **Multi-channel delivery**

### 👥 User Management

- **User registration and profiles**
- **Role assignment**
- **Permission management**
- **User blocking system**

### 🛡️ Security Features

- **CORS configuration**
- **Rate limiting**
- **Input validation**
- **SQL injection protection**
- **XSS protection**

---

## 🏗️ Architecture

### Technology Stack

| Component            | Technology        | Version  |
| -------------------- | ----------------- | -------- |
| **Framework**        | FastAPI           | 0.104.1  |
| **ASGI Server**      | Uvicorn           | 0.24.0   |
| **Database**         | SQLAlchemy        | 2.0.23   |
| **Authentication**   | JWT (python-jose) | 3.3.0    |
| **Password Hashing** | bcrypt            | 1.7.4    |
| **Configuration**    | Pydantic Settings | 2.1.0    |
| **CORS**             | FastAPI CORS      | Built-in |
| **Redis**            | Redis             | 5.0.1    |

### Project Structure

```
fastapi_backend/
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── .env                   # Environment variables (create this)
├── core/                  # Core functionality
│   ├── config.py          # Application settings
│   ├── security.py        # Authentication & security
│   └── rate_limiter.py    # Rate limiting
├── database/              # Database configuration
│   └── connection.py      # SQLAlchemy setup
├── models/                # Database models
│   ├── user.py           # User model
│   ├── role.py           # Role model
│   ├── permission.py     # Permission model
│   ├── notification.py   # Notification models
│   ├── conversation.py   # Conversation models
│   ├── message.py        # Message models
│   └── user_block.py     # User blocking model
├── api/                   # API routers
│   ├── auth.py           # Authentication endpoints
│   ├── users.py          # User management
│   ├── notifications.py  # Notification system
│   ├── messaging.py      # Messaging system
│   └── health.py         # Health checks
└── fastapi_backend.db    # SQLite database (created automatically)
```

---

## 🚀 Installation

### Prerequisites

- Python 3.8+
- pip (Python package manager)
- Git

### Setup Steps

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd fastapi_backend
   ```

2. **Create virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Create environment file**

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run the application**
   ```bash
   python main.py
   ```

The server will start at `http://localhost:8000`

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
# Application
APP_NAME=Youcef Backend API
APP_VERSION=1.0.0
DEBUG=True

# Server
HOST=0.0.0.0
PORT=8000

# Security
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database
DATABASE_URL=sqlite:///./fastapi_backend.db
DATABASE_ECHO=False

# Redis
REDIS_URL=redis://localhost:6379

# CORS
CORS_ALLOWED_ORIGINS=["http://localhost:3000","http://localhost:5173"]

# Rate Limiting
RATE_LIMIT_ANON=100/hour
RATE_LIMIT_USER=1000/hour
RATE_LIMIT_LOGIN=5/minute
RATE_LIMIT_REGISTER=3/minute
```

---

## 📡 API Endpoints

### Authentication Endpoints

| Method | Endpoint             | Description             | Rate Limit |
| ------ | -------------------- | ----------------------- | ---------- |
| `POST` | `/api/register`      | User registration       | 3/minute   |
| `POST` | `/api/login`         | User login              | 5/minute   |
| `POST` | `/api/logout`        | User logout             | -          |
| `POST` | `/api/refresh-token` | Token refresh           | -          |
| `GET`  | `/api/protected`     | Protected endpoint test | -          |
| `GET`  | `/api/test-cors`     | CORS testing            | -          |

### User Management Endpoints

| Method | Endpoint                             | Description           |
| ------ | ------------------------------------ | --------------------- |
| `GET`  | `/users/users`                       | List all users        |
| `GET`  | `/users/{user_id}`                   | Get user profile      |
| `PUT`  | `/users/{user_id}`                   | Update user profile   |
| `GET`  | `/users/roles`                       | List all roles        |
| `GET`  | `/users/permissions`                 | List all permissions  |
| `POST` | `/users/assign-role`                 | Assign role to user   |
| `GET`  | `/users/check-role/{role_name}`      | Check user role       |
| `GET`  | `/users/check-permission/{codename}` | Check user permission |

### Notification Endpoints

| Method | Endpoint                                             | Description            |
| ------ | ---------------------------------------------------- | ---------------------- |
| `GET`  | `/api/notifications/notifications`                   | Get notifications      |
| `POST` | `/api/notifications/notifications/{id}/mark_as_read` | Mark as read           |
| `POST` | `/api/notifications/notifications/mark_all_as_read`  | Mark all as read       |
| `GET`  | `/api/notifications/notifications/stats`             | Get notification stats |
| `GET`  | `/api/notifications/preferences`                     | Get preferences        |
| `PUT`  | `/api/notifications/preferences/update_preferences`  | Update preferences     |

### Messaging Endpoints

| Method | Endpoint                                     | Description         |
| ------ | -------------------------------------------- | ------------------- |
| `GET`  | `/api/messaging/conversations`               | Get conversations   |
| `GET`  | `/api/messaging/conversations/{id}/messages` | Get messages        |
| `POST` | `/api/messaging/conversations/{id}/messages` | Send message        |
| `POST` | `/api/messaging/conversations`               | Create conversation |
| `POST` | `/api/messaging/messages/{id}/react`         | Add reaction        |
| `POST` | `/api/messaging/blocks`                      | Block user          |
| `POST` | `/api/messaging/blocks/unblock`              | Unblock user        |
| `GET`  | `/api/messaging/blocks/blocked_users`        | Get blocked users   |

### Health Check Endpoints

| Method | Endpoint               | Description           |
| ------ | ---------------------- | --------------------- |
| `GET`  | `/api/health`          | Basic health check    |
| `GET`  | `/api/health/detailed` | Detailed health check |

---

## 🗄️ Database Models

### User Models

- **User**: Extended user model with profile fields
- **Role**: Role-based access control
- **Permission**: Granular permission system
- **UserRole**: User-role relationships
- **RolePermission**: Role-permission relationships

### Notification Models

- **Notification**: Notification content and metadata
- **NotificationPreference**: User notification preferences

### Messaging Models

- **Conversation**: Chat conversations
- **ConversationParticipant**: Conversation participants
- **Message**: Individual messages
- **MessageReaction**: Message reactions
- **UserBlock**: User blocking system

---

## 🔒 Security

### Authentication

- JWT token-based authentication
- Access and refresh tokens
- Password hashing with bcrypt
- Token expiration and refresh

### Authorization

- Role-Based Access Control (RBAC)
- Permission-based authorization
- User role assignment
- Permission checking

### Rate Limiting

- Anonymous users: 100 requests/hour
- Authenticated users: 1000 requests/hour
- Login attempts: 5 requests/minute
- Registration: 3 requests/minute

### CORS Configuration

- Configurable allowed origins
- Support for multiple frontend domains
- Secure cookie handling

---

## 🛠️ Development

### Running in Development

```bash
# Start the development server
python main.py

# Or with uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### API Documentation

Once the server is running, you can access:

- **Interactive API docs**: http://localhost:8000/docs
- **ReDoc documentation**: http://localhost:8000/redoc
- **OpenAPI schema**: http://localhost:8000/openapi.json

### Database Migrations

```bash
# Initialize Alembic (if using migrations)
alembic init alembic

# Create a migration
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head
```

### Testing

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=app tests/
```

---

## 🚀 Deployment

### Production Checklist

- [ ] Set `DEBUG = False`
- [ ] Configure production database (PostgreSQL)
- [ ] Set up Redis for caching
- [ ] Configure SSL/HTTPS
- [ ] Set environment variables
- [ ] Configure logging
- [ ] Set up monitoring

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Configuration

```env
# Production settings
DEBUG=False
DATABASE_URL=postgresql://user:password@localhost/dbname
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-production-secret-key
```

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

### Token Response

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

---

## 🔧 Troubleshooting

### Common Issues

1. **Database Connection Issues**

   - Check database URL in `.env`
   - Ensure database is running
   - Run database initialization

2. **CORS Errors**

   - Verify CORS settings in configuration
   - Check allowed origins

3. **Authentication Issues**

   - Verify JWT secret key
   - Check token expiration
   - Validate request headers

4. **Rate Limiting**
   - Check rate limit configuration
   - Monitor request frequency

### Debug Mode

Enable debug mode for detailed error messages:

```python
DEBUG = True
```

---

## 📞 Support

For issues and questions:

1. Check the logs in `fastapi.log`
2. Review this documentation
3. Test endpoints using the interactive docs
4. Check the health endpoints

### Useful Commands

```bash
# Check application health
curl http://localhost:8000/api/health

# Test CORS
curl http://localhost:8000/api/test-cors

# Get API info
curl http://localhost:8000/api/info
```

---

## 📄 License

This FastAPI backend is part of the Youcef project. All rights reserved.

---

_Last updated: January 2024_
_Version: 1.0.0_
