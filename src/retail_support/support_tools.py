from langchain_core.tools import tool

from retail_support.db import fetch_all


async def plan_exists(plan_name: str) -> bool:
    rows = await fetch_all(
        """
        SELECT 1 FROM pricing_plans WHERE plan_name = %s
        """,
        (plan_name,),
    )
    return bool(rows)

@tool
async def get_plan_status(plan_name: str) -> str:
    """
    Get the overall status of a pricing plan including how many
    materials were priced vs total selected.
    Use this when user asks about plan completeness or status.
    """
    rows = await fetch_all(
        """
        SELECT plan_name, region, market, channel, season,
               status, total_materials, priced_materials
        FROM pricing_plans
        WHERE plan_name = %s
        """,
        (plan_name,),
    )

    if not rows:
        return f"Plan '{plan_name}' not found. Please verify the plan name."

    r = rows[0]
    missing = r["total_materials"] - r["priced_materials"]
    return (
        f"Plan: {r['plan_name']} | Region: {r['region']} | "
        f"Market: {r['market']} | Channel: {r['channel']} | "
        f"Season: {r['season']} | Status: {r['status']} | "
        f"Materials priced: {r['priced_materials']}/{r['total_materials']} | "
        f"Missing: {missing}"
    )

@tool
async def get_missing_materials(plan_name: str) -> str:
    """
    Get all materials that were selected in a plan but were NOT priced,
    along with the rejection reason for each.
    Use this when user asks why materials are missing or not showing up.
    """
    if not await plan_exists(plan_name):
        return f"Plan {plan_name} not found."

    rows = await fetch_all(
        """
        SELECT pm.material_id, m.material_name,
            pm.rejection_reason, m.expiry_months
        FROM plan_materials pm
        JOIN pricing_plans pp ON pm.plan_id = pp.plan_id
        JOIN materials m ON pm.material_id = m.material_id
        WHERE pp.plan_name = %s
        AND pm.price_status = 'NOT_PRICED'
        """,
        (plan_name,),
    )

    if not rows:
        return f"No missing materials found for plan '{plan_name}'."

    result = f"Missing materials in '{plan_name}':\n"
    for r in rows:
        result += (
            f"- {r['material_id']} ({r['material_name']}) | "
            f"Reason: {r['rejection_reason']} | "
            f"Expiry: {r['expiry_months']} months\n"
        )
    return result


@tool
async def get_downstream_status(plan_name: str) -> str:
    """
    Get the downstream propagation status for all priced materials in a plan.
    Use this when user asks if prices were sent to client systems or downstreamed.
    """
    if not await plan_exists(plan_name):
            return f"Plan {plan_name} not found."
    
    rows = await fetch_all(
        """
        SELECT pm.material_id, m.material_name, pm.downstream_status
        FROM plan_materials pm
        JOIN pricing_plans pp ON pm.plan_id = pp.plan_id
        JOIN materials m ON pm.material_id = m.material_id
        WHERE pp.plan_name = %s
        AND pm.price_status = 'PRICED'
        """,
        (plan_name,),
    )

    if not rows:
        return f"No priced materials found for plan '{plan_name}'."

    failed = [r for r in rows if r["downstream_status"] == "FAILED"]
    pending = [r for r in rows if r["downstream_status"] == "PENDING"]
    success = [r for r in rows if r["downstream_status"] == "DOWNSTREAMED"]

    result = (
        f"Downstream status for '{plan_name}':\n"
        f"Downstreamed: {len(success)} | "
        f"Pending: {len(pending)} | "
        f"Failed: {len(failed)}\n"
    )

    if failed:
        result += "Failed materials:\n"
        for r in failed:
            result += f"- {r['material_id']} ({r['material_name']})\n"

    return result


@tool
async def get_material_rejection_reason(material_id: str, plan_name: str = "") -> str:
    """
    Get the rejection reason for a specific material in a plan.
    Use this when user asks why a specific material was not priced
    or what rule caused a material to be excluded.
    """
    if plan_name:
        rows = await fetch_all(
            """
            SELECT pm.material_id, m.material_name,
                   pm.price_status, pm.rejection_reason,
                   m.expiry_months, pp.plan_name
            FROM plan_materials pm
            JOIN materials m ON pm.material_id = m.material_id
            JOIN pricing_plans pp ON pm.plan_id = pp.plan_id
            WHERE pm.material_id = %s AND pp.plan_name = %s
            """,
            (material_id, plan_name),
        )
    else:
        rows = await fetch_all(
            """
            SELECT pm.material_id, m.material_name,
                   pm.price_status, pm.rejection_reason,
                   m.expiry_months, pp.plan_name
            FROM plan_materials pm
            JOIN materials m ON pm.material_id = m.material_id
            JOIN pricing_plans pp ON pm.plan_id = pp.plan_id
            WHERE pm.material_id = %s
            """,
            (material_id,),
        )

    if not rows:
        return f"Material '{material_id}' not found."

    lines = []
    for r in rows:
        if r["price_status"] == "PRICED":
            lines.append (
                f"Material {material_id} ({r['material_name']}) was successfully "
                f"priced in plan '{r['plan_name']}'."
            )
        else:
            lines.append (
                f"Material {material_id} ({r['material_name']}) was NOT priced.\n"
                f"Plan: {r['plan_name']} | "
                f"Reason: {r['rejection_reason']} | "
                f"Expiry: {r['expiry_months']} months"
            )
    
    return "\n".join(lines)