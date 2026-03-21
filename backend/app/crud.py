import uuid

from app.models import Item, ItemCreate


async def create_item(*, item_in: ItemCreate, owner_id: uuid.UUID) -> Item:
    db_item = Item(
        title=item_in.title,
        description=item_in.description,
        owner_id=owner_id,
    )
    await db_item.insert()
    return db_item
