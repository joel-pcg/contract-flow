# app/api/templates.py
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.security import get_current_user
from app.models.contract import ContractTemplateType
from app.models.users import User
from app.schemas.template import (
    TemplateCreate,
    TemplateDetail,
    TemplateRead,
    TemplateUpdate,
)
from app.services.template_service import (
    TemplateAlreadyExistsError,
    TemplateNotFoundError,
    create_template,
    delete_template,
    get_template_by_type_for_user,
    get_templates_for_user,
    get_user_organizations,
    update_template,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[TemplateRead])
async def get_available_templates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Get templates accessible to current user based on permission logic:
    - Global templates (predefined) → visible to everyone
    - User's personal templates → only visible to creator
    - Organization templates → only visible to organization members
    """
    try:
        # Get user's organizations
        user_organizations = get_user_organizations(db, current_user.id)
        
        # Get templates with permission filtering
        templates = get_templates_for_user(db, current_user.id, user_organizations)
        
        # Convert to response model
        template_list = [
            TemplateRead(
                type=template.type,
                name=template.name,
                description=template.description,
                is_active=template.is_active
            )
            for template in templates
        ]
        
        return template_list
        
    except Exception as e:
        logger.error(f"Error fetching templates for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch templates"
        )


@router.get("/{template_type}", response_model=TemplateDetail)
async def get_template_details(
    template_type: ContractTemplateType,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Get detailed template information including structure.
    Only returns templates that the user has permission to access.
    """
    try:
        # Get user's organizations
        user_organizations = get_user_organizations(db, current_user.id)
        
        # Get template with permission checking
        template = get_template_by_type_for_user(db, template_type, current_user.id, user_organizations)
        
        # Convert to response model
        template_detail = TemplateDetail(
            type=template.type,
            name=template.name,
            description=template.description,
            structure=template.structure,
            is_global=template.is_global,
            is_active=template.is_active
        )
        
        return template_detail
        
    except TemplateNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_type} not found or not accessible"
        )
    except Exception as e:
        logger.error(f"Error fetching template {template_type} for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch template details"
        )


@router.post("/", response_model=TemplateDetail, status_code=status.HTTP_201_CREATED)
async def create_new_template(
    template_data: TemplateCreate,
    organization_id: Optional[UUID] = None,  # Query param: organization to create template for
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Create a new contract template.
    
    - If organization_id provided: creates template for organization (user must be member)
    - If no organization_id: creates personal template for current user
    """
    try:
        # If creating for organization, verify user is member
        if organization_id:
            user_organizations = get_user_organizations(db, current_user.id)
            if organization_id not in user_organizations:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to create templates for this organization"
                )
        
        # Create template with ownership
        template = create_template(db, template_data, current_user.id, organization_id)
        
        return TemplateDetail(
            type=template.type,
            name=template.name,
            description=template.description,
            structure=template.structure,
            is_global=template.is_global,
            is_active=template.is_active
        )
        
    except TemplateAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating template for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create template"
        )


@router.put("/{template_type}", response_model=TemplateDetail)
async def update_template_endpoint(
    template_type: ContractTemplateType,
    template_data: TemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Update an existing template.
    Admin only functionality.
    """
    try:
        # TODO: Add admin permission check
        # if not current_user.is_admin:
        #     raise HTTPException(status_code=403, detail="Admin access required")
        
        template = update_template(db, template_type, template_data)
        
        return TemplateDetail(
            type=template.type,
            name=template.name,
            description=template.description,
            structure=template.structure,
            is_active=template.is_active
        )
        
    except TemplateNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_type} not found"
        )
    except Exception as e:
        logger.error(f"Error updating template {template_type}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update template"
        )


@router.delete("/{template_type}")
async def delete_template_endpoint(
    template_type: ContractTemplateType,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Deactivate a template.
    Admin only functionality.
    """
    try:
        # TODO: Add admin permission check
        # if not current_user.is_admin:
        #     raise HTTPException(status_code=403, detail="Admin access required")
        
        delete_template(db, template_type)
        
        return {"message": f"Template {template_type} deactivated successfully"}
        
    except TemplateNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_type} not found"
        )
    except Exception as e:
        logger.error(f"Error deactivating template {template_type}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate template"
        )
