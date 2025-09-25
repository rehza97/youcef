# Frontend Application

A modern React application built with Vite, featuring comprehensive error handling, real-time messaging, and role-based access control.

## 🚀 Features

### Core Features

- **Authentication System**: Secure login/register with token management
- **Role-Based Access Control (RBAC)**: User roles and permissions
- **Real-time Messaging**: WebSocket-powered chat system
- **Notifications**: Real-time notifications with preferences
- **File Management**: Upload, process, and manage files with previews
- **Encaissement Module**: Financial data processing and analysis
- **Responsive Design**: Mobile-first approach with dark mode support
- **Error Handling**: Comprehensive error management and user feedback

### Technical Features

- **Modern React**: React 19 with hooks and functional components
- **State Management**: React Query for server state, Context API for auth
- **UI Components**: Shadcn/ui with Tailwind CSS
- **Type Safety**: TypeScript support throughout
- **Real-time**: WebSocket integration for live updates
- **Error Boundaries**: React Error Boundaries for graceful error handling

## 📁 Project Structure

```
frontend/
├── src/
│   ├── components/          # Reusable UI components
│   │   ├── auth/           # Authentication components
│   │   ├── layout/         # Layout components (Sidebar, etc.)
│   │   ├── messaging/      # Messaging components
│   │   ├── notifications/  # Notification components
│   │   └── ui/            # Shadcn/ui components
│   ├── pages/             # Route components
│   ├── hooks/             # Custom React hooks
│   ├── contexts/          # React contexts (Auth, etc.)
│   ├── services/          # API services
│   ├── api/              # API endpoint modules
│   ├── lib/              # Utility functions
│   └── assets/           # Static assets
```

## 🔧 Setup & Installation

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## 🛠️ Key Components

### API Service (`services/api.js`)

Centralized API management with comprehensive CRUD operations:

- **Authentication**: Login, register, token refresh
- **Users**: Full CRUD with role management
- **Roles & Permissions**: Complete RBAC system
- **Notifications**: CRUD operations with preferences
- **Messaging**: Conversations, messages, and user blocking
- **Files**: Upload, preview, and management
- **Encaissement**: Financial data processing

```javascript
import {
  authAPI,
  usersAPI,
  messagingAPI,
  notificationsAPI,
  filesAPI,
  encaissementAPI,
} from "../services/api";

// Usage examples
const login = await authAPI.login(credentials);
const users = await usersAPI.getUsers();
const conversations = await messagingAPI.fetchConversations();
const files = await filesAPI.getUserFiles();
const overview = await encaissementAPI.getOverview();
```

### Error Handling (`lib/error-handler.js`)

Comprehensive error management with backend-specific handling:

- **Error Classification**: HTTP status and backend error codes
- **User-friendly Messages**: Contextual error messages
- **Toast Integration**: Automatic error notifications
- **Retry Logic**: Exponential backoff for failed requests
- **Backend Compatibility**: Handles FastAPI error formats

```javascript
import { handleApiError, ERROR_SEVERITY } from "../lib/error-handler";

try {
  await apiCall();
} catch (error) {
  handleApiError(error, {
    showToast: true,
    logError: true,
    fallbackMessage: "Operation failed",
  });
}
```

### Loading Components (`components/ui/loading.jsx`)

Rich loading states for better UX:

- **Spinner**: Different sizes and colors
- **Skeleton Loaders**: Content placeholders
- **Loading Overlays**: Full-page loading states
- **Progress Bars**: Upload and processing indicators
- **Status Indicators**: Success, error, warning states

```javascript
import { Spinner, LoadingOverlay, ContentLoader } from '../components/ui/loading';

// Usage
<Spinner size="lg" color="primary" />
<LoadingOverlay isLoading={loading} message="Loading data...">
  <YourComponent />
</LoadingOverlay>
```

### Error Boundary (`components/ErrorBoundary.jsx`)

React Error Boundary for catching JavaScript errors:

- **Graceful Fallback**: User-friendly error UI
- **Retry Mechanism**: Automatic retry with limits
- **Development Details**: Error details in development
- **Navigation Options**: Home and reload buttons

## 🔐 Authentication

### Features

- Token-based authentication with JWT
- Automatic token refresh
- Session/local storage management
- Route protection
- CSRF protection

### Usage

```javascript
import { useAuth } from "../contexts/AuthContext";

const { user, login, logout, isAuthenticated } = useAuth();
```

## 📡 Real-time Features

### WebSocket Integration

- **Chat WebSocket**: Real-time messaging
- **Notifications WebSocket**: Live notifications
- **Connection Management**: Automatic reconnection
- **Error Handling**: Graceful connection failures

### Usage

```javascript
import { useChatWebSocket } from "../hooks/useChatWebSocket";
import { useNotificationsWebSocket } from "../hooks/useNotificationsWebSocket";

const { messages, sendMessage } = useChatWebSocket(conversationId);
const { notifications } = useNotificationsWebSocket();
```

## 🎨 UI/UX Features

### Design System

- **Shadcn/ui Components**: Consistent, accessible components
- **Tailwind CSS**: Utility-first styling
- **Dark Mode**: Full dark/light theme support
- **Responsive Design**: Mobile-first approach

### Toast Notifications

- Success, error, warning, and info notifications
- Customizable duration and styling
- Integration with error handling

## 🔒 Security Features

### Client-side Security

- Input sanitization
- XSS protection
- Token validation
- Secure storage management

### API Security

- CSRF token handling
- Request sanitization
- Error message sanitization
- Secure cookie handling

## 📱 Responsive Design

### Mobile Support

- Responsive sidebar with mobile menu
- Touch-friendly interface
- Optimized form inputs
- Mobile-first breakpoints

### Breakpoints

- Mobile: < 768px
- Tablet: 768px - 1024px
- Desktop: > 1024px

## 🧪 Development

### Code Quality

- ESLint configuration
- TypeScript support
- Consistent code formatting
- Error boundary testing

### Performance

- Code splitting
- Lazy loading
- Optimized bundle size
- Efficient re-renders

## 🚀 Deployment

### Build Process

```bash
# Development
npm run dev

# Production build
npm run build

# Preview production
npm run preview
```

### Environment Variables

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/
VITE_WS_BASE_URL=ws://127.0.0.1:8000/
```

## 📚 API Documentation

### Authentication Endpoints

- `POST /api/auth/login/` - User login
- `POST /api/auth/register/` - User registration
- `POST /api/auth/logout/` - User logout
- `POST /api/auth/refresh-token/` - Token refresh

### User Management

- `GET /api/users/` - Get all users
- `POST /api/users/` - Create user (Admin only)
- `PUT /api/users/{id}` - Update user
- `DELETE /api/users/{id}` - Delete user (Admin only)
- `GET /api/users/roles/` - Get all roles
- `POST /api/users/roles/` - Create role (Admin only)
- `GET /api/users/permissions/` - Get all permissions

### Messaging

- `GET /api/conversations/` - Get conversations
- `POST /api/conversations/` - Create conversation
- `GET /api/messages/conversations/{id}/messages/` - Get messages
- `POST /api/messages/conversations/{id}/messages/` - Send message

### Notifications

- `GET /api/notifications/` - Get notifications
- `POST /api/notifications/` - Create notification
- `PUT /api/notifications/{id}/read/` - Mark as read

### Files

- `POST /api/files/upload/` - Upload file
- `GET /api/files/` - Get user files
- `GET /api/files/{id}/` - Get file details
- `PUT /api/files/{id}/` - Update file metadata

### Encaissement

- `POST /api/encaissement/upload-data/` - Upload financial data
- `GET /api/encaissement/overview/` - Get overview statistics
- `GET /api/encaissement/by-organisation/` - Data by organization
- `GET /api/encaissement/by-date/` - Data by date
- `GET /api/encaissement/by-encaisse-rate/` - Data by encaissement rate

## 🤝 Contributing

### Code Style

- Use functional components with hooks
- Implement proper error handling
- Add loading states for async operations
- Follow the established component structure

### Error Handling Guidelines

1. Always use `handleApiError` for API calls
2. Implement loading states for user feedback
3. Use Error Boundaries for component-level errors
4. Provide fallback UI for error states

### Testing

- Test error scenarios
- Verify loading states
- Check responsive behavior
- Validate form submissions

## 📝 Recent Improvements

### ✅ Fixed Issues

1. **Missing API Service**: Recreated `services/api.js` with comprehensive endpoints
2. **Import Inconsistencies**: Fixed all import paths and dependencies
3. **Error Handling**: Implemented comprehensive error management system
4. **Loading States**: Added rich loading components and states
5. **Error Boundaries**: Added React Error Boundaries for graceful error handling
6. **Backend Compatibility**: Updated to work with FastAPI backend fixes
7. **CRUD Operations**: Added complete CRUD for all modules
8. **Encaissement Module**: Added financial data processing interface

### 🆕 New Features

1. **Error Handler Utility**: Centralized error classification and handling
2. **Loading Components**: Comprehensive loading states and animations
3. **Error Boundary**: React Error Boundary with retry mechanism
4. **Improved Auth Context**: Better error handling and token management
5. **Enhanced Forms**: Better validation and user feedback
6. **Encaissement Page**: Complete financial data interface
7. **Admin Endpoints**: Added admin-only file management
8. **Backend Error Handling**: Specific error messages for backend responses

### 🔧 Technical Improvements

1. **API Service**: Complete Axios setup with interceptors
2. **Error Classification**: HTTP status-based error categorization
3. **Toast Integration**: Seamless error notification system
4. **Loading States**: Multiple loading component types
5. **Security**: Enhanced input sanitization and validation
6. **Backend Integration**: Full compatibility with FastAPI backend
7. **CRUD Operations**: Complete Create, Read, Update, Delete for all modules
8. **File Management**: Enhanced file upload and processing

## 🎯 Next Steps

### Planned Improvements

1. **Unit Tests**: Add comprehensive test coverage
2. **Storybook**: Component documentation
3. **Performance**: Implement code splitting and lazy loading
4. **Accessibility**: Enhanced ARIA labels and keyboard navigation
5. **PWA**: Progressive Web App features

### Performance Optimizations

1. **Bundle Analysis**: Monitor and optimize bundle size
2. **Image Optimization**: Implement lazy loading for images
3. **Caching**: Implement service worker for offline support
4. **Code Splitting**: Route-based code splitting

---

**Status**: ✅ Production Ready
**Last Updated**: December 2024
**Version**: 1.0.0
