from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
import os

_mongo_client: Optional[AsyncIOMotorClient] = None
_mongo_db = None


async def get_mongo_client() -> AsyncIOMotorClient:
    global _mongo_client

    if _mongo_client is None:
        mongo_url = os.getenv(
            "MONGO_URL",
            "mongodb://clinic_admin:clinic_mongo_pass@localhost:27017/"
        )
        _mongo_client = AsyncIOMotorClient(mongo_url)

    return _mongo_client


async def get_mongo_db():
    global _mongo_db

    if _mongo_db is None:
        client = await get_mongo_client()
        _mongo_db = client.clinic_logs

    return _mongo_db


async def close_mongo():
    global _mongo_client, _mongo_db
    if _mongo_client:
        _mongo_client.close()
        _mongo_client = None
        _mongo_db = None