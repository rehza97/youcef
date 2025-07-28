# New Django Backend

A fresh Django REST API backend with proper CORS configuration, authentication, and real-time features.

## 🚀 Features

- **Authentication System**: Token-based authentication with registration, login, logout
- **User Management**: Role-based permissions and user profiles
- **Real-time Notifications**: WebSocket-based notification system
- **Messaging System**: Real-time chat with reactions and user blocking
- **CORS Support**: Properly configured for frontend development
- **Admin Interface**: Django admin for easy data management
- **API Documentation**: Comprehensive REST API endpoints

## 📋 Prerequisites

- Python 3.8+
- pip (Python package manager)

## 🛠️ Installation

### 1. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run Database Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Create Superuser (Optional)

```bash
python manage.py createsuperuser
```

## 🚀 Running the Server

### Quick Start

```bash
python start_server.py
```

### Manual Start

```bash
python manage.py runserver 127.0.0.1:8000
```

The server will start on `http://127.0.0.1:8000/`

## 🧪 Testing

### Test CORS Configuration

```bash
python test_cors.py
```

### Test API Endpoints

```bash
# Health check
curl http://127.0.0.1:8000/api/health/

# Register user
curl -X POST http://127.0.0.1:8000/api/register/ \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass123", "email": "test@example.com"}'

# Login
curl -X POST http://127.0.0.1:8000/api/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass123"}'
```

## 📡 API Endpoints

### Authentication

- `POST /api/register/` - User registration
- `POST /api/login/` - User login
- `POST /api/logout/` - User logout
- `POST /api/refresh-token/` - Refresh authentication token

### User Management

- `GET /api/profile/` - Get user profile
- `PUT /api/profile/` - Update user profile
- `POST /api/change-password/` - Change password

### Users & Roles

- `GET /users/users/` - List all users
- `GET /users/roles/` - List all roles
- `GET /users/permissions/` - List all permissions
- `POST /users/assign-role/` - Assign role to user

### Notifications

- `GET /api/notifications/notifications/` - Get user notifications
- `POST /api/notifications/notifications/{id}/mark_as_read/` - Mark notification as read
- `POST /api/notifications/notifications/mark_all_as_read/` - Mark all notifications as read
- `GET /api/notifications/preferences/` - Get notification preferences
- `POST /api/notifications/preferences/update_preferences/` - Update notification preferences

### Messaging

- `GET /api/messaging/conversations/` - Get user conversations
- `GET /api/messaging/conversations/{id}/messages/` - Get conversation messages
- `POST /api/messaging/conversations/{id}/messages/` - Send message
- `POST /api/messaging/messages/{id}/react/` - Add reaction to message
- `POST /api/messaging/blocks/` - Block user
- `POST /api/messaging/blocks/unblock/` - Unblock user

### System

- `GET /api/health/` - Health check
- `GET /api/info/` - API information
- `GET /api/protected/` - Protected endpoint example

## 🔧 Configuration

### CORS Settings

The backend is configured to allow requests from:

- `http://localhost:5173`
- `http://localhost:5174`
- `http://127.0.0.1:5173`
- `http://127.0.0.1:5174`

### Environment Variables

- `DJANGO_SECRET_KEY` - Django secret key
- `DJANGO_DEBUG` - Debug mode (True/False)
- `DJANGO_ALLOWED_HOSTS` - Comma-separated list of allowed hosts

## 🌐 WebSocket Endpoints

### Notifications

- `ws://127.0.0.1:8000/ws/notifications/` - Real-time notifications

### Chat

- `ws://127.0.0.1:8000/ws/chat/{conversation_id}/` - Real-time messaging

## 📊 Database Models

### Core Models

- **User**: Django's built-in User model
- **UserProfile**: Extended user profile with roles
- **Role**: Role-based permissions
- **Permission**: Django's built-in Permission model

### Notification Models

- **Notification**: User notifications with types
- **NotificationPreference**: User notification preferences

### Messaging Models

- **Conversation**: Chat conversations
- **Message**: Individual messages
- **MessageReaction**: Message reactions (like, love, etc.)
- **UserBlock**: User blocking system

## 🔒 Security Features

- **Token Authentication**: Secure token-based authentication
- **Rate Limiting**: API rate limiting for login/register
- **CORS Protection**: Proper CORS configuration
- **CSRF Protection**: Built-in CSRF protection
- **Password Validation**: Strong password requirements
- **User Blocking**: User blocking system for messaging

## 🎯 Frontend Integration

### API Base URL

```javascript
const API_BASE_URL = "http://127.0.0.1:8000/";
```

### Authentication Headers

```javascript
headers: {
  "Authorization": "Token your-token-here",
  "Content-Type": "application/json"
}
```

### WebSocket Connection

```javascript
// Notifications
const notificationSocket = new WebSocket(
  "ws://127.0.0.1:8000/ws/notifications/"
);

// Chat
const chatSocket = new WebSocket("ws://127.0.0.1:8000/ws/chat/1/");
```

## 🐛 Troubleshooting

### Common Issues

1. **CORS Errors**: Make sure the frontend is running on an allowed origin
2. **Database Errors**: Run `python manage.py migrate`
3. **Import Errors**: Make sure all dependencies are installed
4. **Port Conflicts**: Change the port in `start_server.py` if needed

### Debug Mode

Set `DJANGO_DEBUG=True` in environment variables for detailed error messages.

## 📝 Development

### Adding New Endpoints

1. Create views in the appropriate app
2. Add URL patterns in `urls.py`
3. Test with the provided test scripts

### Database Changes

```bash
python manage.py makemigrations
python manage.py migrate
```

### Admin Interface

Access at `http://127.0.0.1:8000/admin/` after creating a superuser.

## 📄 License

This project is for development purposes only.
