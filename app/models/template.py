# app/models/template.py
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlmodel import JSON, Column, Field

from .base import TimestampModel
from .contract import ContractTemplateType


class ContractTemplate(TimestampModel, table=True):
    """
    Template para contratos con sistema de permisos.
    Almacena la estructura JSON y controla la visibilidad por usuario/organización.
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    
    # Identificación del template
    type: ContractTemplateType = Field(index=True)
    name: str
    description: Optional[str] = None
    
    # Estructura del template (JSON con secciones)
    structure: Dict[str, Any] = Field(sa_column=Column(JSON))
    
    # Sistema de permisos y ownership
    is_global: bool = Field(default=False)  # Templates predefinidos accesibles por todos
    created_by_id: Optional[UUID] = Field(default=None, foreign_key="user.id")  # Usuario creador
    organization_id: Optional[UUID] = Field(default=None, foreign_key="organization.id")  # Organización propietaria
    
    # Estado del template
    is_active: bool = Field(default=True)
    
    class Config:
        """Pydantic configuration"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
