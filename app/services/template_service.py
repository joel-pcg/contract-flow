# app/services/template_service.py
import logging
from typing import List, Optional
from uuid import UUID

from sqlmodel import Session, select

from app.models.contract import ContractTemplateType
from app.models.template import ContractTemplate
from app.schemas.template import TemplateCreate, TemplateUpdate

logger = logging.getLogger(__name__)


# =====================================
# CUSTOM EXCEPTIONS
# =====================================

class TemplateServiceError(Exception):
    """Base exception for template service errors"""
    pass


class TemplateNotFoundError(TemplateServiceError):
    """Raised when a template is not found"""
    pass


class TemplateAlreadyExistsError(TemplateServiceError):
    """Raised when trying to create a template that already exists"""
    pass


# =====================================
# TEMPLATE SERVICES
# =====================================

def get_templates_for_user(db: Session, user_id: UUID, user_organizations: List[UUID] = None) -> List[ContractTemplate]:
    """
    Get templates accessible to a specific user based on permission logic:
    - Global templates (is_global=True) → visible to everyone
    - User's personal templates (created_by_id=user_id)
    - Organization templates where user is member
    """
    if user_organizations is None:
        user_organizations = []
    
    # Build query conditions
    conditions = [ContractTemplate.is_active]
    
    # Templates visible to user
    visibility_conditions = [
        ContractTemplate.is_global,  # Global templates
        ContractTemplate.created_by_id == user_id,  # User's personal templates
    ]
    
    # Add organization templates if user belongs to organizations
    if user_organizations:
        visibility_conditions.append(
            ContractTemplate.organization_id.in_(user_organizations)
        )
    
    # Combine conditions: is_active AND (is_global OR created_by_user OR in_user_orgs)
    from sqlalchemy import or_
    conditions.append(or_(*visibility_conditions))
    
    statement = select(ContractTemplate).where(*conditions)
    templates = db.exec(statement).all()
    return templates


def get_template_by_type_for_user(
    db: Session, 
    template_type: ContractTemplateType, 
    user_id: UUID, 
    user_organizations: List[UUID] = None
) -> ContractTemplate:
    """Get specific template by type that user has access to"""
    if user_organizations is None:
        user_organizations = []
    
    # Build query conditions (similar to get_templates_for_user)
    conditions = [
        ContractTemplate.type == template_type,
        ContractTemplate.is_active
    ]
    
    visibility_conditions = [
        ContractTemplate.is_global,
        ContractTemplate.created_by_id == user_id,
    ]
    
    if user_organizations:
        visibility_conditions.append(
            ContractTemplate.organization_id.in_(user_organizations)
        )
    
    from sqlalchemy import or_
    conditions.append(or_(*visibility_conditions))
    
    statement = select(ContractTemplate).where(*conditions)
    template = db.exec(statement).first()
    
    if not template:
        raise TemplateNotFoundError(f"Template {template_type} not found or not accessible")
    
    return template


# Legacy functions for backward compatibility (deprecated)
def get_all_active_templates(db: Session) -> List[ContractTemplate]:
    """DEPRECATED: Get all active templates (no permission filtering)"""
    logger.warning("get_all_active_templates is deprecated, use get_templates_for_user")
    statement = select(ContractTemplate).where(ContractTemplate.is_active)
    templates = db.exec(statement).all()
    return templates


def get_template_by_type(db: Session, template_type: ContractTemplateType) -> ContractTemplate:
    """DEPRECATED: Get template by type (no permission filtering)"""
    logger.warning("get_template_by_type is deprecated, use get_template_by_type_for_user")
    statement = select(ContractTemplate).where(
        ContractTemplate.type == template_type,
        ContractTemplate.is_active
    )
    template = db.exec(statement).first()
    
    if not template:
        raise TemplateNotFoundError(f"Template {template_type} not found or inactive")
    
    return template


def get_user_organizations(db: Session, user_id: UUID) -> List[UUID]:
    """Get list of organization IDs that user belongs to"""
    from app.models.organization import OrganizationUser
    
    statement = select(OrganizationUser.organization_id).where(
        OrganizationUser.user_id == user_id
    )
    org_ids = db.exec(statement).all()
    return list(org_ids)


def create_template(
    db: Session, 
    template_data: TemplateCreate, 
    created_by_id: UUID,
    organization_id: Optional[UUID] = None
) -> ContractTemplate:
    """
    Create a new template with proper ownership.
    
    Args:
        template_data: Template creation data
        created_by_id: User creating the template
        organization_id: Organization ID if creating for organization (None for personal)
    """
    # Create template with ownership
    template_dict = template_data.model_dump()
    template_dict.update({
        'created_by_id': created_by_id,
        'organization_id': organization_id,
        'is_global': False  # Custom templates are never global
    })
    
    template = ContractTemplate(**template_dict)
    db.add(template)
    db.commit()
    db.refresh(template)
    
    scope = "organization" if organization_id else "personal"
    logger.info(f"Created new {scope} template: {template.name} by user {created_by_id}")
    return template


def update_template(db: Session, template_type: ContractTemplateType, template_data: TemplateUpdate) -> ContractTemplate:
    """Update an existing template"""
    template = get_template_by_type(db, template_type)
    
    # Update only provided fields
    update_data = template_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    logger.info(f"Updated template: {template.type}")
    return template


def delete_template(db: Session, template_type: ContractTemplateType) -> None:
    """Soft delete a template (set is_active to False)"""
    template = get_template_by_type(db, template_type)
    template.is_active = False
    
    db.add(template)
    db.commit()
    
    logger.info(f"Deactivated template: {template.type}")


def get_template_by_id(db: Session, template_id: UUID) -> Optional[ContractTemplate]:
    """Get template by ID"""
    return db.get(ContractTemplate, template_id)
