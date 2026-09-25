from datetime import datetime, timedelta, timezone
from typing import Any, Union, Optional, Dict
from passlib.context import CryptContext
import logging
import jwt
from jwt import PyJWKClient
from app.core.config import settings

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_jwks_client: Optional[PyJWKClient] = None

def get_jwks_client() -> Optional[PyJWKClient]:
    """Retrieve or initialize cached PyJWKClient instance for Keycloak JWKS endpoint."""
    global _jwks_client
    if _jwks_client is None and settings.KEYCLOAK_JWKS_URL:
        try:
            _jwks_client = PyJWKClient(
                settings.KEYCLOAK_JWKS_URL,
                cache_keys=True,
                max_cached_keys=16,
                cache_jwk_set=True
            )
        except Exception as e:
            logger.error(f"Failed to initialize PyJWKClient for '{settings.KEYCLOAK_JWKS_URL}': {e}")
    return _jwks_client

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against its hashed version using Bcrypt."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password using Bcrypt."""
    return pwd_context.hash(password)

def create_access_token(
    subject: Union[str, Any],
    extra_claims: Optional[Dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Generate a signed JWT access token with expiration and claims."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode: Dict[str, Any] = {"sub": str(subject), "exp": expire}
    if extra_claims:
        to_encode.update(extra_claims)
        
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a JWT access token.
    Supports Keycloak RS256 token verification via JWKS, as well as legacy HS256 tokens.
    """
    if not token:
        return None

    try:
        unverified_header = jwt.get_unverified_header(token)
        alg = unverified_header.get("alg")

        if alg == "RS256" and settings.KEYCLOAK_ENABLED:
            client = get_jwks_client()
            if not client:
                logger.warning("JWKS client unavailable for RS256 verification")
                return None

            try:
                signing_key = client.get_signing_key_from_jwt(token)
            except Exception as e:
                logger.warning(f"Failed to retrieve signing key for token kid: {e}")
                return None

            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iss": False,  # Verified explicitly below with trailing-slash normalization
                    "verify_aud": False,  # Keycloak public browser clients use 'azp'
                }
            )

            # Strict Issuer Verification with trailing-slash normalization
            iss = payload.get("iss")
            expected_iss = settings.KEYCLOAK_ISSUER_URL
            if not iss or (expected_iss and iss.rstrip("/") != expected_iss.rstrip("/")):
                logger.warning(f"Token issuer '{iss}' does not match expected issuer '{expected_iss}'")
                return None

            # Verify Authorized Party (azp) or Audience (aud) against expected Client ID
            azp = payload.get("azp")
            aud = payload.get("aud")
            client_id = settings.KEYCLOAK_CLIENT_ID
            if client_id:
                client_matched = False
                if azp and azp == client_id:
                    client_matched = True
                elif isinstance(aud, str) and aud == client_id:
                    client_matched = True
                elif isinstance(aud, list) and client_id in aud:
                    client_matched = True
                elif not azp and not aud:
                    client_matched = True

                if not client_matched:
                    logger.warning(f"Token azp '{azp}' / aud '{aud}' does not match expected client ID '{client_id}'")
                    return None

            return payload

        elif alg == "HS256":
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            return payload

        else:
            logger.warning(f"Unsupported JWT algorithm '{alg}'")
            return None

    except jwt.PyJWTError as e:
        logger.warning(f"JWT validation error: {e}")
        return None
    except Exception as e:
        logger.warning(f"Unexpected token error: {e}")
        return None
