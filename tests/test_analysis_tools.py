from retail_support.analysis_tools import (
    get_downstream_summary,
    get_rejection_reason_counts,
    list_plans,
)


async def test_rejection_reason_counts():
    result = await get_rejection_reason_counts.ainvoke({})
    assert "EXPIRY_HORIZON_RULE: 3 materials in 2 plans" in result
    assert "ACTIVE_MATERIAL_RULE: 1" in result
    assert "CATEGORY_CHANNEL_RULE: 1" in result


async def test_downstream_summary():
    result = await get_downstream_summary.ainvoke({})
    assert "SPRING_LATAM_2024 | Downstreamed: 3 | Pending: 0 | Failed: 2" in result
    assert "WINTER_NA_2024 | Downstreamed: 0 | Pending: 6 | Failed: 0" in result


async def test_list_plans():
    result = await list_plans.ainvoke({})
    assert result.count("- ") == 4
    assert "Created: 2024-01-15" in result
    assert "Priced: 8/10" in result