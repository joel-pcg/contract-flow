"""
Organization Settings Service - Makes settings functional, not just decorative
"""
import logging
from typing import List, Optional
from uuid import UUID

from sqlmodel import Session, select

from ..models.organization import Organization, OrganizationUser
from ..schemas.organization import (
    NotificationSettings,
    OrganizationSettings,
    SecuritySettings,
    StorageSettings,
)

logger = logging.getLogger(__name__)


class OrganizationSettingsService:
    """Service to handle organization settings and make them functional"""
    
    @staticmethod
    def get_organization_settings(db: Session, organization_id: UUID) -> OrganizationSettings:
        """Get organization settings with defaults if not set"""
        organization = db.get(Organization, organization_id)
        if not organization:
            raise ValueError("Organization not found")
        
        settings_data = organization.settings or {}
        
        # Create settings with defaults if not present
        security = SecuritySettings(**settings_data.get("security", {}))
        notifications = NotificationSettings(**settings_data.get("notifications", {}))
        storage = StorageSettings(**settings_data.get("storage", {}))
        
        return OrganizationSettings(
            security=security,
            notifications=notifications,
            storage=storage
        )
    
    @staticmethod
    def update_organization_settings(
        db: Session, 
        organization_id: UUID, 
        settings: OrganizationSettings
    ) -> OrganizationSettings:
        """Update organization settings"""
        organization = db.get(Organization, organization_id)
        if not organization:
            raise ValueError("Organization not found")
        
        # Convert to dict for JSON storage
        settings_dict = {
            "security": settings.security.model_dump(),
            "notifications": settings.notifications.model_dump(),
            "storage": settings.storage.model_dump()
        }
        
        organization.settings = settings_dict
        db.add(organization)
        db.commit()
        db.refresh(organization)
        
        return settings
    
    @staticmethod
    def get_user_organization_settings(db: Session, user_id: UUID) -> Optional[OrganizationSettings]:
        """Get organization settings for a user (if they belong to an org)"""
        org_user = db.exec(
            select(OrganizationUser)
            .join(Organization)
            .where(OrganizationUser.user_id == user_id)
        ).first()
        
        if not org_user:
            return None
            
        return OrganizationSettingsService.get_organization_settings(
            db, org_user.organization_id
        )
    
    @staticmethod
    def get_session_timeout_minutes(db: Session, user_id: UUID) -> int:
        """Get session timeout for user based on their organization settings"""
        settings = OrganizationSettingsService.get_user_organization_settings(db, user_id)
        if settings:
            return settings.security.session_timeout_minutes
        
        # Default for personal accounts
        return 60  # 1 hour default
    
    @staticmethod
    def get_allowed_ips(db: Session, user_id: UUID) -> Optional[List[str]]:
        """Get allowed IPs for user based on their organization settings"""
        settings = OrganizationSettingsService.get_user_organization_settings(db, user_id)
        if settings and settings.security.ip_restrictions:
            return settings.security.ip_restrictions
        
        return None  # No IP restrictions
    
    @staticmethod
    def requires_2fa(db: Session, user_id: UUID) -> bool:
        """Check if user's organization requires 2FA"""
        settings = OrganizationSettingsService.get_user_organization_settings(db, user_id)
        if settings:
            return settings.security.require_2fa
        
        return False  # Personal accounts don't require 2FA by default
    
    @staticmethod
    def get_storage_limit_bytes(db: Session, organization_id: UUID) -> int:
        """Get storage limit in bytes for organization"""
        settings = OrganizationSettingsService.get_organization_settings(db, organization_id)
        return settings.storage.limit_gb * 1024 * 1024 * 1024  # Convert GB to bytes
    
    @staticmethod
    def check_storage_available(db: Session, organization_id: UUID, additional_bytes: int) -> bool:
        """Check if organization has enough storage for additional files"""
        organization = db.get(Organization, organization_id)
        if not organization:
            return False
        
        limit_bytes = OrganizationSettingsService.get_storage_limit_bytes(db, organization_id)
        current_usage = organization.storage_used or 0
        
        return (current_usage + additional_bytes) <= limit_bytes
    
    @staticmethod
    def add_storage_usage(db: Session, organization_id: UUID, bytes_used: int):
        """Add to organization storage usage"""
        organization = db.get(Organization, organization_id)
        if organization:
            organization.storage_used = (organization.storage_used or 0) + bytes_used
            db.add(organization)
            db.commit()
            
            logger.info(f"Added {bytes_used} bytes to org {organization_id}. Total: {organization.storage_used}")
    
    @staticmethod
    def is_ip_allowed(db: Session, user_id: UUID, client_ip: str) -> bool:
        """Check if client IP is allowed for user based on organization settings"""
        allowed_ips = OrganizationSettingsService.get_allowed_ips(db, user_id)
        
        if allowed_ips is None:
            return True  # No restrictions
        
        # Check if client IP matches any allowed pattern
        import ipaddress
        
        try:
            client_addr = ipaddress.ip_address(client_ip)
        except ValueError:
            logger.warning(f"Invalid client IP: {client_ip}")
            return False
        
        for allowed_pattern in allowed_ips:
            try:
                if "/" in allowed_pattern:
                    # CIDR notation
                    network = ipaddress.ip_network(allowed_pattern, strict=False)
                    if client_addr in network:
                        return True
                else:
                    # Single IP
                    if client_addr == ipaddress.ip_address(allowed_pattern):
                        return True
            except ValueError:
                logger.warning(f"Invalid IP pattern in settings: {allowed_pattern}")
                continue
        
        return False
