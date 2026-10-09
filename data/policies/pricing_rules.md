# Pricing Rules Reference

## EXPIRY_HORIZON_RULE
Materials must have an expiry duration greater than or equal to the 
plan pricing horizon. 

Example: If a pricing plan generates prices for a 6-month horizon, 
all selected materials must have an expiry of at least 6 months. 
A material with a 2-month expiry will be silently excluded from the 
price generation run.

Resolution: Either remove the material from the plan, or adjust the 
plan pricing horizon to match the material expiry.

## ACTIVE_MATERIAL_RULE
Only active materials can be included in a pricing plan. Materials 
marked as inactive or discontinued are automatically excluded from 
price generation regardless of other settings.

Resolution: Contact the master data team to reactivate the material, 
or remove it from the plan selection.

## CATEGORY_CHANNEL_RULE
Certain product categories are restricted to specific sales channels. 
For example, pool and outdoor products cannot be priced for the EU 
Wholesale channel due to regional distribution restrictions.

Resolution: Verify the category-channel mapping with the master data 
team. Remove the material from the plan if the channel restriction 
cannot be changed.

## MARKET_MAPPING_RULE
Every material must be mapped to the specific Region, Market, and 
Channel combination used in the pricing plan. If a material exists 
in the system but is not mapped to the plan's market combination, 
it will be silently excluded.

Resolution: Contact the master data team to add the missing 
Region-Market-Channel mapping for the material.