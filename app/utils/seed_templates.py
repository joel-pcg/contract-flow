# app/utils/seed_templates.py
"""
Initial template data for ContractFlow.
Contains predefined templates that will be seeded into the database.
"""

from app.models.contract import ContractTemplateType

# Template data following our simple JSON structure approach
INITIAL_TEMPLATES = [
    {
        "type": ContractTemplateType.NDA,
        "name": "Non-Disclosure Agreement",
        "description": "Standard NDA template for protecting confidential information",
        "structure": {
            "sections": [
                {
                    "id": "header",
                    "type": "title",
                    "content": "NON-DISCLOSURE AGREEMENT",
                    "editable": False
                },
                {
                    "id": "parties",
                    "type": "paragraph",
                    "content": "This Non-Disclosure Agreement (\"Agreement\") is made on {{EFFECTIVE_DATE}} between {{COMPANY_NAME}} (\"Company\") and {{RECIPIENT_NAME}} (\"Recipient\").",
                    "editable": True
                },
                {
                    "id": "purpose",
                    "type": "paragraph",
                    "content": "The purpose of this Agreement is to protect confidential information that may be disclosed in connection with {{PURPOSE}}.",
                    "editable": True
                },
                {
                    "id": "definition",
                    "type": "section",
                    "title": "1. CONFIDENTIAL INFORMATION",
                    "content": "For purposes of this Agreement, \"Confidential Information\" means any and all information disclosed by Company to Recipient, whether orally, in writing, or in any other form, including but not limited to technical data, trade secrets, know-how, research, product plans, products, services, customers, customer lists, markets, software, developments, inventions, processes, formulas, technology, designs, drawings, engineering, hardware configuration information, marketing, finances, or other business information.",
                    "editable": True
                },
                {
                    "id": "obligations",
                    "type": "section", 
                    "title": "2. OBLIGATIONS OF RECIPIENT",
                    "content": "Recipient agrees to: (a) maintain the confidentiality of all Confidential Information; (b) not disclose any Confidential Information to third parties without prior written consent of Company; (c) use Confidential Information solely for the purpose stated above; (d) take reasonable precautions to protect the confidentiality of the Confidential Information.",
                    "editable": True
                },
                {
                    "id": "term",
                    "type": "section",
                    "title": "3. TERM",
                    "content": "This Agreement shall remain in effect until {{EXPIRATION_DATE}} or until terminated by either party with thirty (30) days written notice.",
                    "editable": True
                },
                {
                    "id": "signatures",
                    "type": "section",
                    "title": "4. SIGNATURES",
                    "content": "IN WITNESS WHEREOF, the parties have executed this Agreement as of the date first written above.",
                    "editable": False
                }
            ]
        },
        "is_global": True,  # Predefined templates are globally accessible
        "is_active": True
    },
    {
        "type": ContractTemplateType.FREELANCE,
        "name": "Freelance Service Agreement",
        "description": "Standard freelance/contractor service agreement template",
        "structure": {
            "sections": [
                {
                    "id": "header",
                    "type": "title",
                    "content": "FREELANCE SERVICE AGREEMENT",
                    "editable": False
                },
                {
                    "id": "parties",
                    "type": "paragraph",
                    "content": "This Freelance Service Agreement (\"Agreement\") is made on {{EFFECTIVE_DATE}} between {{COMPANY_NAME}} (\"Client\") and {{RECIPIENT_NAME}} (\"Freelancer\").",
                    "editable": True
                },
                {
                    "id": "services",
                    "type": "section",
                    "title": "1. SERVICES",
                    "content": "Freelancer agrees to provide the following services to Client: {{SERVICES_DESCRIPTION}}. The services shall be performed in a professional and workmanlike manner.",
                    "editable": True
                },
                {
                    "id": "compensation",
                    "type": "section",
                    "title": "2. COMPENSATION",
                    "content": "In consideration for the services, Client agrees to pay Freelancer {{COMPENSATION_AMOUNT}} according to the following payment schedule: {{PAYMENT_SCHEDULE}}.",
                    "editable": True
                },
                {
                    "id": "timeline",
                    "type": "section",
                    "title": "3. TIMELINE",
                    "content": "The services shall commence on {{EFFECTIVE_DATE}} and shall be completed by {{COMPLETION_DATE}}. Time is of the essence in this Agreement.",
                    "editable": True
                },
                {
                    "id": "intellectual_property",
                    "type": "section",
                    "title": "4. INTELLECTUAL PROPERTY",
                    "content": "All work product, inventions, and intellectual property created by Freelancer in the performance of services hereunder shall be the exclusive property of Client.",
                    "editable": True
                },
                {
                    "id": "independent_contractor",
                    "type": "section",
                    "title": "5. INDEPENDENT CONTRACTOR",
                    "content": "Freelancer is an independent contractor and not an employee of Client. Freelancer shall be responsible for all taxes, insurance, and other obligations related to this independent contractor status.",
                    "editable": True
                },
                {
                    "id": "termination",
                    "type": "section",
                    "title": "6. TERMINATION",
                    "content": "Either party may terminate this Agreement with seven (7) days written notice. Upon termination, Freelancer shall be paid for all services satisfactorily performed up to the termination date.",
                    "editable": True
                },
                {
                    "id": "signatures",
                    "type": "section",
                    "title": "7. SIGNATURES",
                    "content": "IN WITNESS WHEREOF, the parties have executed this Agreement as of the date first written above.",
                    "editable": False
                }
            ]
        },
        "is_global": True,  # Predefined templates are globally accessible
        "is_active": True
    },
    {
        "type": ContractTemplateType.COLLABORATION,
        "name": "Collaboration Agreement",
        "description": "Template for business collaboration and partnership agreements",
        "structure": {
            "sections": [
                {
                    "id": "header",
                    "type": "title",
                    "content": "COLLABORATION AGREEMENT",
                    "editable": False
                },
                {
                    "id": "parties",
                    "type": "paragraph",
                    "content": "This Collaboration Agreement (\"Agreement\") is made on {{EFFECTIVE_DATE}} between {{COMPANY_NAME}} and {{RECIPIENT_NAME}} (collectively, \"Parties\").",
                    "editable": True
                },
                {
                    "id": "purpose",
                    "type": "section",
                    "title": "1. PURPOSE AND SCOPE",
                    "content": "The purpose of this collaboration is {{COLLABORATION_PURPOSE}}. The Parties agree to work together to achieve the following objectives: {{OBJECTIVES}}.",
                    "editable": True
                },
                {
                    "id": "responsibilities",
                    "type": "section",
                    "title": "2. RESPONSIBILITIES",
                    "content": "{{COMPANY_NAME}} shall be responsible for: {{COMPANY_RESPONSIBILITIES}}. {{RECIPIENT_NAME}} shall be responsible for: {{RECIPIENT_RESPONSIBILITIES}}.",
                    "editable": True
                },
                {
                    "id": "resource_sharing",
                    "type": "section",
                    "title": "3. RESOURCE SHARING",
                    "content": "The Parties agree to share resources as follows: {{RESOURCE_SHARING_TERMS}}. Each Party shall contribute {{CONTRIBUTION_DETAILS}}.",
                    "editable": True
                },
                {
                    "id": "intellectual_property",
                    "type": "section",
                    "title": "4. INTELLECTUAL PROPERTY",
                    "content": "Any intellectual property created jointly during this collaboration shall be owned {{IP_OWNERSHIP_TERMS}}. Pre-existing intellectual property shall remain with the original owner.",
                    "editable": True
                },
                {
                    "id": "confidentiality",
                    "type": "section",
                    "title": "5. CONFIDENTIALITY",
                    "content": "Both Parties agree to maintain confidentiality of all proprietary information shared during this collaboration and not to disclose such information to third parties without written consent.",
                    "editable": True
                },
                {
                    "id": "term_termination",
                    "type": "section",
                    "title": "6. TERM AND TERMINATION",
                    "content": "This Agreement shall commence on {{EFFECTIVE_DATE}} and continue until {{EXPIRATION_DATE}} or until terminated by mutual agreement or by either Party with thirty (30) days written notice.",
                    "editable": True
                },
                {
                    "id": "signatures",
                    "type": "section",
                    "title": "7. SIGNATURES",
                    "content": "IN WITNESS WHEREOF, the parties have executed this Agreement as of the date first written above.",
                    "editable": False
                }
            ]
        },
        "is_global": True,  # Predefined templates are globally accessible
        "is_active": True
    }
]


def get_template_data():
    """
    Get initial template data for seeding.
    Returns list of template dictionaries ready for database insertion.
    """
    return INITIAL_TEMPLATES
