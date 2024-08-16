from notion_client import AsyncClient

from environment import Settings

notion = AsyncClient(auth=Settings().NOTION_TOKEN)

domain = Settings().NOTION_DOMAIN

database_id = Settings().NOTION_DB_ID
