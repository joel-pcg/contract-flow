# app/schemas/template.py
from typing import Any, Dict, Optional

from sqlmodel import SQLModel

from app.models.contract import ContractTemplateType


class TemplateRead(SQLModel):
    """Schema para listar templates disponibles"""
    type: ContractTemplateType
    name: str
    description: Optional[str] = None
    is_active: bool


class TemplateDetail(SQLModel):
    """Schema para obtener detalles completos del template"""
    type: ContractTemplateType
    name: str
    description: Optional[str] = None
    structure: Dict[str, Any]
    is_global: bool
    is_active: bool


class TemplateCreate(SQLModel):
    """Schema para crear nuevos templates"""
    type: ContractTemplateType
    name: str
    description: Optional[str] = None
    structure: Dict[str, Any]
    is_active: bool = True
    # is_global, created_by_id, organization_id se asignan automáticamente


class TemplateUpdate(SQLModel):
    """Schema para actualizar templates (admin only)"""
    name: Optional[str] = None
    description: Optional[str] = None
    structure: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
