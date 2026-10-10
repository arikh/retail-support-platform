# Material Setup Guide

## What is a Material?
A material is a sellable product unit in the pricing platform. 
Each material has a unique ID in the format M-XXXX (e.g. M-1001).

## Material Dimensions
Every material must be correctly mapped across these dimensions 
before it can be included in a pricing plan:
- Region (e.g. NA, LATAM, EU)
- Market (e.g. USA, Brazil, Germany)
- Channel (e.g. Wholesale, Retail)
- Product Hierarchy (e.g. Apparel > Outerwear > Jackets)
- Season (e.g. Summer, Winter, Fall, Spring)

## Why Materials Go Missing
The most common reasons materials are excluded from a pricing run:

1. Expiry mismatch — material expiry shorter than plan horizon
2. Inactive status — material marked as discontinued
3. Missing market mapping — material not mapped to plan dimensions
4. Category-channel restriction — product type not allowed in channel

## Master Data Issues
If a material is missing due to a mapping issue, the resolution 
always involves the master data team — not the pricing planner. 
The planner cannot fix mapping issues directly in the pricing tool.

## Checking Material Status
To check if a material is active and correctly mapped, contact 
your system administrator or raise a support ticket with the 
material ID and the plan dimensions.