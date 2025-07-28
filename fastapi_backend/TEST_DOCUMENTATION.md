# FastAPI Backend Test Documentation

This document provides comprehensive information about all test scripts available for the FastAPI backend.

## 📋 Test Scripts Overview

### 1. `test_comprehensive_detailed.py` - Main Comprehensive Test

**Purpose**: Complete API testing with detailed reporting and admin login verification

**Features**:

- ✅ **Comprehensive endpoint coverage**: Tests all API endpoints systematically
- ✅ **Admin login verification**: Specifically tests admin account (username: `admin`, password: `admin`)
- ✅ **Detailed reporting**: Shows timestamps, success/failure indicators, and response data
- ✅ **Error tracking**: Maintains detailed error logs and test statistics
- ✅ **Test categorization**: Groups tests by functionality (Auth, Users, Roles, Notifications, Messaging, etc.)
- ✅ **Robust error handling**: Gracefully handles various error scenarios
- ✅ **Test summary**: Provides comprehensive test results with success rates

**Usage**:

```bash
python test_comprehensive_detailed.py
```

**Output includes**:

- 🔐 Admin login testing with token verification
- 🔐 Authentication endpoint testing (valid/invalid tokens)
- 👥 User endpoint testing (profile, search, CRUD operations)
- 🔑 Role and permission endpoint testing
- 🔔 Notification endpoint testing with data creation
- 💬 Messaging endpoint testing with conversation creation
- 🚫 User blocking endpoint testing
- 🏥 Health check endpoint testing

### 2. `test_admin_login.py` - Focused Admin Login Test

**Purpose**: Detailed testing of admin login functionality specifically

**Features**:

- ✅ **Detailed admin login verification**: Tests admin credentials thoroughly
- ✅ **Invalid login scenarios**: Tests various invalid login attempts
- ✅ **Token verification**: Tests protected endpoints with obtained token
- ✅ **User profile verification**: Confirms admin user profile access
- ✅ **Response analysis**: Detailed analysis of login responses

**Usage**:

```bash
python test_admin_login.py
```

**Test scenarios**:

1. Valid admin login (username: `admin`, password: `admin`)
2. Invalid username/password combinations
3. Empty/missing credentials
4. Protected endpoint access with admin token
5. Admin user profile verification

### 3. `test_improved.py` - Improved General Test

**Purpose**: Enhanced version of basic API testing with better error handling

**Features**:

- ✅ **Robust data creation**: Creates test notifications and conversations
- ✅ **Idempotent testing**: Handles existing data gracefully
- ✅ **Better error handling**: Accepts multiple valid status codes
- ✅ **Resource management**: Attempts to use existing resources before creating new ones

**Usage**:

```bash
python test_improved.py
```

### 4. `verify_fixes.py` - Quick Verification Test

**Purpose**: Quick verification of critical fixes

**Features**:

- ✅ **Fast execution**: Focuses on critical endpoints only
- ✅ **Fix verification**: Specifically tests previously problematic endpoints
- ✅ **Minimal output**: Concise reporting for quick verification

**Usage**:

```bash
python verify_fixes.py
```

## 🎯 Test Coverage Details

### Authentication Endpoints

- `POST /api/auth/login` - Admin login verification
- `GET /api/auth/protected` - Protected endpoint access
- Invalid token testing
- Invalid credential testing

### User Endpoints

- `GET /api/users/me` - Current user profile
- `PUT /api/users/me` - Update user profile
- `GET /api/users/search?q={query}` - User search
- `GET /api/users/` - Get all users
- `GET /api/users/{user_id}` - Get specific user

### Role & Permission Endpoints

- `GET /api/users/roles/` - Get all roles
- `GET /api/users/permissions/` - Get all permissions
- `POST /api/users/roles/` - Create new role
- `GET /api/users/roles/{role_id}` - Get specific role
- `GET /api/users/permissions/{permission_id}` - Get specific permission
- `GET /api/users/{user_id}/roles` - Get user roles
- `GET /api/users/roles/{role_id}/permissions` - Get role permissions

### Notification Endpoints

- `GET /api/notifications/` - Get all notifications
- `POST /api/notifications/` - Create notification
- `GET /api/notifications/{notification_id}` - Get specific notification
- `PUT /api/notifications/{notification_id}/read` - Mark as read
- `PUT /api/notifications/read-all` - Mark all as read
- `PUT /api/notifications/preferences` - Update preferences

### Messaging Endpoints

- `GET /api/messaging/conversations` - Get all conversations
- `POST /api/messaging/conversations` - Create conversation
- `GET /api/messaging/conversations/{conversation_id}` - Get specific conversation
- `GET /api/messaging/conversations/{conversation_id}/messages` - Get messages
- `POST /api/messaging/conversations/{conversation_id}/messages` - Send message

### User Blocking Endpoints

- `GET /api/messaging/blocks` - Get all blocks
- `POST /api/messaging/blocks` - Block user

### Health Endpoint

- `GET /health` - Health check

## 📊 Test Results Format

### Success Indicators

- ✅ **Green checkmark**: Test passed
- ❌ **Red X**: Test failed
- ⏭️ **Skip arrow**: Test skipped
- ⚠️ **Warning**: Unexpected but acceptable result

### Detailed Reporting

Each test includes:

- **Timestamp**: When the test was executed
- **Method & Endpoint**: HTTP method and endpoint path
- **Status Code**: Actual vs expected status code
- **Response Data**: JSON response or error message
- **Description**: Human-readable test description

### Test Summary

- **Total Tests**: Count of all executed tests
- **Passed**: Count of successful tests
- **Failed**: Count of failed tests
- **Success Rate**: Percentage of successful tests
- **Failed Test Details**: List of failed tests with error messages

## 🔧 Configuration

### Base Configuration

```python
BASE_URL = "http://127.0.0.1:8000"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"
```

### Headers

```python
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}
```

## 🚀 Running Tests

### Prerequisites

1. FastAPI server running on `http://127.0.0.1:8000`
2. Database initialized with test data
3. Admin user created (username: `admin`, password: `admin`)

### Quick Start

```bash
# Start the FastAPI server
python main.py

# Run comprehensive tests
python test_comprehensive_detailed.py

# Run focused admin login tests
python test_admin_login.py
```

### Test Execution Order

1. **Health Check**: Verify server is running
2. **Admin Login**: Get authentication token
3. **Authentication Tests**: Test protected endpoints
4. **User Tests**: Test user management endpoints
5. **Role/Permission Tests**: Test role and permission endpoints
6. **Notification Tests**: Test notification system
7. **Messaging Tests**: Test messaging system
8. **Blocking Tests**: Test user blocking functionality

## 📈 Expected Results

### Successful Test Run

- All endpoints return expected status codes (200, 201, 204)
- Admin login returns valid JWT token
- Protected endpoints accessible with valid token
- Test data creation successful
- Error scenarios handled gracefully

### Common Issues & Solutions

- **401 Unauthorized**: Check admin credentials and token validity
- **404 Not Found**: Verify endpoint paths and server running
- **422 Unprocessable Entity**: Check request data format
- **500 Internal Server Error**: Check server logs for detailed error

## 🔍 Debugging

### Enable Debug Mode

Add debug logging to test scripts:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Server Logs

Monitor FastAPI server output for detailed error information.

### Verify Database State

Ensure test data exists and is accessible:

```bash
python setup_fixed.py
```

## 📝 Test Maintenance

### Adding New Tests

1. Add test function to appropriate test script
2. Include proper error handling
3. Add descriptive test name
4. Update documentation

### Updating Test Data

Modify test data creation functions to match current API schema.

### Extending Coverage

Add new test categories for additional endpoints or functionality.

---

**Last Updated**: December 2024
**Version**: 1.0
**Maintainer**: FastAPI Backend Team
