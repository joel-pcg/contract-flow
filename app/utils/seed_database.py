# app/utils/seed_database.py
"""
Database seeding utilities for ContractFlow.
Contains functions to populate database with initial data.
"""

import logging

from sqlmodel import Session, select

from app.core.database import engine
from app.models.template import ContractTemplate
from app.utils.seed_templates import get_template_data

logger = logging.getLogger(__name__)


def seed_contract_templates(db: Session) -> None:
    """
    Seed the database with initial contract templates.
    Only creates templates that don't already exist.
    """
    logger.info("🌱 Starting template seeding...")
    
    template_data = get_template_data()
    
    for template_info in template_data:
        # Check if template already exists
        existing = db.exec(
            select(ContractTemplate).where(ContractTemplate.type == template_info["type"])
        ).first()
        
        if existing:
            logger.info(f"✓ Template {template_info['type']} already exists, skipping")
            continue
        
        # Create new template
        template = ContractTemplate(**template_info)
        db.add(template)
        logger.info(f"✓ Created template: {template.name}")
    
    db.commit()
    logger.info("🌱 Template seeding completed successfully!")


def seed_all_initial_data(db: Session) -> None:
    """
    Seed all initial data for the application.
    """
    logger.info("🌱 Starting database seeding...")
    
    try:
        # Seed templates
        seed_contract_templates(db)
        
        logger.info("🎉 All initial data seeded successfully!")
        
    except Exception as e:
        logger.error(f"❌ Error during database seeding: {str(e)}")
        db.rollback()
        raise


def main():
    """
    Main function to run seeding from command line.
    Usage: python -m app.utils.seed_database
    """
    from app.core.database import get_session
    
    logger.info("🚀 Starting ContractFlow database seeding...")
    
    with Session(engine) as session:
        seed_all_initial_data(session)
    
    logger.info("✅ Database seeding completed!")


if __name__ == "__main__":
    # Configure logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    main()
