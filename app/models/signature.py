from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship

from .base import TimestampModel

if TYPE_CHECKING:
    from .contract import Contract


class ContractSignature(TimestampModel, table=True):
    __tablename__ = "contract_signatures"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    contract_id: UUID = Field(foreign_key="contract.id", index=True)
    party_email: str = Field(index=True)
    signed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    signature_method: str = Field(default="digital")  # digital, electronic, etc.
    signature_data: Optional[str] = Field(default=None)  # Base64 encoded signature or metadata
    ip_address: Optional[str] = Field(default=None)
    user_agent: Optional[str] = Field(default=None)
    
    # Relationships
    contract: "Contract" = Relationship(back_populates="signatures")

