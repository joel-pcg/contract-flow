import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlmodel import Session, func, select

from app.core.permission import ROLE_PERMISSIONS, Permission
from app.models.contract import Contract, ContractParty, ContractStatus, ContractVersion
from app.models.organization import OrganizationUser
from app.schemas.contract import ContractCreate, ContractUpdate, ContractVersionCreate
from app.services.pdf_service import generate_pdf
from app.utils.utils import ensure_timezone_aware

logger = logging.getLogger(__name__)


# =====================================
# CUSTOM EXCEPTIONS
# =====================================

class ContractServiceError(Exception):
    """Base exception for contract service errors."""
    pass


class ContractNotFoundError(ContractServiceError):
    """Raised when a contract is not found."""
    pass


class ContractPermissionError(ContractServiceError):
    """Raised when user lacks permission for contract operation."""
    pass


class ContractStatusError(ContractServiceError):
    """Raised when contract status transition is invalid."""
    pass


class ContractValidationError(ContractServiceError):
    """Raised when contract data validation fails."""
    pass


def create_contract(db: Session, user_id: UUID, contract_data: ContractCreate) -> Contract:
    """
    Create a new contract with initial content and parties.
    
    Args:
        db: Database session
        user_id: ID of the user creating the contract
        contract_data: Contract creation data
        
    Returns:
        Newly created contract
    """
    # [CHALLENGE 13] Implement contract creation
    # Requirements:
    # - Create Contract instance with data from contract_data
    # - Set owner_id to user_id
    # - Set status to DRAFT
    # - Set current_version to 1
    # - Set last_activity tracking fields
    
    contract = Contract(
        title=contract_data.title,
        description=contract_data.description,
        template_type=contract_data.template_type,
        effective_date=contract_data.effective_date,
        expiration_date=contract_data.expiration_date,
        organization_id=contract_data.organization_id,
        status=ContractStatus.DRAFT,
        owner_id=user_id,
        current_version=1,
        last_activity_by_id=user_id,
        last_activity=datetime.now(timezone.utc)
    )
    db.add(contract)
    db.flush()
    # [CHALLENGE 14] Create initial version
    # Requirements:
    # - Create ContractVersion with version=1
    # - Use content from contract_data
    # - Set modified_by_id to user_id
    # - Add appropriate change_summary
    version = ContractVersion(
        contract_id=contract.id,
        version=1,
        modified_by_id=user_id,
        change_summary=contract_data.content.get('change_summary', "Initial contract creation"),
        content=contract_data.content,
    )
    db.add(version)
    # [CHALLENGE 15] Create contract parties
    # Requirements:
    # - Create ContractParty instances for each party in contract_data.parties
    # - Add all parties to database session
    for party in contract_data.parties:
        contract_party = ContractParty(
            contract_id=contract.id,
            party_type=party.party_type,
            user_id=party.user_id,
            organization_id=party.organization_id,
            external_name=party.external_name,
            external_email=party.external_email,
            signature_required=party.signature_required,
        )
        db.add(contract_party)

    db.commit()
    db.refresh(contract)
    
    # Load relationships
    db.refresh(contract, ['owner', 'organization'])
    
    return contract


def update_contract(
    db: Session, 
    contract_id: UUID, 
    user_id: UUID, 
    contract_data: ContractUpdate
) -> Contract:
    """Update contract metadata (not content)."""
    # Get contract by ID
    contract = db.exec(select(Contract).where(Contract.id == contract_id)).one_or_none()
    if not contract:
        raise ContractNotFoundError(f"Contract {contract_id} not found")
    
    # Update fields from contract_data if provided
    for field, value in contract_data.model_dump().items():
        if value is not None:
            setattr(contract, field, value)
    
    # Validate status transition if status is changing
    if contract.status != contract_data.status:
        if contract.status == ContractStatus.ACTIVE and contract_data.status != ContractStatus.ACTIVE:
            raise ContractStatusError(
                f"Cannot change status from {contract.status.value} to {contract_data.status.value}"
            )
    
    # Update activity tracking fields
    contract.last_activity_by_id = user_id
    contract.last_activity = datetime.now(timezone.utc)
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return contract



def create_contract_version(
    db: Session, 
    contract_id: UUID, 
    user_id: UUID, 
    version_data: ContractVersionCreate
) -> ContractVersion:
    """Create a new version of contract content."""
    # [CHALLENGE 17] Implement version creation
    # Requirements:
    # - Get contract by ID
    contract = db.exec(select(Contract).where(Contract.id == contract_id)).one_or_none()
    if not contract:
        raise ContractNotFoundError(f"Contract {contract_id} not found")
    # - Create new version with incremented version number
    version   = ContractVersion(
        contract_id=contract_id,
        version=contract.current_version + 1,
        modified_by_id=user_id,
        change_summary=version_data.change_summary,
        content=version_data.content,
    )
    db.add(version)

    contract.current_version = version.version
    contract.last_activity_by_id = user_id 
    contract.last_activity = datetime.now(timezone.utc)
   
    db.add(contract)
    db.commit()
    db.refresh(contract)

    return version


def get_contract_with_current_content(
    db: Session, contract_id: UUID
) -> Tuple[Optional[Contract], Optional[Dict[str, Any]]]:
    """
    Get a contract with its current version content.
    
    Returns:
        Tuple of (contract, content)
    """
    # Get contract
    contract = db.get(Contract, contract_id)
    
    if not contract:
        return None, None
    
    # Load relationships
    db.refresh(contract, ['parties', 'owner', 'organization'])
    
    # Get current version content
    version = db.exec(
        select(ContractVersion).where(
            ContractVersion.contract_id == contract_id, 
            ContractVersion.version == contract.current_version
        )
    ).first()
    
    content = version.content if version else {}
        
    return contract, content

def get_user_contracts(
    db: Session, 
    user_id: UUID,
    status: Optional[ContractStatus] = None,
    organization_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 100,
    sort_by: str = "updated_at",
    sort_desc: bool = True
) -> List[Contract]:
    """
    Get contracts accessible to a user using an optimized query approach.
    
    Args:
        db: Database session
        user_id: ID of the user
        status: Optional filter by contract status
        organization_id: Optional filter by organization
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        sort_by: Field to sort by
        sort_desc: Whether to sort in descending order
        
    Returns:
        List of contracts accessible to the user
    """
    # Get organizations where user has VIEW_MEMBERS permission
    org_users = db.exec(
        select(OrganizationUser).where(
            OrganizationUser.user_id == user_id
        )
    ).all()
    
    org_ids_with_permission = [
        org_user.organization_id for org_user in org_users
        if ROLE_PERMISSIONS[org_user.role] & Permission.VIEW_MEMBERS
    ]
    
    # Base conditions that apply to all queries
    base_conditions = []
    if status:
        base_conditions.append(Contract.status == status)
    if organization_id:
        base_conditions.append(Contract.organization_id == organization_id)
    
    # 1. Contracts owned by the user
    owned_query = select(Contract.id).where(Contract.owner_id == user_id)
    for condition in base_conditions:
        owned_query = owned_query.where(condition)
    
    # 2. Contracts where user is a party
    party_query = (
        select(Contract.id)
        .join(ContractParty, ContractParty.contract_id == Contract.id)
        .where(ContractParty.user_id == user_id)
    )
    for condition in base_conditions:
        party_query = party_query.where(condition)
    
    # 3. Contracts from organizations with permission
    org_query = None
    if org_ids_with_permission:
        org_query = select(Contract.id).where(Contract.organization_id.in_(org_ids_with_permission))
        for condition in base_conditions:
            org_query = org_query.where(condition)
    
    # Combine queries with UNION to get unique contract IDs
    # Collect all contract IDs from different sources
    contract_ids = set()
    
    # Get IDs from owned contracts
    owned_ids = db.exec(owned_query).all()
    contract_ids.update(owned_ids)
    
    # Get IDs from party contracts  
    party_ids = db.exec(party_query).all()
    contract_ids.update(party_ids)
    
    # Get IDs from organization contracts
    if org_query is not None:
        org_ids = db.exec(org_query).all()
        contract_ids.update(org_ids)
    
    # Convert to list
    contract_ids = list(contract_ids)
    
    # Now fetch the actual Contract objects
    if not contract_ids:
        return []
    
    # Create a query to fetch the contracts by ID
    contracts_query = select(Contract).where(Contract.id.in_(contract_ids))
    
    # Apply sorting
    sort_column = getattr(Contract, sort_by, Contract.updated_at)
    if sort_desc:
        contracts_query = contracts_query.order_by(sort_column.desc())
    else:
        contracts_query = contracts_query.order_by(sort_column)
    
    # Apply pagination
    contracts_query = contracts_query.offset(skip).limit(limit)
    
    # Execute query
    contracts = db.exec(contracts_query).all()
    
    return contracts
 

def get_contract_data(db: Session, contract_id: UUID) -> Dict[str, Any]:
    """
    Get complete contract data for API responses.
    Clean separation: Backend provides data, Frontend handles presentation.
    
    Args:
        db: Database session
        contract_id: Contract identifier
        
    Returns:
        Complete contract data with content and metadata
        
    Raises:
        ValueError: If contract not found
    """
    contract, content = get_contract_with_current_content(db, contract_id)
    
    if not contract:
        raise ContractNotFoundError(f"Contract {contract_id} not found")
    
    return {
        "contract": contract_to_api_response(contract, content),
        "content": content or {},
        "parties": [
            {
                "id": str(party.id),
                "name": _get_party_display_name(party),
                "email": _get_party_email(party),
                "type": party.party_type.value,
                "signature_required": party.signature_required,
                "signature_date": party.signature_date.isoformat() if party.signature_date else None,
                "signed": party.signature_date is not None
            }
            for party in contract.parties
        ],
        "metadata": {
            "version": contract.current_version,
            "status": contract.status.value,
            "effective_date": contract.effective_date.isoformat() if contract.effective_date else None,
            "expiration_date": contract.expiration_date.isoformat() if contract.expiration_date else None,
            "created_at": contract.created_at.isoformat(),
            "last_activity": contract.last_activity.isoformat() if contract.last_activity else None
        }
    }


def _get_party_display_name(party: ContractParty) -> str:
    """Get the display name for a contract party."""
    if party.user and party.user.full_name:
        return party.user.full_name
    elif party.user:
        return party.user.email
    elif party.organization:
        return party.organization.name
    elif party.external_name:
        return party.external_name
    else:
        return party.external_email or "Unknown Party"


def _get_party_email(party: ContractParty) -> str:
    """Get the email for a contract party."""
    if party.user:
        return party.user.email
    elif party.external_email:
        return party.external_email
    else:
        return ""

def generate_contract_pdf(content: Dict[str, Any], contract: Contract, db: Session = None) -> str:
    """
    Generate PDF from contract content with real signatures included.
    
    Args:
        content: Contract content
        contract: Contract model
        db: Database session (required for signature data)
        
    Returns:
        Path to generated PDF file
    """
    try:
        # Get signatures for this contract if db session provided
        signatures_data = {}
        if db:
            from app.models.signature import ContractSignature
            signatures = db.exec(
                select(ContractSignature).where(ContractSignature.contract_id == contract.id)
            ).all()
            
            # Create mapping: party_email -> signature_info
            for signature in signatures:
                signatures_data[signature.party_email] = {
                    'signed_at': signature.signed_at,
                    'signature_method': signature.signature_method,
                    'signature_data': signature.signature_data,
                    'ip_address': signature.ip_address
                }
        
        # Create PDF HTML with signature data
        html_content = _create_pdf_html(contract, content, signatures_data)
        
        # Generate filename and path
        status_suffix = "_signed" if signatures_data else "_draft"
        filename = f"contract_{contract.id}_{contract.current_version}{status_suffix}.pdf"
        output_path = f"storage/contracts/{contract.id}/{filename}"
        
        # PDF-optimized CSS with signature styling
        css_content = """
        body {
            font-family: 'Times New Roman', serif;
            font-size: 11pt;
            line-height: 1.4;
            margin: 2.5cm;
            color: #000;
        }
        .header {
        text-align: center;
        margin-bottom: 2cm;
            border-bottom: 2px solid #000;
            padding-bottom: 1cm;
        }
        .title {
            font-size: 16pt;
            font-weight: bold;
        margin-bottom: 0.5cm;
    }
        .contract-status {
            font-size: 10pt;
            margin-top: 0.5cm;
            font-weight: bold;
        }
        .parties {
            margin: 1.5cm 0;
            page-break-inside: avoid;
        }
        .party {
            margin: 0.3cm 0;
            font-size: 10pt;
        }
    .section {
            margin-bottom: 1.2cm;
            page-break-inside: avoid;
        }
        .section h2 {
            font-size: 12pt;
            font-weight: bold;
            margin-bottom: 0.5cm;
            border-bottom: 1px solid #ccc;
            padding-bottom: 0.2cm;
        }
        .signatures {
            margin-top: 5cm;
            page-break-inside: avoid;
        }
        .signatures h3 {
            font-size: 16pt;
            margin-bottom: 3cm;
            text-align: center;
            border-bottom: 2px solid #000;
            padding-bottom: 0.5cm;
            letter-spacing: 1px;
        }
        .signature-block {
            display: inline-block;
            width: 40%;
            margin: 1.5cm 5% 3cm 0;
            page-break-inside: avoid;
            vertical-align: top;
        }
        .signature-area {
            height: 4cm;
            position: relative;
            margin-bottom: 1cm;
        }
        .handwritten-signature {
            font-family: 'Brush Script MT', cursive, 'Dancing Script', serif;
            font-size: 18pt;
            color: #1a472a;
            margin-bottom: 0.5cm;
            text-align: center;
            font-weight: bold;
            transform: rotate(-2deg);
            margin-top: 1cm;
        }
        .signature-line {
            border-bottom: 1.5px solid #000;
            height: 1px;
            margin: 1cm 0 0.3cm 0;
        }
        .signature-details {
            text-align: center;
            margin-top: 0.5cm;
        }
        .signer-name {
            font-size: 11pt;
            font-weight: bold;
            margin-bottom: 0.2cm;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .signature-date {
            font-size: 9pt;
            color: #666;
            font-style: italic;
        }
        .verification-footer {
            margin-top: 6cm;
            padding: 0.3cm 0;
            border-top: 0.5px solid #ddd;
            page-break-inside: avoid;
        }
        .verification-info {
            font-size: 8pt;
            color: #999;
            text-align: center;
            font-style: italic;
            letter-spacing: 0.3px;
        }
        @page {
            @bottom-center {
                content: "Page " counter(page) " of " counter(pages);
                font-size: 9pt;
            }
        }
        """
        
        # Generate PDF
        pdf_path = generate_pdf(
            html_content=html_content,
            output_path=output_path,
            css_content=css_content
        )
        
        logger.info(f"Contract PDF generated: {pdf_path}")
        return pdf_path
        
    except Exception as e:
        logger.error(f"Error generating contract PDF: {str(e)}")
        raise ContractServiceError(f"Failed to generate contract PDF: {str(e)}")


def _create_pdf_html(contract: Contract, content: Dict[str, Any], signatures_data: Dict[str, Any] = None) -> str:
    """
    Create clean HTML specifically for PDF generation with real signatures.
    
    Args:
        contract: Contract model
        content: Contract content
        signatures_data: Dict mapping party_email -> signature_info
    """
    
    signatures_data = signatures_data or {}
    
    # Build sections HTML
    sections_html = ""
    for section in content.get("sections", []):
        sections_html += f"""
        <div class="section">
            <h2>{section.get('title', 'Section')}</h2>
            <div class="section-content">{section.get('text', '')}</div>
        </div>
        """
    
    # Build signatures HTML - showing real signatures vs empty spaces
    signatures_html = ""
    
    for party in contract.parties:
        party_name = _get_party_display_name(party)
        party_email = _get_party_email(party)
        
        # Check if this party has signed
        if party_email in signatures_data:
            signature_info = signatures_data[party_email]
            signed_at = signature_info['signed_at']
            
            # Format the signed date elegantly
            if isinstance(signed_at, str):
                from dateutil import parser
                signed_at = parser.parse(signed_at)
            
            formatted_date = signed_at.strftime('%B %d, %Y')
            
            # Signed: Show elegant signature with name and date
            signatures_html += f'''
            <div class="signature-block signed">
                <div class="signature-area">
                    <div class="handwritten-signature">{party_name}</div>
                    <div class="signature-line"></div>
                </div>
                <div class="signature-details">
                    <div class="signer-name">{party_name}</div>
                    <div class="signature-date">{formatted_date}</div>
                </div>
            </div>
            '''
        else:
            # Not signed: Show elegant blank signature block
            signatures_html += f'''
            <div class="signature-block unsigned">
                <div class="signature-area">
                    <div class="signature-line"></div>
                </div>
                <div class="signature-details">
                    <div class="signer-name">{party_name}</div>
                    <div class="signature-date">Date: ______________</div>
                </div>
            </div>
            '''
    
    # Create PDF-optimized HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{contract.title}</title>
    </head>
    <body>
        <div class="header">
            <div class="title">{contract.title}</div>
            <div class="effective-date">
                Effective Date: {contract.effective_date.strftime('%B %d, %Y') if contract.effective_date else 'N/A'}
            </div>
            <div class="contract-status">Status: {contract.status.value.title()}</div>
        </div>
        
        <div class="parties">
            <h3>Parties to this Agreement:</h3>
            {''.join(f'<div class="party">{_get_party_display_name(party)} ({_get_party_email(party)})</div>' for party in contract.parties)}
        </div>
        
        <div class="content">
            {sections_html}
        </div>
        
        <div class="signatures">
            <h3>Signatures:</h3>
            {signatures_html}
        </div>
        
        {_create_signature_verification_footer(signatures_data)}
    </body>
    </html>
    """
    
    return html


def _create_signature_verification_footer(signatures_data: Dict[str, Any]) -> str:
    """Create ultra-discrete verification footer for signed documents."""
    
    if not signatures_data:
        return ""
    
    signed_count = len(signatures_data)
    
    return f"""
    <div class="verification-footer">
        <div class="verification-info">
            Document authenticated with {signed_count} digital signature{'s' if signed_count != 1 else ''}
            • Verified {datetime.now(timezone.utc).strftime('%B %Y')} • ContractFlow
        </div>
    </div>
    """

def contract_to_api_response(contract: Contract, content: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Convert a Contract model to an API response dictionary.
    
    Args:
        contract: Contract model
        content: Optional content to include
        
    Returns:
        Dictionary suitable for API response
    """
    return {
        "id": str(contract.id),
        "title": contract.title,
        "description": contract.description,
        "template_type": contract.template_type.value,
        "status": contract.status.value,
        "effective_date": contract.effective_date.isoformat() if contract.effective_date else None,
        "expiration_date": contract.expiration_date.isoformat() if contract.expiration_date else None,
        "organization_id": str(contract.organization_id) if contract.organization_id else None,
        "current_version": contract.current_version,
        "created_at": contract.created_at.isoformat(),
        "updated_at": contract.updated_at.isoformat() if contract.updated_at else None,
        "last_activity": contract.last_activity.isoformat() if contract.last_activity else None,
        "owner": {
            "id": str(contract.owner.id),
            "email": contract.owner.email,
            "full_name": contract.owner.full_name if hasattr(contract.owner, "full_name") else None
        },
        "organization": {
            "id": str(contract.organization.id),
            "name": contract.organization.name
        } if contract.organization else None,
        "parties": [
            {
                "id": str(party.id),
                "contract_id": str(party.contract_id),
                "party_type": party.party_type.value,
                "user_id": str(party.user_id) if party.user_id else None,
                "organization_id": str(party.organization_id) if party.organization_id else None,
                "external_name": party.external_name,
                "external_email": party.external_email,
                "signature_required": party.signature_required,
                "signature_date": party.signature_date.isoformat() if party.signature_date else None,
                "user": {
                    "id": str(party.user.id),
                    "email": party.user.email,
                    "full_name": party.user.full_name if hasattr(party.user, "full_name") else None
                } if party.user else None,
                "organization": {
                    "id": str(party.organization.id),
                    "name": party.organization.name
                } if party.organization else None
            }
            for party in contract.parties
        ],
        "current_content": content or {}
    }
def send_contract_for_signature(db: Session, contract_id: UUID, user_id: UUID) -> Contract:
    """
    Send a contract for signature by changing its status to PENDING.
    This triggers the signature process.
    
    Args:
        db: Database session
        contract_id: ID of the contract to send for signature
        user_id: ID of the user sending the contract
        
    Returns:
        Updated contract
        
    Raises:
        ContractNotFoundError: If contract not found
        ContractPermissionError: If user not authorized
        ContractStatusError: If contract in invalid status
        ContractValidationError: If no parties require signatures
    """
    
    contract = db.get(Contract, contract_id)
    if not contract:
        raise ContractNotFoundError(f"Contract {contract_id} not found")
    
    # Check if user is owner or has permission
    if contract.owner_id != user_id:
        raise ContractPermissionError("Only contract owner can send contract for signature")
    
    # Check if contract is in valid state
    if contract.status != ContractStatus.DRAFT:
        raise ContractStatusError(
            f"Cannot send contract with status '{contract.status.value}' for signature. "
            f"Contract must be in DRAFT status."
        )
    
    # Check if there are parties that require signatures
    parties_requiring_signature = [p for p in contract.parties if p.signature_required]
    if not parties_requiring_signature:
        raise ContractValidationError("Contract has no parties requiring signatures")
    
    # Update contract status
    contract.status = ContractStatus.PENDING
    contract.last_activity = datetime.now(timezone.utc)
    contract.last_activity_by_id = user_id
    
    db.commit()
    db.refresh(contract)
    
    return contract

def get_contract_dashboard_data(db: Session, user_id: UUID) -> Dict[str, Any]:
    """
    Get dashboard data for contracts - overview statistics.
    Optimized version using direct SQL queries instead of loading all contracts.
    
    Args:
        db: Database session  
        user_id: ID of the user
        
    Returns:
        Dashboard data with contract statistics
    """
    now_utc = datetime.now(timezone.utc)
    thirty_days_ago = now_utc - timedelta(days=30)
    thirty_days_future = now_utc + timedelta(days=30)
    
    # 1. Total contracts count (single query)
    total_contracts = db.exec(
        select(func.count(Contract.id)).where(Contract.owner_id == user_id)
    ).one()
    
    # 2. Status breakdown using group by (single optimized query)
    status_query = select(Contract.status, func.count(Contract.id)).where(
        Contract.owner_id == user_id
    ).group_by(Contract.status)
    
    status_results = db.exec(status_query).all()
    status_counts = {status.value: 0 for status in ContractStatus}
    for status, count in status_results:
        status_counts[status.value] = count
    
    # 3. Recent activity count (optimized query with date filter)
    recent_contracts_count = db.exec(
        select(func.count(Contract.id)).where(
            Contract.owner_id == user_id,
            Contract.created_at >= thirty_days_ago
        )
    ).one()
    
    # 4. Contracts expiring soon (only load what we need)
    expiring_query = select(
        Contract.id, 
        Contract.title, 
        Contract.expiration_date
    ).where(
        Contract.owner_id == user_id,
        Contract.status == ContractStatus.ACTIVE,
        Contract.expiration_date.is_not(None),
        Contract.expiration_date <= thirty_days_future
    ).order_by(Contract.expiration_date).limit(5)
    
    expiring_results = db.exec(expiring_query).all()
    
    expiring_soon = []
    for contract_id, title, expiration_date in expiring_results:
        expiring_date_aware = ensure_timezone_aware(expiration_date)
        days_until = (expiring_date_aware - now_utc).days if expiring_date_aware else 0
        
        expiring_soon.append({
            "id": str(contract_id),
            "title": title,
            "expiration_date": expiration_date.isoformat(),
            "days_until_expiration": days_until
        })
    
    return {
        "total_contracts": total_contracts,
        "status_breakdown": status_counts,
        "recent_contracts_count": recent_contracts_count,
        "expiring_soon_count": len(expiring_soon),
        "expiring_soon": expiring_soon
    }