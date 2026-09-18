from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core.security import verify_password, create_access_token
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserResponse

router = APIRouter()

@router.post("/login", response_model=TokenResponse, tags=["Authentication"])
def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """Authenticate user with email & password, returning a JWT access token."""
    user = db.query(User).filter(User.email == request.email).first()
    
    # Generic authentication error to avoid user enumeration
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not user:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
        )

    if not verify_password(request.password, user.password_hash):
        raise credentials_exception

    access_token = create_access_token(
        subject=user.id,
        extra_claims={
            "email": user.email,
            "role": str(user.role)
        }
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )

@router.get("/me", response_model=UserResponse, tags=["Authentication"])
def get_me(
    current_user: User = Depends(get_current_user)
):
    """Fetch profile information for the currently authenticated user."""
    return UserResponse.model_validate(current_user)
