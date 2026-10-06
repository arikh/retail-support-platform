# ruff: noqa: E501
from langchain_core.tools import tool

from retail_support.db import fetch_all


@tool
async def get_rejection_reason_counts()-> str:
    """
    Count rejected (not priced) materials by rejection reason across all plans. 
    Use for the most common rejection reasons.
    """
    rows = await fetch_all(
        """
        SELECT rejection_reason,
            COUNT(*) AS rejected,
            COUNT(DISTINCT plan_id) AS plans
        FROM plan_materials
        WHERE price_status = 'NOT_PRICED'
        GROUP BY rejection_reason
        ORDER BY rejected DESC, rejection_reason
        """
    )
    if not rows:
        return "No data found."
    
    lines = []
    for r in rows:
        lines.append(f"- {r['rejection_reason']}: {r['rejected']} materials in {r['plans']} plans")
        
    return "\n".join(lines)

@tool
async def get_downstream_summary()->str:
    """
    Count downstream results (downstreamed, pending, failed) for priced materials in every plan. 
    Use to compare plans or find failures.
    """
    rows = await fetch_all(
        """
        SELECT pp.plan_name,
            COUNT(*) FILTER (WHERE pm.downstream_status = 'DOWNSTREAMED') AS downstreamed,
            COUNT(*) FILTER (WHERE pm.downstream_status = 'PENDING') AS pending,
            COUNT(*) FILTER (WHERE pm.downstream_status = 'FAILED') AS failed
        FROM plan_materials pm
        JOIN pricing_plans pp ON pm.plan_id = pp.plan_id
        WHERE pm.price_status = 'PRICED'
        GROUP BY pp.plan_name
        ORDER BY pp.plan_name
        """
    )

    if not rows:
        return "No data found."

    lines = []
    for r in rows:
        lines.append(
            f"- {r['plan_name']} | "
            f"Downstreamed: {r['downstreamed']} | "
            f"Pending: {r['pending']} | Failed: {r['failed']}"
        )

    return "\n".join(lines)

@tool
async def list_plans() ->str:
    """
    List every pricing plan with region, season, status, creation date and priced/total counts. 
    Use to see which plans and dates the data covers.
    """
    rows = await fetch_all(
        """
        SELECT plan_name, region, season, status, created_at,
            total_materials, priced_materials
        FROM pricing_plans
        ORDER BY created_at
        """
    )

    if not rows:
        return "No data found."

    lines = []
    for r in rows:
        lines.append(
            f"- {r['plan_name']} | Region: {r['region']} | Season: {r['season']} | "
            f"Status: {r['status']} | Created: {r['created_at']} | Priced: {r['priced_materials']}/{r['total_materials']}"
        )
    return "\n".join(lines)