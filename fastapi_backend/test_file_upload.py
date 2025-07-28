#!/usr/bin/env python3
"""
File Upload and Preview Test Script
Tests Excel and CSV file upload, preview, and management functionality
"""

import requests
import json
import os
import tempfile
import pandas as pd
from datetime import datetime
from pathlib import Path

# Configuration
BASE_URL = "http://127.0.0.1:8000"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"

# Test results tracking
test_results = {
    "passed": 0,
    "failed": 0,
    "skipped": 0,
    "errors": []
}


def log_test_result(endpoint, method, status_code, expected_status, success, error_msg=None):
    """Log test result with detailed information"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    status_icon = "✅" if success else "❌"
    print(
        f"{status_icon} [{timestamp}] {method} {endpoint}: {status_code} (expected: {expected_status})")

    if not success and error_msg:
        print(f"    Error: {error_msg}")

    if success:
        test_results["passed"] += 1
    else:
        test_results["failed"] += 1
        test_results["errors"].append({
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "expected_status": expected_status,
            "error": error_msg
        })


def test_endpoint(method, endpoint, data=None, files=None, expected_status=200, description="", headers=None):
    """Test an endpoint with detailed reporting"""
    url = f"{BASE_URL}{endpoint}"

    if headers is None:
        headers = {
            "Content-Type": "application/json"
        }

    if description:
        print(f"\n🔍 Testing: {description}")
        print(f"   Endpoint: {method} {endpoint}")

    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            if files:
                # Remove Content-Type for file uploads
                headers.pop("Content-Type", None)
                response = requests.post(
                    url, headers=headers, files=files, data=data)
            else:
                response = requests.post(url, headers=headers, json=data)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            print(f"❌ Unsupported method: {method}")
            test_results["failed"] += 1
            return None

        success = response.status_code == expected_status

        if success:
            try:
                result = response.json()
                if isinstance(result, dict) and len(result) > 0:
                    print(
                        f"    Response: {json.dumps(result, indent=4)[:300]}...")
                else:
                    print(f"    Response: {result}")
            except:
                print(f"    Response: {response.text[:200]}...")
        else:
            print(
                f"    Expected: {expected_status}, Got: {response.status_code}")
            print(f"    Error Response: {response.text}")

        log_test_result(endpoint, method, response.status_code,
                        expected_status, success, response.text if not success else None)
        return response

    except Exception as e:
        error_msg = f"Request failed: {str(e)}"
        log_test_result(endpoint, method, 0, expected_status, False, error_msg)
        return None


def create_test_csv_file():
    """Create a test CSV file"""
    data = {
        'Name': ['John Doe', 'Jane Smith', 'Bob Johnson', 'Alice Brown', 'Charlie Wilson'],
        'Age': [30, 25, 35, 28, 32],
        'Email': ['john@example.com', 'jane@example.com', 'bob@example.com', 'alice@example.com', 'charlie@example.com'],
        'Department': ['IT', 'HR', 'Sales', 'Marketing', 'Engineering'],
        'Salary': [75000, 65000, 80000, 70000, 90000]
    }

    df = pd.DataFrame(data)

    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(
        mode='w', suffix='.csv', delete=False)
    df.to_csv(temp_file.name, index=False)
    temp_file.close()

    return temp_file.name


def create_test_excel_file():
    """Create a test Excel file with multiple sheets"""
    # Create sample data for multiple sheets
    employees_data = {
        'Name': ['John Doe', 'Jane Smith', 'Bob Johnson', 'Alice Brown', 'Charlie Wilson'],
        'Age': [30, 25, 35, 28, 32],
        'Email': ['john@example.com', 'jane@example.com', 'bob@example.com', 'alice@example.com', 'charlie@example.com'],
        'Department': ['IT', 'HR', 'Sales', 'Marketing', 'Engineering'],
        'Salary': [75000, 65000, 80000, 70000, 90000]
    }

    departments_data = {
        'Department': ['IT', 'HR', 'Sales', 'Marketing', 'Engineering'],
        'Manager': ['John Manager', 'Jane Manager', 'Bob Manager', 'Alice Manager', 'Charlie Manager'],
        'Budget': [1000000, 500000, 800000, 600000, 1200000],
        'Employees': [15, 8, 12, 10, 20]
    }

    projects_data = {
        'Project': ['Website Redesign', 'Mobile App', 'Database Migration', 'Cloud Migration', 'Security Audit'],
        'Status': ['In Progress', 'Completed', 'Planning', 'In Progress', 'Completed'],
        'Start Date': ['2024-01-15', '2023-11-01', '2024-02-01', '2024-01-01', '2023-12-01'],
        'End Date': ['2024-06-15', '2024-01-15', '2024-05-01', '2024-12-01', '2024-02-15'],
        'Budget': [50000, 75000, 30000, 100000, 25000]
    }

    # Create temporary Excel file
    temp_file = tempfile.NamedTemporaryFile(
        mode='w', suffix='.xlsx', delete=False)
    temp_file.close()

    with pd.ExcelWriter(temp_file.name, engine='openpyxl') as writer:
        pd.DataFrame(employees_data).to_excel(
            writer, sheet_name='Employees', index=False)
        pd.DataFrame(departments_data).to_excel(
            writer, sheet_name='Departments', index=False)
        pd.DataFrame(projects_data).to_excel(
            writer, sheet_name='Projects', index=False)

    return temp_file.name


def test_admin_login():
    """Test admin login and get token"""
    print("\n" + "="*60)
    print("🔐 ADMIN LOGIN FOR FILE UPLOAD TESTING")
    print("="*60)

    login_data = {
        "username": ADMIN_USERNAME,
        "password": ADMIN_PASSWORD
    }

    response = test_endpoint(
        "POST",
        "/api/auth/login",
        login_data,
        200,
        "Admin Login for File Upload Testing"
    )

    if response and response.status_code == 200:
        result = response.json()
        token = result.get("access_token")
        if token:
            print(f"✅ Admin login successful! Token obtained.")
            return token
        else:
            print("❌ Admin login failed: No token in response")
            return None
    else:
        print("❌ Admin login failed")
        return None


def test_file_upload_endpoints(token):
    """Test file upload endpoints"""
    print("\n" + "="*60)
    print("📁 FILE UPLOAD ENDPOINTS TESTING")
    print("="*60)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Test get user files (should be empty initially)
    test_endpoint("GET", "/api/files/", headers=headers,
                  description="Get User Files (Empty)")

    # Test file statistics
    test_endpoint("GET", "/api/files/stats/summary", headers=headers,
                  description="Get File Upload Statistics")


def test_csv_upload(token):
    """Test CSV file upload"""
    print("\n" + "="*60)
    print("📊 CSV FILE UPLOAD TESTING")
    print("="*60)

    headers = {
        "Authorization": f"Bearer {token}"
    }

    # Create test CSV file
    csv_file_path = create_test_csv_file()

    try:
        with open(csv_file_path, 'rb') as f:
            files = {'file': ('test_data.csv', f, 'text/csv')}

            response = test_endpoint(
                "POST",
                "/api/files/upload",
                files=files,
                headers=headers,
                description="Upload CSV File"
            )

        if response and response.status_code == 200:
            result = response.json()
            file_id = result.get("id")
            print(f"✅ CSV file uploaded successfully! File ID: {file_id}")
            return file_id
        else:
            print("❌ CSV file upload failed")
            return None

    finally:
        # Clean up temporary file
        if os.path.exists(csv_file_path):
            os.unlink(csv_file_path)

    return None


def test_excel_upload(token):
    """Test Excel file upload"""
    print("\n" + "="*60)
    print("📈 EXCEL FILE UPLOAD TESTING")
    print("="*60)

    headers = {
        "Authorization": f"Bearer {token}"
    }

    # Create test Excel file
    excel_file_path = create_test_excel_file()

    try:
        with open(excel_file_path, 'rb') as f:
            files = {'file': (
                'test_data.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}

            response = test_endpoint(
                "POST",
                "/api/files/upload",
                files=files,
                headers=headers,
                description="Upload Excel File"
            )

        if response and response.status_code == 200:
            result = response.json()
            file_id = result.get("id")
            print(f"✅ Excel file uploaded successfully! File ID: {file_id}")
            return file_id
        else:
            print("❌ Excel file upload failed")
            return None

    finally:
        # Clean up temporary file
        if os.path.exists(excel_file_path):
            os.unlink(excel_file_path)

    return None


def test_file_preview_endpoints(token, csv_file_id=None, excel_file_id=None):
    """Test file preview endpoints"""
    print("\n" + "="*60)
    print("👁️ FILE PREVIEW ENDPOINTS TESTING")
    print("="*60)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Test CSV file preview
    if csv_file_id:
        test_endpoint("GET", f"/api/files/{csv_file_id}", headers=headers,
                      description=f"Get CSV File Details (ID: {csv_file_id})")

        test_endpoint("GET", f"/api/files/{csv_file_id}/previews", headers=headers,
                      description=f"Get CSV File Previews (ID: {csv_file_id})")

        test_endpoint("GET", f"/api/files/{csv_file_id}/status", headers=headers,
                      description=f"Get CSV File Processing Status (ID: {csv_file_id})")

    # Test Excel file preview
    if excel_file_id:
        test_endpoint("GET", f"/api/files/{excel_file_id}", headers=headers,
                      description=f"Get Excel File Details (ID: {excel_file_id})")

        test_endpoint("GET", f"/api/files/{excel_file_id}/previews", headers=headers,
                      description=f"Get Excel File Previews (ID: {excel_file_id})")

        test_endpoint("GET", f"/api/files/{excel_file_id}/status", headers=headers,
                      description=f"Get Excel File Processing Status (ID: {excel_file_id})")

    # Test generate new preview
    if csv_file_id:
        preview_request = {
            "max_rows": 5,
            "sheet_name": None
        }
        test_endpoint("POST", f"/api/files/{csv_file_id}/preview", preview_request, headers=headers,
                      description=f"Generate New CSV Preview (ID: {csv_file_id})")

    if excel_file_id:
        preview_request = {
            "max_rows": 3,
            "sheet_name": "Employees"
        }
        test_endpoint("POST", f"/api/files/{excel_file_id}/preview", preview_request, headers=headers,
                      description=f"Generate New Excel Preview (ID: {excel_file_id})")


def test_file_management_endpoints(token, csv_file_id=None, excel_file_id=None):
    """Test file management endpoints"""
    print("\n" + "="*60)
    print("🗂️ FILE MANAGEMENT ENDPOINTS TESTING")
    print("="*60)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Test get user files (should now have uploaded files)
    test_endpoint("GET", "/api/files/", headers=headers,
                  description="Get User Files (With Uploaded Files)")

    # Test file statistics
    test_endpoint("GET", "/api/files/stats/summary", headers=headers,
                  description="Get Updated File Upload Statistics")

    # Test download files
    if csv_file_id:
        test_endpoint("GET", f"/api/files/{csv_file_id}/download", headers=headers,
                      description=f"Download CSV File (ID: {csv_file_id})")

    if excel_file_id:
        test_endpoint("GET", f"/api/files/{excel_file_id}/download", headers=headers,
                      description=f"Download Excel File (ID: {excel_file_id})")


def test_invalid_file_upload(token):
    """Test invalid file upload scenarios"""
    print("\n" + "="*60)
    print("❌ INVALID FILE UPLOAD TESTING")
    print("="*60)

    headers = {
        "Authorization": f"Bearer {token}"
    }

    # Test uploading text file (should fail)
    temp_file = tempfile.NamedTemporaryFile(
        mode='w', suffix='.txt', delete=False)
    temp_file.write("This is a text file, not CSV or Excel")
    temp_file.close()

    try:
        with open(temp_file.name, 'rb') as f:
            files = {'file': ('test.txt', f, 'text/plain')}

            test_endpoint(
                "POST",
                "/api/files/upload",
                files=files,
                headers=headers,
                expected_status=400,
                description="Upload Invalid File Type (Text)"
            )
    finally:
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)

    # Test uploading without file
    test_endpoint(
        "POST",
        "/api/files/upload",
        headers=headers,
        expected_status=422,
        description="Upload Without File"
    )


def test_file_cleanup(token, csv_file_id=None, excel_file_id=None):
    """Test file deletion"""
    print("\n" + "="*60)
    print("🗑️ FILE CLEANUP TESTING")
    print("="*60)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Test delete files
    if csv_file_id:
        test_endpoint("DELETE", f"/api/files/{csv_file_id}", headers=headers,
                      description=f"Delete CSV File (ID: {csv_file_id})")

    if excel_file_id:
        test_endpoint("DELETE", f"/api/files/{excel_file_id}", headers=headers,
                      description=f"Delete Excel File (ID: {excel_file_id})")

    # Verify files are deleted
    test_endpoint("GET", "/api/files/", headers=headers,
                  description="Get User Files (After Deletion)")


def print_test_summary():
    """Print comprehensive test summary"""
    print("\n" + "="*60)
    print("📊 FILE UPLOAD TEST SUMMARY")
    print("="*60)

    total_tests = test_results["passed"] + \
        test_results["failed"] + test_results["skipped"]

    print(f"Total Tests: {total_tests}")
    print(f"✅ Passed: {test_results['passed']}")
    print(f"❌ Failed: {test_results['failed']}")
    print(f"⏭️  Skipped: {test_results['skipped']}")

    if test_results["failed"] > 0:
        success_rate = (test_results["passed"] / total_tests) * 100
        print(f"Success Rate: {success_rate:.1f}%")

        print("\n❌ Failed Tests:")
        for error in test_results["errors"]:
            print(
                f"  - {error['method']} {error['endpoint']}: {error['status_code']} (expected: {error['expected_status']})")
            if error['error']:
                print(f"    Error: {error['error'][:100]}...")
    else:
        print("🎉 All file upload tests passed successfully!")


def main():
    """Main test execution function"""
    print("🚀 FILE UPLOAD & PREVIEW COMPREHENSIVE TESTING")
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    try:
        # Test admin login
        token = test_admin_login()

        if not token:
            print("❌ Cannot proceed without valid admin token")
            return

        # Test file upload endpoints
        test_file_upload_endpoints(token)

        # Test CSV file upload
        csv_file_id = test_csv_upload(token)

        # Test Excel file upload
        excel_file_id = test_excel_upload(token)

        # Test file preview endpoints
        test_file_preview_endpoints(token, csv_file_id, excel_file_id)

        # Test file management endpoints
        test_file_management_endpoints(token, csv_file_id, excel_file_id)

        # Test invalid file upload scenarios
        test_invalid_file_upload(token)

        # Test file cleanup
        test_file_cleanup(token, csv_file_id, excel_file_id)

        # Print final summary
        print_test_summary()

    except KeyboardInterrupt:
        print("\n⚠️  Testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        test_results["failed"] += 1

    print(
        f"\n🏁 File upload testing completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
