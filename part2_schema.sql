-- Core company entity
CREATE TABLE companies (
    id            SERIAL PRIMARY KEY,
    name          VARCHAR(255) NOT NULL,
    created_at    TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Warehouses belong to a company
CREATE TABLE warehouses (
    id            SERIAL PRIMARY KEY,
    company_id    INT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    name          VARCHAR(255) NOT NULL,
    address       TEXT,
    created_at    TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Suppliers are separate entities; linked to companies via a join table
CREATE TABLE suppliers (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    contact_email   VARCHAR(255),
    contact_phone   VARCHAR(50),
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE company_suppliers (
    company_id    INT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    supplier_id   INT NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    PRIMARY KEY (company_id, supplier_id)
);

-- Products belong to a company; SKU is unique platform-wide
CREATE TABLE products (
    id              SERIAL PRIMARY KEY,
    company_id      INT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    supplier_id     INT REFERENCES suppliers(id) ON DELETE SET NULL,
    name            VARCHAR(255) NOT NULL,
    sku             VARCHAR(100) NOT NULL UNIQUE,
    description     TEXT,
    price           NUMERIC(12, 2) NOT NULL CHECK (price >= 0),
    product_type    VARCHAR(50) NOT NULL DEFAULT 'standard', -- 'standard' | 'bundle'
    low_stock_threshold INT NOT NULL DEFAULT 10,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_products_company ON products(company_id);
CREATE INDEX idx_products_sku ON products(sku);

-- Inventory: how much of a product is in each warehouse
CREATE TABLE inventory (
    id              SERIAL PRIMARY KEY,
    product_id      INT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    warehouse_id    INT NOT NULL REFERENCES warehouses(id) ON DELETE CASCADE,
    quantity        INT NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (product_id, warehouse_id)  -- one row per product-warehouse pair
);

CREATE INDEX idx_inventory_product ON inventory(product_id);
CREATE INDEX idx_inventory_warehouse ON inventory(warehouse_id);

-- Audit log of every inventory change
CREATE TABLE inventory_transactions (
    id              SERIAL PRIMARY KEY,
    inventory_id    INT NOT NULL REFERENCES inventory(id),
    change_quantity INT NOT NULL,           -- positive = stock in, negative = stock out
    reason          VARCHAR(100),           -- 'sale', 'restock', 'adjustment', etc.
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_inv_tx_inventory ON inventory_transactions(inventory_id);
CREATE INDEX idx_inv_tx_created ON inventory_transactions(created_at);

-- Bundle products contain other products
CREATE TABLE bundle_items (
    bundle_product_id   INT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    component_product_id INT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    quantity            INT NOT NULL DEFAULT 1 CHECK (quantity > 0),
    PRIMARY KEY (bundle_product_id, component_product_id)
);
