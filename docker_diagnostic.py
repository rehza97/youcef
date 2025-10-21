#!/usr/bin/env python3
"""
Docker Services Diagnostic Script
Identifies why only database starts but not backend/frontend
"""

import subprocess
import sys
import time
import json
import os


def run_command(cmd, description, capture_output=True):
    """Run a command and return result"""
    print(f"🔍 {description}")
    print(f"   Command: {cmd}")

    try:
        if capture_output:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                print(f"   ✅ Success")
                if result.stdout.strip():
                    print(f"   Output: {result.stdout.strip()}")
                return True, result.stdout.strip()
            else:
                print(f"   ❌ Failed: {result.stderr.strip()}")
                return False, result.stderr.strip()
        else:
            result = subprocess.run(cmd, shell=True, timeout=60)
            return result.returncode == 0, ""
    except subprocess.TimeoutExpired:
        print(f"   ⏰ Timeout: Command took too long")
        return False, "Timeout"
    except Exception as e:
        print(f"   💥 Error: {e}")
        return False, str(e)


def check_docker_status():
    """Check if Docker is running"""
    print("=" * 70)
    print("  DOCKER STATUS CHECK")
    print("=" * 70)
    print()

    success, output = run_command(
        "docker --version", "Check Docker installation")
    if not success:
        print("❌ Docker is not installed or not in PATH")
        return False

    success, output = run_command("docker info", "Check Docker daemon status")
    if not success:
        print("❌ Docker daemon is not running")
        print("   Please start Docker Desktop")
        return False

    print("✅ Docker is running")
    return True


def check_containers():
    """Check container status"""
    print("=" * 70)
    print("  CONTAINER STATUS CHECK")
    print("=" * 70)
    print()

    success, output = run_command(
        "docker ps -a --filter name=youcef", "Check Youcef containers")
    if success and output:
        print("📋 Container Status:")
        lines = output.split('\n')
        for line in lines[1:]:  # Skip header
            if line.strip():
                parts = line.split()
                if len(parts) >= 2:
                    name = parts[-1]
                    status = parts[4] if len(parts) > 4 else "unknown"
                    print(f"   {name}: {status}")
    else:
        print("❌ No Youcef containers found")
        return False

    return True


def check_networks():
    """Check Docker networks"""
    print("=" * 70)
    print("  NETWORK STATUS CHECK")
    print("=" * 70)
    print()

    success, output = run_command("docker network ls", "List Docker networks")
    if success:
        if "youcef" in output:
            print("✅ Youcef network exists")
        else:
            print("❌ Youcef network not found")
            return False

    success, output = run_command(
        "docker network inspect youcef_youcef_network", "Inspect Youcef network")
    if success:
        try:
            network_info = json.loads(output)
            containers = network_info[0].get('Containers', {})
            print(f"📋 Connected containers: {len(containers)}")
            for container_id, container_info in containers.items():
                name = container_info.get('Name', 'unknown')
                print(f"   - {name}")
        except:
            print("   Could not parse network info")

    return True


def check_build_logs():
    """Check build logs for errors"""
    print("=" * 70)
    print("  BUILD LOGS CHECK")
    print("=" * 70)
    print()

    # Check if Docker images exist
    success, output = run_command(
        "docker images | grep youcef", "Check Youcef images")
    if success and output:
        print("✅ Youcef images found:")
        for line in output.split('\n'):
            if line.strip():
                print(f"   {line}")
    else:
        print("❌ No Youcef images found - need to build")
        return False

    return True


def check_dockerfile_issues():
    """Check for Dockerfile issues"""
    print("=" * 70)
    print("  DOCKERFILE ISSUES CHECK")
    print("=" * 70)
    print()

    # Check if Dockerfiles exist
    if not os.path.exists("Dockerfile.backend"):
        print("❌ Dockerfile.backend not found")
        return False
    else:
        print("✅ Dockerfile.backend exists")

    if not os.path.exists("Dockerfile.frontend"):
        print("❌ Dockerfile.frontend not found")
        return False
    else:
        print("✅ Dockerfile.frontend exists")

    # Check if source directories exist
    if not os.path.exists("fastapi_backend"):
        print("❌ fastapi_backend directory not found")
        return False
    else:
        print("✅ fastapi_backend directory exists")

    if not os.path.exists("frontend"):
        print("❌ frontend directory not found")
        return False
    else:
        print("✅ frontend directory exists")

    # Check if requirements files exist
    if not os.path.exists("fastapi_backend/requirements.txt"):
        print("❌ fastapi_backend/requirements.txt not found")
        return False
    else:
        print("✅ fastapi_backend/requirements.txt exists")

    if not os.path.exists("frontend/package.json"):
        print("❌ frontend/package.json not found")
        return False
    else:
        print("✅ frontend/package.json exists")

    return True


def check_docker_compose():
    """Check docker-compose configuration"""
    print("=" * 70)
    print("  DOCKER COMPOSE CHECK")
    print("=" * 70)
    print()

    if not os.path.exists("docker-compose.yml"):
        print("❌ docker-compose.yml not found")
        return False
    else:
        print("✅ docker-compose.yml exists")

    # Validate docker-compose syntax
    success, output = run_command(
        "docker-compose config", "Validate docker-compose.yml")
    if success:
        print("✅ docker-compose.yml is valid")
    else:
        print("❌ docker-compose.yml has syntax errors:")
        print(f"   {output}")
        return False

    return True


def test_build_services():
    """Test building services individually"""
    print("=" * 70)
    print("  INDIVIDUAL SERVICE BUILD TEST")
    print("=" * 70)
    print()

    # Test backend build
    print("🔨 Testing backend build...")
    success, output = run_command(
        "docker build -f Dockerfile.backend -t youcef-backend-test .", "Build backend")
    if success:
        print("✅ Backend builds successfully")
    else:
        print("❌ Backend build failed:")
        print(f"   {output}")
        return False

    # Test frontend build
    print("🔨 Testing frontend build...")
    success, output = run_command(
        "docker build -f Dockerfile.frontend -t youcef-frontend-test .", "Build frontend")
    if success:
        print("✅ Frontend builds successfully")
    else:
        print("❌ Frontend build failed:")
        print(f"   {output}")
        return False

    return True


def check_service_logs():
    """Check logs of running services"""
    print("=" * 70)
    print("  SERVICE LOGS CHECK")
    print("=" * 70)
    print()

    services = ["youcef_postgres", "youcef_backend", "youcef_frontend"]

    for service in services:
        print(f"📋 Checking logs for {service}...")
        success, output = run_command(
            f"docker logs {service} --tail 20", f"Get logs for {service}")
        if success and output:
            print(f"   Last 20 lines of {service}:")
            for line in output.split('\n')[-10:]:  # Show last 10 lines
                if line.strip():
                    print(f"   {line}")
        else:
            print(f"   No logs found for {service}")


def main():
    """Main diagnostic function"""
    print("🚀 Starting Docker Services Diagnostic...")
    print()

    # Step 1: Check Docker status
    if not check_docker_status():
        print("\n❌ Docker is not running. Please start Docker Desktop first.")
        return 1

    print()

    # Step 2: Check Dockerfile issues
    if not check_dockerfile_issues():
        print("\n❌ Missing required files. Please check your project structure.")
        return 1

    print()

    # Step 3: Check docker-compose
    if not check_docker_compose():
        print("\n❌ Docker Compose configuration has issues.")
        return 1

    print()

    # Step 4: Check containers
    check_containers()
    print()

    # Step 5: Check networks
    check_networks()
    print()

    # Step 6: Check build logs
    check_build_logs()
    print()

    # Step 7: Test individual builds
    if not test_build_services():
        print("\n❌ Individual service builds failed.")
        return 1

    print()

    # Step 8: Check service logs
    check_service_logs()
    print()

    # Final recommendations
    print("=" * 70)
    print("  DIAGNOSTIC COMPLETE")
    print("=" * 70)
    print()
    print("🔧 Common Solutions:")
    print("1. Clean and rebuild:")
    print("   docker-compose down")
    print("   docker-compose build --no-cache")
    print("   docker-compose up")
    print()
    print("2. Check specific service logs:")
    print("   docker-compose logs backend")
    print("   docker-compose logs frontend")
    print()
    print("3. Start services individually:")
    print("   docker-compose up postgres")
    print("   docker-compose up backend")
    print("   docker-compose up frontend")
    print()
    print("4. Check for port conflicts:")
    print("   netstat -an | findstr :8001")
    print("   netstat -an | findstr :3000")
    print("   netstat -an | findstr :5432")

    return 0


if __name__ == "__main__":
    sys.exit(main())
