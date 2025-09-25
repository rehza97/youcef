from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta

from database.connection import get_db
from core.security import (
    verify_password, get_password_hash, create_access_token,
    create_refresh_token, verify_token, validate_password_strength,
    get_current_user
)
from core.rate_limiter import login_rate_limiter, register_rate_limiter
from models.user import User, UserCreate, UserLogin, UserResponse
from core.security import Token
from pydantic import BaseModel
from core.config import settings

auth_router = APIRouter()
security = HTTPBearer()


class RefreshTokenRequest(BaseModel):
    refresh_token: str


@auth_router.post("/register", response_model=dict)
async def register(
    user_data: UserCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Register a new user"""
    # Rate limiting
    await register_rate_limiter.check_register_rate_limit(request)

    # Validate password strength
    if not validate_password_strength(user_data.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long and contain uppercase, lowercase, and numeric characters"
        )

    # Check if username already exists
    existing_user = db.query(User).filter(
        User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    # Check if email already exists
    existing_email = db.query(User).filter(
        User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        bio=user_data.bio,
        avatar_url=user_data.avatar_url
    )

    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        return {
            "success": True,
            "message": "User registered successfully",
            "data": {
                "id": db_user.id,
                "username": db_user.username,
                "email": db_user.email
            }
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating user"
        )


@auth_router.post("/login")
async def login(
    user_credentials: UserLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """Login user and return tokens"""
    # Rate limiting
    await login_rate_limiter.check_login_rate_limit(request)

    # Find user by username or email
    user = db.query(User).filter(
        (User.username == user_credentials.username) |
        (User.email == user_credentials.username)
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password"
        )

    # Verify password
    if not verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password"
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled"
        )

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()

    # Create tokens
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id}
    )
    refresh_token = create_refresh_token(
        data={"sub": user.username, "user_id": user.id}
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_active": user.is_active,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
            "last_login": user.last_login,
            "date_joined": user.date_joined
        }
    }


@auth_router.post("/logout")
async def logout(
    current_user=Depends(security),
    db: Session = Depends(get_db)
):
    """Logout user (invalidate token)"""
    # In a real implementation, you might want to blacklist the token
    # For now, we'll just return a success message
    return {
        "success": True,
        "message": "Successfully logged out"
    }


@auth_router.post("/refresh-token", response_model=Token)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token"""
    try:
        # Verify refresh token
        payload = verify_token(request.refresh_token)

        # Get user
        user = db.query(User).filter(User.id == payload.user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        # Create new access token
        access_token = create_access_token(
            data={"sub": user.username, "user_id": user.id}
        )
        new_refresh_token = create_refresh_token(
            data={"sub": user.username, "user_id": user.id}
        )

        return Token(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@auth_router.get("/protected")
async def protected_endpoint(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Test protected endpoint"""
    return {
        "success": True,
        "message": "This is a protected endpoint",
        "user": {
            "username": current_user.username,
            "user_id": current_user.id
        }
    }


@auth_router.get("/test-cors")
async def test_cors():
    """Test CORS endpoint"""
    return {
        "message": "CORS test successful",
        "timestamp": datetime.utcnow().isoformat()
    }
