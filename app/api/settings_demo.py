"""
Settings Demo API - Demonstrates functional organization settings
"""
from typing import Optional

from fastapi import APIRouter, Depends
from sqlmodel import Session

from ..core.database import get_session
from ..core.security import get_current_user
from ..models.users import User
from ..services.organization_settings_service import OrganizationSettingsService

router = APIRouter()


@router.get("/my-effective-settings")
async def get_my_effective_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Demo endpoint showing the effective settings applied to the current user
    based on their organization configuration.
    """
    
    # Get user's organization settings
    org_settings = OrganizationSettingsService.get_user_organization_settings(db, current_user.id)
    
    if not org_settings:
        return {
            "message": "Personal account - using default settings",
            "account_type": "personal",
            "effective_settings": {
                "session_timeout_minutes": 60,
                "requires_2fa": False,
                "ip_restrictions": None,
                "storage_limit_gb": "unlimited"
            }
        }
    
    # Get all the functional settings
    session_timeout = OrganizationSettingsService.get_session_timeout_minutes(db, current_user.id)
    requires_2fa = OrganizationSettingsService.requires_2fa(db, current_user.id)
    allowed_ips = OrganizationSettingsService.get_allowed_ips(db, current_user.id)
    
    return {
        "message": "Organization member - settings enforced",
        "account_type": "business",
        "organization_settings": org_settings.model_dump(),
        "effective_settings": {
            "session_timeout_minutes": session_timeout,
            "requires_2fa": requires_2fa,
            "ip_restrictions": allowed_ips,
            "storage_limit_gb": org_settings.storage.limit_gb
        },
        "functional_features": {
            "session_timeout": "✅ JWT tokens expire based on org setting",
            "ip_restrictions": "✅ Middleware blocks unauthorized IPs",
            "storage_limits": "✅ PDF generation respects storage quota",
            "2fa_requirement": "✅ Login blocked if 2FA required but not enabled"
        }
    }


@router.get("/test-ip-check")
async def test_ip_restrictions(
    client_ip: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Demo endpoint to test IP restrictions functionality.
    Shows if the current request would be allowed based on organization IP settings.
    """
    
    test_ip = client_ip or "192.168.1.100"  # Default test IP
    
    is_allowed = OrganizationSettingsService.is_ip_allowed(db, current_user.id, test_ip)
    allowed_ips = OrganizationSettingsService.get_allowed_ips(db, current_user.id)
    
    return {
        "test_ip": test_ip,
        "is_allowed": is_allowed,
        "organization_ip_restrictions": allowed_ips,
        "message": (
            f"IP {test_ip} would be {'ALLOWED' if is_allowed else 'BLOCKED'} "
            f"{'(no restrictions)' if allowed_ips is None else 'by organization policy'}"
        )
    }


@router.get("/storage-usage")
async def get_organization_storage_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Demo endpoint showing organization storage usage and limits.
    """
    
    # Get user's organization
    from sqlmodel import select

    from ..models.organization import Organization, OrganizationUser
    
    org_user = db.exec(
        select(OrganizationUser)
        .join(Organization)
        .where(OrganizationUser.user_id == current_user.id)
    ).first()
    
    if not org_user:
        return {
            "account_type": "personal",
            "message": "Personal accounts have unlimited storage"
        }
    
    organization = org_user.organization
    settings = OrganizationSettingsService.get_organization_settings(db, organization.id)
    
    limit_bytes = settings.storage.limit_gb * 1024 * 1024 * 1024
    used_bytes = organization.storage_used or 0
    available_bytes = limit_bytes - used_bytes
    
    return {
        "account_type": "business",
        "organization_name": organization.name,
        "storage_limit_gb": settings.storage.limit_gb,
        "storage_used_bytes": used_bytes,
        "storage_used_mb": round(used_bytes / (1024 * 1024), 2),
        "storage_available_bytes": available_bytes,
        "storage_available_mb": round(available_bytes / (1024 * 1024), 2),
        "usage_percentage": round((used_bytes / limit_bytes) * 100, 2),
        "message": (
            f"Using {round((used_bytes / limit_bytes) * 100, 2)}% "
            f"of {settings.storage.limit_gb}GB storage quota"
        )
    }
