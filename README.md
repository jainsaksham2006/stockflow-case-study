# StockFlow - Backend Engineering Intern Case Study

Backend case study solution for the StockFlow inventory management platform.

---

## Part 1: Code Review & Debugging

### Issues Found in Original Code

1. **No input validation** — code crashed with unhandled `KeyError` if any field was missing
2. **No SKU uniqueness check** — duplicate SKUs could be silently inserted
3. **Two separate commits** — if the `Inventory` insert failed, a `Product` row was left orphaned in the database with no stock record
4. **No price validation** — negative prices or non-numeric values were accepted
5. **No warehouse validation** — invalid `warehouse_id` caused a database error instead of a clean 400/404
6. **No authentication** — anyone could hit the endpoint
7. **Wrong HTTP status** — returned 200 instead of 201 on successful creation
8. **No quantity validation** — negative inventory quantities were possible

### Fix Summary
- Added full input validation with meaningful error messages
- Used `db.session.flush()` + single `db.session.commit()` to make both inserts atomic
- Added SKU uniqueness check before inserting
- Added `@require_auth` decorator
- Returns `201 Created` on success

---

## Part 2: Database Schema

### Tables
- `companies` — top-level entity owning warehouses and products
- `warehouses` — belong to a company, hold inventory
- `suppliers` — external entities providing products
- `company_suppliers` — many-to-many join between companies and suppliers
- `products` — belong to a company, SKU is unique platform-wide
- `inventory` — tracks quantity of a product in a specific warehouse
- `inventory_transactions` — append-only audit log of every stock change
- `bundle_items` — self-referencing join table for bundle products

### Key Design Decisions
- `NUMERIC(12,2)` for price to avoid floating-point rounding errors
- `UNIQUE(product_id, warehouse_id)` on inventory enforces one row per location
- `inventory_transactions` is append-only — never deleted, used for audit trail and sales velocity calculations
- `low_stock_threshold` stored per product since it varies by product type
- Indexes added on all foreign keys and frequently filtered columns

### Assumptions Made
- SKU is unique across the entire platform, not just per company
- A product has one primary supplier
- Bundles do not nest (no bundles-within-bundles)

### Questions I Would Ask the Product Team
1. Is SKU unique per company or truly platform-wide?
2. What defines "recent" for sales activity — 7 days? 30 days? Configurable?
3. Can a product have multiple suppliers?
4. Can bundles contain other bundles?
5. Do we need multi-currency support for price?
6. Should `low_stock_threshold` be per product-warehouse pair or just per product?

---

## Part 3: Low-Stock Alerts API

### Endpoint
`GET /api/companies/{company_id}/alerts/low-stock`

### Assumptions Made
- "Recent sales activity" = at least one sale transaction in the last 30 days
- `days_until_stockout` = current stock divided by average daily sales over 30 days
- Returns `null` for `days_until_stockout` if no recent sales data exists
- One alert raised per product-warehouse pair

### Edge Cases Handled
- Company not found → 404
- Unauthorized access → 403
- Product has no supplier → `supplier` field returns `null`
- No recent sales → product excluded from alerts
- Zero average daily sales → `days_until_stockout` returns `null` (no division by zero)
- No alerts exist → returns empty list cleanly

---

## Assumptions & Notes

- `@require_auth` and `current_user_can_access()` are assumed to be implemented elsewhere in the application
- Database models (`Product`, `Inventory`, `Warehouse`, `Company`) are assumed to be defined using SQLAlchemy
- PostgreSQL is assumed as the database (uses `SERIAL`, `NUMERIC`, `TIMESTAMP`)
