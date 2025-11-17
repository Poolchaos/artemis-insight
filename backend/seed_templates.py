"""
Script to seed default templates into the database.
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
from app.models.template import FEASIBILITY_STUDY_TEMPLATE, EXECUTIVE_SUMMARY_TEMPLATE
from app.services.template_service import TemplateService


async def seed_templates():
    """Seed default templates."""
    client = AsyncIOMotorClient(settings.mongo_uri)
    db = client["artemis_insight"]

    # Get or create an admin user
    user = await db.users.find_one({"email": "bt1phillip@gmail.com"})
    if not user:
        print("User not found!")
        await client.close()
        return

    user_id = str(user["_id"])
    print(f"Found user: {user['email']} (ID: {user_id})")

    # Initialize template service
    template_service = TemplateService(db)

    # Seed templates
    print("\nSeeding default templates...")
    seeded = await template_service.seed_default_templates(created_by=user_id)

    print(f"\n✅ Successfully seeded {len(seeded)} templates")
    print(f"Templates created: {seeded}")

    await client.close()
if __name__ == "__main__":
    asyncio.run(seed_templates())
