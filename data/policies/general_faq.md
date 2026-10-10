# General FAQ — Pricing Operations

## Why are some materials missing from my plan output?
Materials can be silently excluded during price generation for 
several reasons — rule mismatches, inactive status, or missing 
master data mappings. The agent can investigate the specific 
reason for any missing material if you provide the plan name 
and material ID.

## What does "downstreamed" mean?
After prices are generated, they are sent to client systems 
such as ERP, ecommerce platforms, and wholesale management 
systems. This process is called downstreaming. A status of 
DOWNSTREAMED means the price was successfully delivered to 
the client system.

## What does "PENDING" downstream status mean?
PENDING means the price was generated but has not yet been 
sent to the client system. This is normal for plans that are 
still in progress. If a completed plan shows PENDING status 
after 24 hours, escalate to the support team.

## What does "FAILED" downstream status mean?
FAILED means the price generation succeeded but the delivery 
to the client system failed. This requires immediate developer 
investigation as it may impact live pricing in client systems.

## Can I re-run price generation for missing materials?
No. The agent cannot trigger system actions. To re-run price 
generation, contact your system administrator with the plan 
name and list of missing material IDs.

## How long does price generation take?
A typical plan with 500 materials across one region completes 
in under 5 minutes. Larger plans spanning multiple regions 
may take longer.

## Who do I contact for master data issues?
For material mapping issues (Region, Market, Channel, Hierarchy), 
contact the master data team with the material ID and the 
specific mapping that needs to be added or corrected.