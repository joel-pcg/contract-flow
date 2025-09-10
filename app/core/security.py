from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import Session, select

from ..models.organization import Organization, OrganizationUser
from ..models.users import UUID, User
from ..services.redis_service import redis_service
from .config import get_settings
from .database import get_session

settings = get_settings()
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_minutes: Optional[int] = None):
    to_encode = data.copy()
    # Use custom timeout or default
    minutes = expires_minutes if expires_minutes is not None else settings.ACCESS_TOKEN_EXPIRE_MINUTES
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    session: Session = Depends(get_session)
) -> User:
    if redis_service.is_blacklisted(credentials.credentials):
        raise HTTPException(status_code=401, detail="Token has been revoked")

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401)
        user = session.get(User, UUID(user_id))
        if not user:
            raise HTTPException(status_code=401)
        return user
    except JWTError:
        raise HTTPException(status_code=401)


async def get_current_user_with_org(
    credentials: HTTPAuthorizationCredentials = Security(security),
    session: Session = Depends(get_session)
) -> tuple[User, Optional[Organization]]:
    """
    Obtiene el usuario actual y su organización activa con información detallada.

    Returns:
        tuple[User, Optional[Organization]]: Usuario actual y su organización si existe
    """
    if redis_service.is_blacklisted(credentials.credentials):
        raise HTTPException(
            status_code=401,
            detail="Token has been revoked"
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401)

        # Consulta optimizada que obtiene el usuario y su organización en una sola query
        query = (
            select(User, Organization)
            .join(OrganizationUser, User.id == OrganizationUser.user_id)
            .join(Organization, OrganizationUser.organization_id == Organization.id)
            .where(User.id == UUID(user_id))
        )

        result = session.exec(query).first()

        if not result:
            # Si no hay resultado con join, intentamos obtener solo el usuario
            user = session.get(User, UUID(user_id))
            if not user:
                raise HTTPException(status_code=401, detail="User not found")
            return user, None

        user, organization = result
        return user, organization

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials"
        )
