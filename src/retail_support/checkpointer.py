import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from retail_support.state import (
    AnalysisFindings,
    EscalationFindings,
    PendingApproval,
    SupportFindings,
)

load_dotenv() # TODO(env): temporary — centralize at app entry point, strip from modules

DATABASE_URL = os.environ["DATABASE_URL"]


@asynccontextmanager
async def get_checkpointer():
    async with AsyncPostgresSaver.from_conn_string(
        DATABASE_URL, serde=build_serde()
    ) as saver:
        yield saver

def build_serde() -> JsonPlusSerializer:
    return JsonPlusSerializer(
        allowed_msgpack_modules=[
            SupportFindings,
            AnalysisFindings,
            EscalationFindings,
            PendingApproval,
        ]
    )



