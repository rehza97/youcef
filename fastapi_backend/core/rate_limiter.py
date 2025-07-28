from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer
import time
from typing import Dict, Tuple
import asyncio
from core.config import settings


class RateLimiter:
    """Rate limiter for API endpoints"""

    def __init__(self):
        self.requests: Dict[str, list] = {}
        self.limits = {
            "anon": (100, 3600),  # 100 requests per hour
            "user": (1000, 3600),  # 1000 requests per hour
            "login": (5, 60),      # 5 requests per minute
            "register": (3, 60),   # 3 requests per minute
        }

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0]
        return request.client.host

    def _get_user_identifier(self, request: Request) -> str:
        """Get user identifier for rate limiting"""
        # Try to get user from token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # For authenticated users, use a different identifier
            return f"user_{self._get_client_ip(request)}"
        return f"anon_{self._get_client_ip(request)}"

    def _clean_old_requests(self, identifier: str, window: int):
        """Clean old requests outside the time window"""
        current_time = time.time()
        if identifier in self.requests:
            self.requests[identifier] = [
                req_time for req_time in self.requests[identifier]
                if current_time - req_time < window
            ]

    def _check_limit(self, identifier: str, limit_type: str = "anon") -> bool:
        """Check if request is within rate limit"""
        max_requests, window = self.limits[limit_type]

        # Clean old requests
        self._clean_old_requests(identifier, window)

        # Check current requests
        current_requests = len(self.requests.get(identifier, []))

        if current_requests >= max_requests:
            return False

        # Add current request
        if identifier not in self.requests:
            self.requests[identifier] = []
        self.requests[identifier].append(time.time())

        return True

    async def check_rate_limit(self, request: Request, limit_type: str = "anon"):
        """Check rate limit for the request"""
        identifier = self._get_user_identifier(request)

        # Determine limit type based on endpoint
        path = request.url.path
        if "/login" in path:
            limit_type = "login"
        elif "/register" in path:
            limit_type = "register"
        elif identifier.startswith("user_"):
            limit_type = "user"

        if not self._check_limit(identifier, limit_type):
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Too many requests for {limit_type}."
            )


class LoginRateLimiter(RateLimiter):
    """Rate limiter specifically for login endpoints"""

    async def check_login_rate_limit(self, request: Request):
        """Check rate limit for login"""
        await self.check_rate_limit(request, "login")


class RegisterRateLimiter(RateLimiter):
    """Rate limiter specifically for register endpoints"""

    async def check_register_rate_limit(self, request: Request):
        """Check rate limit for register"""
        await self.check_rate_limit(request, "register")


# Create instances
rate_limiter = RateLimiter()
login_rate_limiter = LoginRateLimiter()
register_rate_limiter = RegisterRateLimiter()
