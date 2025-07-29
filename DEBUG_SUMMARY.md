# 🔍 Comprehensive Debug System

## **Backend Debugging Features**

### **1. Enhanced Logging Configuration**

- **File**: `fastapi_backend/main.py`
- **Features**:
  - Detailed logging with timestamps and module names
  - Separate WebSocket logger (`ws_logger`)
  - File-specific logger (`file_logger`)
  - Debug level logging for all operations
  - Log output to both console and `debug.log` file

### **2. WebSocket Authentication Debugging**

- **File**: `fastapi_backend/main.py`
- **Features**:
  - Token validation step-by-step logging
  - User authentication tracking
  - Connection lifecycle monitoring
  - Error code and reason logging
  - Message parsing and handling logs

### **3. File Upload Debugging**

- **File**: `fastapi_backend/api/files.py`
- **Features**:
  - File validation logging
  - Upload progress tracking
  - Database record creation logs
  - Notification sending logs
  - Error handling with detailed context

### **4. Comprehensive Test Script**

- **File**: `fastapi_backend/test_debug.py`
- **Features**:
  - Backend health check
  - Authentication flow testing
  - File upload testing
  - WebSocket connection testing
  - API endpoint testing
  - Detailed error reporting

## **Frontend Debugging Features**

### **1. Debug Logger Utility**

- **File**: `frontend/src/lib/debug.js`
- **Features**:
  - Timestamped logging with emojis
  - API call tracking
  - WebSocket event logging
  - Authentication debugging
  - File upload tracking
  - Component-specific debugging

### **2. API Service Debugging**

- **File**: `frontend/src/services/api.js`
- **Features**:
  - Request/response interceptors
  - Authentication header logging
  - Error response tracking
  - API call performance monitoring

### **3. WebSocket Hook Debugging**

- **File**: `frontend/src/hooks/useNotificationsWebSocket.js`
- **Features**:
  - Connection lifecycle logging
  - Message parsing debugging
  - Reconnection logic tracking
  - Error handling with context

### **4. Files Page Debugging**

- **File**: `frontend/src/pages/FilesPage/index.jsx`
- **Features**:
  - Component lifecycle logging
  - File upload process tracking
  - WebSocket connection status
  - Mutation success/error logging

### **5. Browser Console Debugger**

- **File**: `frontend/src/lib/frontend-debug.js`
- **Features**:
  - Global debug instance (`window.frontendDebug`)
  - Authentication testing
  - File upload testing
  - WebSocket connection testing
  - API endpoint testing
  - App state inspection

## **How to Use the Debug System**

### **Backend Testing**

```bash
# Run comprehensive backend tests
cd fastapi_backend
python test_debug.py

# Check debug logs
tail -f debug.log
```

### **Frontend Testing**

```javascript
// In browser console
// Run comprehensive frontend tests
window.frontendDebug.runFullTest();

// Debug current app state
window.frontendDebug.debugAppState();

// Test specific features
window.frontendDebug.testAuth();
window.frontendDebug.testFileUpload(token);
window.frontendDebug.testWebSocket(token);
```

### **Component Debugging**

```javascript
// In any component
import { debugComponent } from "../lib/debug.js";

const debug = debugComponent("MyComponent");
debug.log("Component rendered", { data });
debug.error("Error occurred", error);
debug.success("Operation successful", result);
```

## **Debug Output Examples**

### **Backend WebSocket Logs**

```
🔌 WebSocket connection attempt for user_id: 1
📡 Accepting WebSocket connection...
✅ WebSocket connection accepted
🔍 Token from query params: Present
🔍 Starting token validation for token: eyJhbGciOiJIUzI1NiIs...
🔧 Removed 'Bearer ' prefix from token
🔍 Validating token: eyJhbGciOiJIUzI1NiIs...
✅ Token validation successful, user_id: 1
✅ User found: admin (ID: 1)
✅ Authentication successful for user: admin
🔗 Connecting to notification manager...
✅ User 1 connected to notifications WebSocket
📤 Sending welcome message: {"type": "connection", "message": "Connected to notifications", "user_id": 1, "timestamp": "2024-01-01T12:00:00"}
✅ Welcome message sent
🔄 Starting message loop...
```

### **Frontend Debug Logs**

```
🔍 [DEBUG] 2024-01-01T12:00:00.000Z - [FilesPage] Component rendered
📊 Data: {wsConnected: true, notificationCount: 5, fileNotificationCount: 2}

🔌 WebSocket: Attempting connection
📊 Data: {user: "admin", userId: 1}

🌐 API Call: POST http://127.0.0.1:8000/api/files/upload
📊 Data: {headers: {...}, data: FormData}

✅ [SUCCESS] 2024-01-01T12:00:00.000Z - [FilesPage] File upload successful
📊 Data: {id: 1, filename: "test.csv", ...}
```

## **Troubleshooting Common Issues**

### **1. WebSocket 403 Forbidden**

- Check token validation in backend logs
- Verify user authentication
- Check token format and expiration

### **2. File Upload 422 Error**

- Check file validation in backend logs
- Verify authentication headers
- Check file type and size limits

### **3. Frontend Connection Issues**

- Check browser console for WebSocket errors
- Verify API base URL configuration
- Check authentication state

### **4. Real-time Notifications Not Working**

- Check WebSocket connection status
- Verify notification service integration
- Check user notification preferences

## **Next Steps**

1. **Run the backend test script** to identify server-side issues
2. **Use browser console debugging** to test frontend functionality
3. **Check debug logs** for detailed error information
4. **Monitor WebSocket connections** in real-time
5. **Test file uploads** with detailed logging

The debug system provides comprehensive visibility into both frontend and backend operations, making it easier to identify and fix the issues you're experiencing.
