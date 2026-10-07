import os

import psycopg
import pytest

from retail_support import db
from retail_support.db import fetch_all


async def test_use_database_url_switches_the_database_user(monkeypatch):
    monkeypatch.setattr(db, "_database_url", None)  # pytest restores it after the test
    db.use_database_url(os.environ["MCP_DATABASE_URL"])

    rows = await db.fetch_all("select current_user")

    assert rows == [{"current_user": "retail_mcp_ro"}]

async def test_fetch_all_returns_rows_as_dicts():
    rows = await fetch_all(
        "SELECT plan_name, status FROM pricing_plans WHERE plan_id = %s",
        ("PLAN-001",),
    )
    assert rows == [{"plan_name": "SUMMER_LATAM_V2", "status": "COMPLETED"}]


async def test_fetch_all_returns_empty_list_when_nothing_matches():
    rows = await fetch_all(
        "SELECT plan_name FROM pricing_plans WHERE plan_id = %s",
        ("NO-SUCH-PLAN",),
    )
    assert rows == []


async def test_connection_is_read_only():
    with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
        await fetch_all(
            "DELETE FROM plan_materials WHERE plan_id = %s",
            ("NO-SUCH-PLAN",),
        )
