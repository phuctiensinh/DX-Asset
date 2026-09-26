from typing import Generator, List, Callable, Optional
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.models.enums import UserRole

import logging
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False
)

def get_current_user(
    token: Optional[str] = Depends(reusable_oauth2),
    token_param: Optional[str] = Query(None, alias="token"),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to extract and validate current authenticated user from Bearer token or Query token param.
    Prioritizes keycloak_user_id lookup, handles first-time identity linking by email,
    and performs safe transactional JIT provisioning for new users.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    effective_token = token or token_param
    if not effective_token:
        raise credentials_exception

    payload = decode_access_token(effective_token)

    if not payload:
        raise credentials_exception

    sub: Optional[str] = payload.get("sub")
    email: Optional[str] = payload.get("email") or payload.get("preferred_username")

    if not sub and not email:
        raise credentials_exception

    user: Optional[User] = None

    # 1. Primary Lookup: Match keycloak_user_id == sub (Fast indexed lookup)
    if sub and not sub.isdigit():
        user = db.query(User).filter(User.keycloak_user_id == sub).first()

    # 2. Legacy Lookup: Match integer ID for internal HS256 tokens (Backward compatibility)
    if not user and sub and sub.isdigit():
        user = db.query(User).filter(User.id == int(sub)).first()

    # 3. First-Time Identity Linking: Match by email if keycloak_user_id is not yet set
    if not user and email:
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            # Check for identity conflict (if existing user is already linked to a different Keycloak sub)
            if existing_user.keycloak_user_id and existing_user.keycloak_user_id != sub:
                logger.warning(
                    f"Identity conflict: User '{email}' is linked to Keycloak sub '{existing_user.keycloak_user_id}', "
                    f"but incoming token sub is '{sub}'"
                )
                raise credentials_exception

            # Safe initial linking: attach keycloak_user_id to existing user record
            if not existing_user.keycloak_user_id and sub and not sub.isdigit():
                try:
                    existing_user.keycloak_user_id = sub
                    db.commit()
                    db.refresh(existing_user)
                    logger.info(f"Successfully linked Keycloak sub '{sub}' to local user '{email}'")
                except IntegrityError:
                    db.rollback()
                    existing_user = db.query(User).filter(User.keycloak_user_id == sub).first()

            user = existing_user

    # 4. Transactional JIT Provisioning for newly registered Keycloak users
    token_iss = payload.get("iss", "")
    iss_valid = token_iss and token_iss.rstrip("/") == settings.KEYCLOAK_ISSUER_URL.rstrip("/")
    if not user and email and sub and not sub.isdigit() and iss_valid:
        full_name = (payload.get("name") or payload.get("preferred_username") or email)[:100]
        clean_email = email[:100]
        assigned_role = UserRole.ADMIN if clean_email == SYSTEM_OWNER_EMAIL else UserRole.EMPLOYEE
        try:
            user = User(
                keycloak_user_id=sub,
                email=clean_email,
                password_hash="EXTERNAL_KEYCLOAK_AUTHENTICATED",
                full_name=full_name,
                role=assigned_role,
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"JIT Provisioned new local user '{clean_email}' with sub '{sub}' and role '{assigned_role}'")

        except Exception as exc:
            db.rollback()
            logger.warning(f"JIT Provisioning error for '{clean_email}' (sub '{sub}'): {exc}")
            # Concurrency handling: Re-query DB for user created by concurrent request
            user = db.query(User).filter(
                (User.keycloak_user_id == sub) | (User.email == clean_email)
            ).first()

    if not user:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive"
        )

    return user

class RoleChecker:
    """Dependency helper to enforce Role-Based Access Control (RBAC)."""
    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted for this user role"
            )
        return current_user

def require_roles(*roles: UserRole) -> Callable:
    """Helper function to instantiate RoleChecker dependency."""
    return RoleChecker(list(roles))
