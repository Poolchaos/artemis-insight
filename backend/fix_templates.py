"""Fix templates to add missing usage_count field."""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient


async def fix_templates():
    client = AsyncIOMotorClient('mongodb://admin:devpassword123@mongodb:27017/artemis_insight?authSource=admin')
    db = client['artemis_insight']

    # Add usage_count to all templates that don't have it
    result = await db.templates.update_many(
        {'usage_count': {'$exists': False}},
        {'$set': {'usage_count': 0}}
    )

    print(f'Updated {result.modified_count} templates with usage_count field')

    # Verify
    templates = await db.templates.find({}).to_list(length=10)
    print(f'\nFound {len(templates)} templates:')
    for t in templates:
        print(f"  - {t.get('name')}: usage_count={t.get('usage_count', 'MISSING')}")

    client.close()


if __name__ == '__main__':
    asyncio.run(fix_templates())
