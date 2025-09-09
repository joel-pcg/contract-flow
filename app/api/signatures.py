import logging
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlmodel import Session

from ..core.database import get_session
from ..core.security import get_current_user

# from ..models.signature import ContractSignature
from ..models.users import User
from ..schemas.signature import ContractSignatureStatus, SignatureCreate, SignatureRead
from ..services.signature_service import (
    get_contract_signature_status,
    get_contract_signatures,
    reject_contract,
    send_signature_request_emails,
    sign_contract,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/{contract_id}/sign", response_model=SignatureRead, status_code=status.HTTP_201_CREATED)
async def sign_contract_endpoint(
    contract_id: str,
    signature_data: SignatureCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_session)
):
    """
    Sign a contract. This endpoint can be accessed by anyone with the contract link.
    No authentication required for external parties.
    """
    
    # Validate that the contract_id matches
    if str(signature_data.contract_id) != contract_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contract ID mismatch"
        )
    
    # Get client IP and user agent for audit
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "Unknown")
    
    try:
        signature = sign_contract(
            db=db,
            signature_data=signature_data,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
      # 🚀 Send email notifications in background after successful signing
        try:
            from ..services.email_services import email_service
            from ..services.signature_service import get_signature_notification_data
            
            notification_data = get_signature_notification_data(db, signature.contract_id, signature.party_email)
            
            if notification_data and notification_data.get('emails_to_notify'):
                if notification_data['notification_type'] == 'completed':
                    # Contract fully signed - notify all parties
                    for email_addr in notification_data['emails_to_notify']:
                        background_tasks.add_task(
                            email_service.send_contract_completed_notification,
                            to_email=email_addr,
                            contract_title=notification_data['contract'].title,
                            contract_id=str(signature.contract_id)
                        )
                else:
                    # Partial signature - notify owner and other parties
                    for email_addr in notification_data['emails_to_notify']:
                        background_tasks.add_task(
                            email_service.send_contract_signed_notification,
                            to_email=email_addr,
                            contract_title=notification_data['contract'].title,
                            signer_name=notification_data['signer_name'],
                            contract_id=str(signature.contract_id)
                        )
                
                logger.info(f"Queued signature notification emails for contract {signature.contract_id}")
        except Exception as e:
            logger.warning(f"Failed to queue signature notification emails: {str(e)}")
            # Don't fail the signing process if email queuing fails
        
        return SignatureRead(
            id=signature.id,
            contract_id=signature.contract_id,
            party_email=signature.party_email,
            signed_at=signature.signed_at,
            signature_method=signature.signature_method,
            created_at=signature.created_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{contract_id}/signatures", response_model=List[SignatureRead])
async def get_contract_signatures_endpoint(
    contract_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Get all signatures for a contract. Requires authentication."""
    
    try:
        signatures = get_contract_signatures(db, contract_id)
        
        return [
            SignatureRead(
                id=sig.id,
                contract_id=sig.contract_id,
                party_email=sig.party_email,
                signed_at=sig.signed_at,
                signature_method=sig.signature_method,
                created_at=sig.created_at
            )
            for sig in signatures
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve signatures: {str(e)}"
        )


@router.get("/{contract_id}/signature-status", response_model=ContractSignatureStatus)
async def get_signature_status_endpoint(
    contract_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Get signature status for a contract. Requires authentication."""
    
    try:
        return get_contract_signature_status(db, contract_id)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve signature status: {str(e)}"
        )


@router.post("/{contract_id}/request-signatures", status_code=status.HTTP_200_OK)
async def send_signature_requests(
    contract_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Send signature request emails to all pending parties. Requires authentication."""
    
    try:
        send_signature_request_emails(db, contract_id)
        return {"message": "Signature requests sent successfully"}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to send signature requests for contract {contract_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send signature requests"
        )


@router.post("/{contract_id}/reject")
async def reject_contract_endpoint(
    contract_id: str,
    party_email: str,
    reason: str = None,
    db: Session = Depends(get_session)
):
    """
    Reject a contract. No authentication required for external parties.
    """
    
    try:
        contract = reject_contract(db, contract_id, party_email, reason)
        return {
            "message": "Contract rejected successfully",
            "contract_id": str(contract.id),
            "status": contract.status
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to reject contract {contract_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reject contract"
        )
