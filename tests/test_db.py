import psycopg
import pytest

from retail_support.db import fetch_all


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
