from langchain_core.tools import tool

from retail_support import policy_search, pricing_lookups

get_plan_status = tool(pricing_lookups.get_plan_status)
get_missing_materials = tool(pricing_lookups.get_missing_materials)
get_downstream_status = tool(pricing_lookups.get_downstream_status)
get_material_rejection_reason = tool(pricing_lookups.get_material_rejection_reason)

# Not a database lookup: a search over the policy texts (sql/007).
search_policy = tool(policy_search.search_policy)
