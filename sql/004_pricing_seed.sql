-- Sample pricing data, ported row for row from the capstone SQLite
-- database (retail-ai-support-agent, data/pricing.db).
-- Safe to run more than once: existing rows are left alone.

INSERT INTO pricing_rules (rule_name, description, active) VALUES
    ('EXPIRY_HORIZON_RULE', 'Material expiry months must be >= plan pricing horizon months. Example: 6-month plan requires material expiry >= 6 months.', true),
    ('ACTIVE_MATERIAL_RULE', 'Only active materials can be included in a pricing plan. Inactive or discontinued materials are automatically excluded.', true),
    ('MARKET_MAPPING_RULE', 'Material must be mapped to the plan region, market, and channel combination in master data. Missing mapping causes silent exclusion.', true),
    ('CATEGORY_CHANNEL_RULE', 'Certain product categories are restricted to specific channels. Example: Pool products cannot be priced for EU Wholesale channel.', true)
ON CONFLICT (rule_name) DO NOTHING;

INSERT INTO materials (material_id, material_name, category, expiry_months, active) VALUES
    ('M-1001', 'Winter Jacket XL', 'Outerwear', 6, true),
    ('M-1002', 'Summer Dress S', 'Apparel', 3, true),
    ('M-1003', 'Running Shoes Size 10', 'Footwear', 12, true),
    ('M-1004', 'Leather Belt', 'Accessories', 24, true),
    ('M-1005', 'Wool Scarf', 'Accessories', 6, true),
    ('M-1006', 'Denim Jeans 32', 'Apparel', 12, true),
    ('M-1007', 'Polo Shirt M', 'Apparel', 3, true),
    ('M-1008', 'Canvas Tote Bag', 'Accessories', 18, true),
    ('M-1009', 'Silk Blouse L', 'Apparel', 2, true),
    ('M-1010', 'Formal Trousers 34', 'Apparel', 12, true),
    ('M-1011', 'Expired Product A', 'Apparel', 1, true),
    ('M-1012', 'Discontinued Item B', 'Footwear', NULL, false),
    ('M-2001', 'Garden Hose 50ft', 'Hardware', 24, true),
    ('M-2002', 'Power Drill Set', 'Tools', 36, true),
    ('M-2003', 'Paint Brush Set', 'Hardware', 12, true),
    ('M-3001', 'Pool Chlorine Tablets', 'Pool', 3, true),
    ('M-3002', 'Pool Vacuum Head', 'Pool', 24, true),
    ('M-3003', 'Swim Goggles', 'Pool', 6, true)
ON CONFLICT (material_id) DO NOTHING;

INSERT INTO pricing_plans (plan_id, plan_name, region, market, channel, season, status, created_at, total_materials, priced_materials) VALUES
    ('PLAN-001', 'SUMMER_LATAM_V2', 'LATAM', 'Brazil', 'Wholesale', 'Summer', 'COMPLETED', '2024-01-15', 10, 8),
    ('PLAN-002', 'FALL_EU_2024', 'EU', 'Germany', 'Retail', 'Fall', 'COMPLETED', '2024-02-10', 6, 5),
    ('PLAN-003', 'WINTER_NA_2024', 'NA', 'USA', 'Wholesale', 'Winter', 'IN_PROGRESS', '2024-03-01', 8, 6),
    ('PLAN-004', 'SPRING_LATAM_2024', 'LATAM', 'Mexico', 'Retail', 'Spring', 'COMPLETED', '2024-03-15', 5, 5)
ON CONFLICT (plan_id) DO NOTHING;

INSERT INTO plan_materials (plan_id, material_id, season, price_status, downstream_status, rejection_reason, price_value) VALUES
    ('PLAN-001', 'M-1001', 'Summer', 'PRICED', 'DOWNSTREAMED', NULL, 45.99),
    ('PLAN-001', 'M-1002', 'Summer', 'PRICED', 'DOWNSTREAMED', NULL, 29.99),
    ('PLAN-001', 'M-1003', 'Summer', 'PRICED', 'DOWNSTREAMED', NULL, 89.99),
    ('PLAN-001', 'M-1004', 'Summer', 'PRICED', 'DOWNSTREAMED', NULL, 34.99),
    ('PLAN-001', 'M-1005', 'Summer', 'PRICED', 'DOWNSTREAMED', NULL, 19.99),
    ('PLAN-001', 'M-1006', 'Summer', 'PRICED', 'DOWNSTREAMED', NULL, 59.99),
    ('PLAN-001', 'M-1007', 'Summer', 'PRICED', 'DOWNSTREAMED', NULL, 24.99),
    ('PLAN-001', 'M-1008', 'Summer', 'PRICED', 'DOWNSTREAMED', NULL, 14.99),
    ('PLAN-001', 'M-1009', 'Summer', 'NOT_PRICED', NULL, 'EXPIRY_HORIZON_RULE', NULL),
    ('PLAN-001', 'M-1011', 'Summer', 'NOT_PRICED', NULL, 'EXPIRY_HORIZON_RULE', NULL),
    ('PLAN-002', 'M-1001', 'Fall', 'PRICED', 'DOWNSTREAMED', NULL, 52.99),
    ('PLAN-002', 'M-1004', 'Fall', 'PRICED', 'DOWNSTREAMED', NULL, 36.99),
    ('PLAN-002', 'M-1005', 'Fall', 'PRICED', 'DOWNSTREAMED', NULL, 22.99),
    ('PLAN-002', 'M-1006', 'Fall', 'PRICED', 'DOWNSTREAMED', NULL, 64.99),
    ('PLAN-002', 'M-1010', 'Fall', 'PRICED', 'DOWNSTREAMED', NULL, 74.99),
    ('PLAN-002', 'M-3001', 'Fall', 'NOT_PRICED', NULL, 'CATEGORY_CHANNEL_RULE', NULL),
    ('PLAN-003', 'M-1001', 'Winter', 'PRICED', 'PENDING', NULL, 67.99),
    ('PLAN-003', 'M-1003', 'Winter', 'PRICED', 'PENDING', NULL, 94.99),
    ('PLAN-003', 'M-1004', 'Winter', 'PRICED', 'PENDING', NULL, 38.99),
    ('PLAN-003', 'M-1005', 'Winter', 'PRICED', 'PENDING', NULL, 27.99),
    ('PLAN-003', 'M-1006', 'Winter', 'PRICED', 'PENDING', NULL, 72.99),
    ('PLAN-003', 'M-1010', 'Winter', 'PRICED', 'PENDING', NULL, 82.99),
    ('PLAN-003', 'M-1011', 'Winter', 'NOT_PRICED', NULL, 'EXPIRY_HORIZON_RULE', NULL),
    ('PLAN-003', 'M-1012', 'Winter', 'NOT_PRICED', NULL, 'ACTIVE_MATERIAL_RULE', NULL),
    ('PLAN-004', 'M-1002', 'Spring', 'PRICED', 'DOWNSTREAMED', NULL, 31.99),
    ('PLAN-004', 'M-1003', 'Spring', 'PRICED', 'DOWNSTREAMED', NULL, 91.99),
    ('PLAN-004', 'M-1006', 'Spring', 'PRICED', 'DOWNSTREAMED', NULL, 61.99),
    ('PLAN-004', 'M-1007', 'Spring', 'PRICED', 'FAILED', NULL, 26.99),
    ('PLAN-004', 'M-1008', 'Spring', 'PRICED', 'FAILED', NULL, 16.99)
ON CONFLICT (plan_id, material_id) DO NOTHING;
