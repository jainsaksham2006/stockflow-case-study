from flask import jsonify
from sqlalchemy import text
from datetime import datetime, timedelta

@app.route('/api/companies/<int:company_id>/alerts/low-stock', methods=['GET'])
@require_auth
def low_stock_alerts(company_id):
    company = Company.query.get(company_id)
    if not company:
        return jsonify({"error": "Company not found"}), 404

    if not current_user_can_access(company_id):
        return jsonify({"error": "Forbidden"}), 403

    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    # CTE calculates average daily sales per product/warehouse over last 30 days.
    # Only products with actual sales activity are included.
    query = text("""
        WITH recent_sales AS (
            SELECT
                i.product_id,
                i.warehouse_id,
                ABS(SUM(CASE WHEN it.change_quantity < 0 THEN it.change_quantity ELSE 0 END)) AS units_sold,
                ABS(SUM(CASE WHEN it.change_quantity < 0 THEN it.change_quantity ELSE 0 END)) / 30.0 AS avg_daily_sales
            FROM inventory i
            JOIN inventory_transactions it ON it.inventory_id = i.id
            JOIN warehouses w ON w.id = i.warehouse_id
            WHERE w.company_id = :company_id
              AND it.created_at >= :since
              AND it.change_quantity < 0
            GROUP BY i.product_id, i.warehouse_id
            HAVING ABS(SUM(CASE WHEN it.change_quantity < 0 THEN it.change_quantity ELSE 0 END)) > 0
        )
        SELECT
            p.id                  AS product_id,
            p.name                AS product_name,
            p.sku,
            w.id                  AS warehouse_id,
            w.name                AS warehouse_name,
            inv.quantity          AS current_stock,
            p.low_stock_threshold AS threshold,
            rs.avg_daily_sales,
            s.id                  AS supplier_id,
            s.name                AS supplier_name,
            s.contact_email       AS supplier_email
        FROM inventory inv
        JOIN products p       ON p.id = inv.product_id
        JOIN warehouses w     ON w.id = inv.warehouse_id
        JOIN recent_sales rs  ON rs.product_id = inv.product_id
                              AND rs.warehouse_id = inv.warehouse_id
        LEFT JOIN suppliers s ON s.id = p.supplier_id
        WHERE w.company_id = :company_id
          AND p.is_active = TRUE
          AND inv.quantity < p.low_stock_threshold
        ORDER BY inv.quantity ASC
    """)

    rows = db.session.execute(query, {
        "company_id": company_id,
        "since": thirty_days_ago
    }).fetchall()

    alerts = []
    for row in rows:
        # Avoid division by zero for days_until_stockout
        if row.avg_daily_sales and row.avg_daily_sales > 0:
            days_until_stockout = round(row.current_stock / row.avg_daily_sales)
        else:
            days_until_stockout = None

        alerts.append({
            "product_id":          row.product_id,
            "product_name":        row.product_name,
            "sku":                 row.sku,
            "warehouse_id":        row.warehouse_id,
            "warehouse_name":      row.warehouse_name,
            "current_stock":       row.current_stock,
            "threshold":           row.threshold,
            "days_until_stockout": days_until_stockout,
            "supplier": {
                "id":            row.supplier_id,
                "name":          row.supplier_name,
                "contact_email": row.supplier_email
            } if row.supplier_id else None
        })

    return jsonify({
        "alerts":       alerts,
        "total_alerts": len(alerts)
    }), 200
