import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlmodel import Session, select

from ..models.contract import Contract, ContractParty, ContractStatus
from ..models.signature import ContractSignature
from ..schemas.signature import ContractSignatureStatus, SignatureCreate

logger = logging.getLogger(__name__)


def sign_contract(
    db: Session, 
    signature_data: SignatureCreate,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> ContractSignature:
    """
    Sign a contract on behalf of a party.
    
    Args:
        db: Database session
        signature_data: Signature creation data
        ip_address: IP address of the signer (for audit)
        user_agent: User agent of the signer (for audit)
        
    Returns:
        Created signature record
        
    Raises:
        ValueError: If contract doesn't exist, party not found, or already signed
    """
    
    # Get the contract
    contract = db.get(Contract, signature_data.contract_id)
    if not contract:
        raise ValueError("Contract not found")
    
    # Check if contract is in signable state
    if contract.status not in [ContractStatus.PENDING, ContractStatus.DRAFT]:
        raise ValueError(f"Contract status '{contract.status}' does not allow signing")
    
    # Check if the party is authorized to sign this contract
    party_query = select(ContractParty).where(
        ContractParty.contract_id == signature_data.contract_id,
        ContractParty.external_email == signature_data.party_email,
        ContractParty.signature_required
    )
    party = db.exec(party_query).first()
    
    if not party:
        raise ValueError("Party not found or not authorized to sign this contract")
    
    # Check if already signed
    existing_signature = db.exec(
        select(ContractSignature).where(
            ContractSignature.contract_id == signature_data.contract_id,
            ContractSignature.party_email == signature_data.party_email
        )
    ).first()
    
    if existing_signature:
        raise ValueError("Contract already signed by this party")
    
    # Create signature
    signature = ContractSignature(
        contract_id=signature_data.contract_id,
        party_email=signature_data.party_email,
        signature_data=signature_data.signature_data,
        ip_address=ip_address,
        user_agent=user_agent,
        signed_at=datetime.now(timezone.utc)
    )
    
    db.add(signature)
    
    # Update party signature info
    party.signature_date = signature.signed_at
    party.signature_data = "signed"  # Just mark as signed
    
    # Check if all parties have signed
    signature_status = get_contract_signature_status(db, signature_data.contract_id)
    
    # If all parties signed, update contract status
    if signature_status.all_signed:
        contract.status = ContractStatus.ACTIVE
        contract.last_activity = datetime.now(timezone.utc)
        
        # TODO: Send "contract fully executed" email to all parties
        logger.info(f"Contract {contract.id} fully executed - all parties signed")
    
    db.commit()
    db.refresh(signature)
    
    return signature


def get_contract_signature_status(db: Session, contract_id: UUID) -> ContractSignatureStatus:
    """Get the signature status for a contract."""
    
    # Get all parties that need to sign
    parties_query = select(ContractParty).where(
        ContractParty.contract_id == contract_id,
        ContractParty.signature_required
    )
    required_parties = db.exec(parties_query).all()
    
    # Get all signatures for this contract
    signatures_query = select(ContractSignature).where(
        ContractSignature.contract_id == contract_id
    )
    signatures = db.exec(signatures_query).all()
    
    signed_emails = {sig.party_email for sig in signatures}
    required_emails = {party.external_email for party in required_parties}
    
    total_parties = len(required_emails)
    signed_parties = len(signed_emails)
    pending_parties = total_parties - signed_parties
    all_signed = pending_parties == 0 and total_parties > 0
    
    remaining_signers = list(required_emails - signed_emails)
    
    return ContractSignatureStatus(
        contract_id=contract_id,
        total_parties=total_parties,
        signed_parties=signed_parties,
        pending_parties=pending_parties,
        all_signed=all_signed,
        remaining_signers=remaining_signers
    )


def get_contract_signatures(db: Session, contract_id: UUID) -> List[ContractSignature]:
    """Get all signatures for a contract."""
    
    query = select(ContractSignature).where(
        ContractSignature.contract_id == contract_id
    ).order_by(ContractSignature.signed_at)
    
    return db.exec(query).all()


def send_signature_request_emails(db: Session, contract_id: UUID) -> None:
    """Send signature request emails to all parties that need to sign."""
    
    contract = db.get(Contract, contract_id)
    if not contract:
        raise ValueError("Contract not found")
    
    # Get parties that need to sign but haven't signed yet
    signature_status = get_contract_signature_status(db, contract_id)
    
    for email in signature_status.remaining_signers:
        try:
            # TODO: Implement signature request email template
            logger.info(f"Sending signature request to {email} for contract {contract_id}")
            # email_service.send_signature_request_email(email, contract.title, contract_id)
        except Exception as e:
            logger.error(f"Failed to send signature request to {email}: {str(e)}")


def reject_contract(db: Session, contract_id: UUID, party_email: str, reason: Optional[str] = None) -> Contract:
    """Reject a contract on behalf of a party."""
    
    contract = db.get(Contract, contract_id)
    if not contract:
        raise ValueError("Contract not found")
    
    # Check if party is authorized
    party_query = select(ContractParty).where(
        ContractParty.contract_id == contract_id,
        ContractParty.external_email == party_email,
        ContractParty.signature_required
    )
    party = db.exec(party_query).first()
    
    if not party:
        raise ValueError("Party not authorized to reject this contract")
    
    # Update contract status
    contract.status = ContractStatus.REJECTED
    contract.last_activity = datetime.now(timezone.utc)
    
    db.commit()
    
    # TODO: Send rejection notification to all parties
    logger.info(f"Contract {contract_id} rejected by {party_email}. Reason: {reason}")
    
    return contract
