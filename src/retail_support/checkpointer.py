import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]


@asynccontextmanager
async def get_checkpointer():
    async with AsyncPostgresSaver.from_conn_string(DATABASE_URL) as saver:
        yield saver
