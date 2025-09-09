from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import SQLModel


class SignatureCreate(SQLModel):
    contract_id: UUID
    party_email: str
    signature_data: Optional[str] = None  # Base64 or signature method


class SignatureRead(SQLModel):
    id: UUID
    contract_id: UUID
    party_email: str
    signed_at: datetime
    signature_method: str
    created_at: datetime


class ContractSignatureStatus(SQLModel):
    contract_id: UUID
    total_parties: int
    signed_parties: int
    pending_parties: int
    all_signed: bool
    remaining_signers: list[str]
