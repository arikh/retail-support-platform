from retail_support.support_tools import (
    get_downstream_status,
    get_material_rejection_reason,
    get_missing_materials,
    get_plan_status,
)


async def test_get_plan_status_known_plan():
    result = await get_plan_status.ainvoke({"plan_name": "SUMMER_LATAM_V2"})
    assert "COMPLETED" in result
    assert "8/10" in result


async def test_get_plan_status_unknown_plan():
    result = await get_plan_status.ainvoke({"plan_name": "WINTER_APAC_V9"})
    assert "not found" in result


async def test_get_missing_materials_lists_reasons():
    result = await get_missing_materials.ainvoke({"plan_name": "SUMMER_LATAM_V2"})
    assert "M-1009" in result
    assert "M-1011" in result
    assert "EXPIRY_HORIZON_RULE" in result


async def test_get_missing_materials_none_missing():
    result = await get_missing_materials.ainvoke({"plan_name": "SPRING_LATAM_2024"})
    assert "No missing materials" in result


async def test_get_missing_materials_unknown_plan():
    result = await get_missing_materials.ainvoke({"plan_name": "WINTER_APAC_V9"})
    assert "not found" in result


async def test_get_downstream_status_failed():
    result = await get_downstream_status.ainvoke({"plan_name": "SPRING_LATAM_2024"})
    assert "Failed: 2" in result
    assert "M-1007" in result
    assert "M-1008" in result


async def test_get_downstream_status_pending():
    result = await get_downstream_status.ainvoke({"plan_name": "WINTER_NA_2024"})
    assert "Pending: 6" in result


async def test_get_downstream_status_unknown_plan():
    result = await get_downstream_status.ainvoke({"plan_name": "WINTER_APAC_V9"})
    assert "not found" in result


async def test_rejection_reason_in_one_plan():
    result = await get_material_rejection_reason.ainvoke(
        {"material_id": "M-1009", "plan_name": "SUMMER_LATAM_V2"}
    )
    assert "EXPIRY_HORIZON_RULE" in result


async def test_rejection_reason_across_plans():
    result = await get_material_rejection_reason.ainvoke({"material_id": "M-1011"})
    assert "SUMMER_LATAM_V2" in result
    assert "WINTER_NA_2024" in result


async def test_rejection_reason_priced_material():
    result = await get_material_rejection_reason.ainvoke(
        {"material_id": "M-1001", "plan_name": "SUMMER_LATAM_V2"}
    )
    assert "successfully priced" in result
    assert "NOT priced" not in result


async def test_rejection_reason_unknown_material():
    result = await get_material_rejection_reason.ainvoke({"material_id": "M-9999"})
    assert "not found" in result