from flask import request, jsonify
from sqlalchemy.exc import IntegrityError
from decimal import Decimal, InvalidOperation

@app.route('/api/products', methods=['POST'])
@require_auth  # authentication decorator
def create_product():
    data = request.get_json()

    # Validate request body exists
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    # Validate required fields
    required_fields = ['name', 'sku', 'price', 'warehouse_id', 'initial_quantity']
    missing = [f for f in required_fields if f not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {missing}"}), 400

    # Validate price is a positive decimal
    try:
        price = Decimal(str(data['price']))
        if price < 0:
            raise ValueError()
    except (InvalidOperation, ValueError):
        return jsonify({"error": "Price must be a non-negative number"}), 400

    # Validate quantity is non-negative integer
    initial_quantity = data['initial_quantity']
    if not isinstance(initial_quantity, int) or initial_quantity < 0:
        return jsonify({"error": "initial_quantity must be a non-negative integer"}), 400

    # Validate warehouse exists
    warehouse = Warehouse.query.get(data['warehouse_id'])
    if not warehouse:
        return jsonify({"error": "Warehouse not found"}), 404

    # Check SKU uniqueness
    if Product.query.filter_by(sku=data['sku']).first():
        return jsonify({"error": "SKU already exists"}), 409

    try:
        # Single atomic transaction — both inserts succeed or both roll back
        product = Product(
            name=data['name'],
            sku=data['sku'],
            price=price,
            warehouse_id=data['warehouse_id']
        )
        db.session.add(product)
        db.session.flush()  # get product.id without committing yet

        inventory = Inventory(
            product_id=product.id,
            warehouse_id=data['warehouse_id'],
            quantity=initial_quantity
        )
        db.session.add(inventory)
        db.session.commit()  # single atomic commit

    except IntegrityError as e:
        db.session.rollback()
        return jsonify({"error": "Database integrity error", "detail": str(e)}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Internal server error"}), 500

    # Return 201 Created
    return jsonify({"message": "Product created", "product_id": product.id}), 201

