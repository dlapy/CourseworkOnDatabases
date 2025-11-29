-- Полный скрипт для создания БД склада (исправленная версия)
-- Просто запусти весь этот код

DROP TABLE IF EXISTS outgoing_items CASCADE;
DROP TABLE IF EXISTS outgoing_invoices CASCADE;
DROP TABLE IF EXISTS incoming_items CASCADE;
DROP TABLE IF EXISTS incoming_invoices CASCADE;
DROP TABLE IF EXISTS stock_balances CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS staff CASCADE;
DROP TABLE IF EXISTS positions CASCADE;
DROP TABLE IF EXISTS warehouses CASCADE;

-- Таблица складов
CREATE TABLE warehouses (
    warehouse_id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    manager_name TEXT NOT NULL,
    address TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT now()
);

-- Таблица должностей
CREATE TABLE positions (
    position_id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

-- Таблица персонала
CREATE TABLE staff (
    staff_id SERIAL PRIMARY KEY,
    warehouse_id INTEGER NOT NULL REFERENCES warehouses(warehouse_id) ON DELETE CASCADE,
    inn VARCHAR(12) UNIQUE,
    full_name TEXT NOT NULL,
    position_id INTEGER NOT NULL REFERENCES positions(position_id),
    hired_at DATE DEFAULT CURRENT_DATE,
    CHECK (char_length(inn) BETWEEN 10 AND 12)
);

-- Таблица товаров
CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    sku TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    unit TEXT NOT NULL DEFAULT 'шт',
    price NUMERIC(10,2) NOT NULL CHECK (price >= 0),
    created_at TIMESTAMP DEFAULT now()
);

-- Таблица приходных накладных
CREATE TABLE incoming_invoices (
    incoming_id SERIAL PRIMARY KEY,
    warehouse_id INTEGER NOT NULL REFERENCES warehouses(warehouse_id),
    supplier TEXT NOT NULL,
    invoice_number TEXT NOT NULL,
    invoice_date DATE DEFAULT CURRENT_DATE,
    total_amount NUMERIC(12,2) DEFAULT 0 CHECK (total_amount >= 0),
    UNIQUE (warehouse_id, invoice_number)
);

-- Таблица позиций прихода
CREATE TABLE incoming_items (
    incoming_item_id SERIAL PRIMARY KEY,
    incoming_id INTEGER NOT NULL REFERENCES incoming_invoices(incoming_id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    quantity NUMERIC(12,3) NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(10,2) NOT NULL CHECK (unit_price >= 0),
    line_total NUMERIC(12,2) GENERATED ALWAYS AS (quantity * unit_price) STORED
);

-- Таблица расходных накладных
CREATE TABLE outgoing_invoices (
    outgoing_id SERIAL PRIMARY KEY,
    warehouse_id INTEGER NOT NULL REFERENCES warehouses(warehouse_id),
    customer TEXT NOT NULL,
    invoice_number TEXT NOT NULL,
    invoice_date DATE DEFAULT CURRENT_DATE,
    total_amount NUMERIC(12,2) DEFAULT 0 CHECK (total_amount >= 0),
    UNIQUE (warehouse_id, invoice_number)
);

-- Таблица позиций расхода
CREATE TABLE outgoing_items (
    outgoing_item_id SERIAL PRIMARY KEY,
    outgoing_id INTEGER NOT NULL REFERENCES outgoing_invoices(outgoing_id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    quantity NUMERIC(12,3) NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(10,2) NOT NULL CHECK (unit_price >= 0),
    line_total NUMERIC(12,2) GENERATED ALWAYS AS (quantity * unit_price) STORED
);

-- Остатки
CREATE TABLE stock_balances (
    warehouse_id INTEGER NOT NULL REFERENCES warehouses(warehouse_id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    qty NUMERIC(14,3) NOT NULL DEFAULT 0 CHECK (qty >= 0),
    last_updated TIMESTAMP DEFAULT now(),
    PRIMARY KEY (warehouse_id, product_id)
);

-- ==================== ИНДЕКСЫ ====================
CREATE INDEX idx_products_sku ON products(sku);
CREATE INDEX idx_incoming_date ON incoming_invoices(invoice_date);
CREATE INDEX idx_outgoing_date ON outgoing_invoices(invoice_date);
CREATE INDEX idx_staff_inn ON staff(inn);
CREATE INDEX idx_stock_warehouse ON stock_balances(warehouse_id);
CREATE INDEX idx_stock_product ON stock_balances(product_id);

-- ==================== ПРЕДСТАВЛЕНИЯ ====================

-- Представление: товары
CREATE OR REPLACE VIEW vw_products_info AS
SELECT product_id, sku, name, unit, price, created_at
FROM products;

-- Представление: текущие остатки 
CREATE OR REPLACE VIEW vw_current_stock AS
SELECT
    w.name AS warehouse_name,
    p.sku,
    p.name AS product_name,
    p.unit,
    p.price,
    sb.qty,
    ROUND(p.price * sb.qty, 2) AS stock_value,
    sb.last_updated
FROM stock_balances sb
JOIN warehouses w ON w.warehouse_id = sb.warehouse_id
JOIN products p ON p.product_id = sb.product_id;

-- Представление: общая стоимость запасов по складам (с GROUP BY и HAVING)
CREATE OR REPLACE VIEW vw_warehouse_stock_summary AS
SELECT
    w.name AS warehouse_name,
    SUM(p.price * sb.qty) AS total_value,
    COUNT(sb.product_id) AS product_count
FROM stock_balances sb
JOIN warehouses w ON w.warehouse_id = sb.warehouse_id
JOIN products p ON p.product_id = sb.product_id
GROUP BY w.name
HAVING SUM(p.price * sb.qty) > 0
ORDER BY total_value DESC;

-- ==================== ТРИГГЕРЫ ====================

-- Триггер: обновление total_amount для приходных накладных
CREATE OR REPLACE FUNCTION update_incoming_total()
RETURNS trigger AS $$
DECLARE
    inv_id INTEGER;
BEGIN
  -- Определяем ID накладной в зависимости от операции
  IF TG_OP = 'DELETE' THEN
    inv_id := OLD.incoming_id;
  ELSE
    inv_id := NEW.incoming_id;
  END IF;

  -- Обновляем итоговую сумму
  UPDATE incoming_invoices
     SET total_amount = (SELECT COALESCE(SUM(line_total),0)
                         FROM incoming_items WHERE incoming_id = inv_id)
   WHERE incoming_id = inv_id;
   
  IF TG_OP = 'DELETE' THEN
    RETURN OLD;
  ELSE
    RETURN NEW;
  END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_incoming_items_total
AFTER INSERT OR UPDATE OR DELETE ON incoming_items
FOR EACH ROW EXECUTE FUNCTION update_incoming_total();


-- Триггер: обновление total_amount для расходных накладных (ИСПРАВЛЕНО)
CREATE OR REPLACE FUNCTION update_outgoing_total()
RETURNS trigger AS $$
DECLARE
    inv_id INTEGER;
BEGIN
  -- Определяем ID накладной в зависимости от операции
  IF TG_OP = 'DELETE' THEN
    inv_id := OLD.outgoing_id;
  ELSE
    inv_id := NEW.outgoing_id;
  END IF;

  -- Обновляем итоговую сумму
  UPDATE outgoing_invoices
     SET total_amount = (SELECT COALESCE(SUM(line_total),0)
                         FROM outgoing_items WHERE outgoing_id = inv_id)
   WHERE outgoing_id = inv_id;
   
  IF TG_OP = 'DELETE' THEN
    RETURN OLD;
  ELSE
    RETURN NEW;
  END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_outgoing_items_total
AFTER INSERT OR UPDATE OR DELETE ON outgoing_items
FOR EACH ROW EXECUTE FUNCTION update_outgoing_total();


-- Триггер: корректировка остатков при приходе товара
CREATE OR REPLACE FUNCTION adjust_stock_on_incoming()
RETURNS trigger AS $$
DECLARE
  w_id INT;
  old_qty NUMERIC(12,3);
  new_qty NUMERIC(12,3);
BEGIN
  IF TG_OP = 'INSERT' THEN
    w_id := (SELECT warehouse_id FROM incoming_invoices WHERE incoming_id = NEW.incoming_id);
    INSERT INTO stock_balances(warehouse_id, product_id, qty, last_updated)
    VALUES (w_id, NEW.product_id, NEW.quantity, now())
    ON CONFLICT (warehouse_id, product_id)
    DO UPDATE SET qty = stock_balances.qty + EXCLUDED.qty, last_updated = now();
    RETURN NEW;
    
  ELSIF TG_OP = 'UPDATE' THEN
    w_id := (SELECT warehouse_id FROM incoming_invoices WHERE incoming_id = NEW.incoming_id);
    old_qty := OLD.quantity;
    new_qty := NEW.quantity;
    UPDATE stock_balances 
    SET qty = qty - old_qty + new_qty, last_updated = now()
    WHERE warehouse_id = w_id AND product_id = NEW.product_id;
    RETURN NEW;
    
  ELSIF TG_OP = 'DELETE' THEN
    w_id := (SELECT warehouse_id FROM incoming_invoices WHERE incoming_id = OLD.incoming_id);
    UPDATE stock_balances SET qty = qty - OLD.quantity, last_updated = now()
    WHERE warehouse_id = w_id AND product_id = OLD.product_id;
    RETURN OLD;
  END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_incoming_stock
AFTER INSERT OR UPDATE OR DELETE ON incoming_items
FOR EACH ROW EXECUTE FUNCTION adjust_stock_on_incoming();


-- Триггер: корректировка остатков при расходе товара
CREATE OR REPLACE FUNCTION adjust_stock_on_outgoing()
RETURNS trigger AS $$
DECLARE
  w_id INT;
  old_qty NUMERIC(12,3);
  new_qty NUMERIC(12,3);
BEGIN
  IF TG_OP = 'INSERT' THEN
    w_id := (SELECT warehouse_id FROM outgoing_invoices WHERE outgoing_id = NEW.outgoing_id);
    UPDATE stock_balances SET qty = qty - NEW.quantity, last_updated = now()
      WHERE warehouse_id = w_id AND product_id = NEW.product_id;
    RETURN NEW;
    
  ELSIF TG_OP = 'UPDATE' THEN
    w_id := (SELECT warehouse_id FROM outgoing_invoices WHERE outgoing_id = NEW.outgoing_id);
    old_qty := OLD.quantity;
    new_qty := NEW.quantity;
    UPDATE stock_balances 
    SET qty = qty + old_qty - new_qty, last_updated = now()
    WHERE warehouse_id = w_id AND product_id = NEW.product_id;
    RETURN NEW;
    
  ELSIF TG_OP = 'DELETE' THEN
    w_id := (SELECT warehouse_id FROM outgoing_invoices WHERE outgoing_id = OLD.outgoing_id);
    UPDATE stock_balances SET qty = qty + OLD.quantity, last_updated = now()
      WHERE warehouse_id = w_id AND product_id = OLD.product_id;
    RETURN OLD;
  END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_outgoing_stock
AFTER INSERT OR UPDATE OR DELETE ON outgoing_items
FOR EACH ROW EXECUTE FUNCTION adjust_stock_on_outgoing();

-- ==================== ТЕСТОВЫЕ ДАННЫЕ ====================

INSERT INTO warehouses (name, manager_name, address) VALUES
('Основной склад', 'Иванов И.И.', 'Ижевск, Студенческая 10'),
('Северный склад',  'Петров П.П.', 'Можга, Заводская 5'),
('Южный склад',     'Сидоров С.С.', 'Сарапул, Ленина 22');

INSERT INTO positions (name) VALUES
('Кладовщик'),
('Заведующий складом'),
('Менеджер по логистике');

INSERT INTO staff (warehouse_id, inn, full_name, position_id, hired_at) VALUES
(1, '123456789012', 'Петров Павел', 1, '2022-01-10'),
(1, '123456789013', 'Смирнов Иван',  2, '2021-05-22'),
(2, '123456789014', 'Иванова Ольга', 3, '2023-03-14');

INSERT INTO products (sku, name, unit, price) VALUES
('SKU-001', 'Подшипник 6204',       'шт', 120.50),
('SKU-002', 'Мотор-редуктор',       'шт', 4500.00),
('SKU-003', 'Кабель силовой 3x2.5', 'м', 95.00),
('SKU-004', 'Электродвигатель 1кВт', 'шт', 3200.00),
('SKU-005', 'Провод ПВС 2x1.5', 'м', 42.00);

INSERT INTO incoming_invoices (warehouse_id, supplier, invoice_number, invoice_date) VALUES
(1, 'ООО МеталлСнаб',    'INV-001', '2025-09-01'),
(1, 'ООО ЭлектроТех',    'INV-002', '2025-09-03'),
(2, 'ЗАО ЛогистикТрейд', 'INV-003', '2025-09-05'),
(3, 'ООО ТехноПоставка', 'INV-004', '2025-09-10');

INSERT INTO incoming_items (incoming_id, product_id, quantity, unit_price) VALUES
(1, 1, 100, 110.00),
(1, 3, 50, 85.00),
(2, 2, 10, 4200.00),
(2, 4, 15, 3100.00),
(3, 3, 300, 85.00),
(3, 5, 200, 40.00),
(4, 1, 50, 115.00),
(4, 2, 5, 4300.00);

INSERT INTO outgoing_invoices (warehouse_id, customer, invoice_number, invoice_date) VALUES
(1, 'ООО РемонтСервис', 'OUT-001', '2025-09-25'),
(2, 'ЗАО ЭлектроМонтаж','OUT-002', '2025-09-26'),
(3, 'ООО СтройКомплект','OUT-003', '2025-09-27'),
(1, 'ООО МастерПлюс', 'OUT-004', '2025-10-05');

INSERT INTO outgoing_items (outgoing_id, product_id, quantity, unit_price) VALUES
(1, 1, 20, 120.50),
(1, 3, 10, 95.00),
(2, 3, 50, 95.00),
(2, 5, 30, 42.00),
(3, 1, 10, 120.50),
(4, 2, 3, 4500.00),
(4, 4, 5, 3200.00);

-- Проверка представлений
SELECT * FROM vw_products_info;
SELECT * FROM vw_current_stock;
SELECT * FROM vw_warehouse_stock_summary;

-- Проверка остатков
SELECT 
    w.name as "Склад",
    p.name as "Товар",
    sb.qty as "Остаток"
FROM stock_balances sb
JOIN warehouses w ON w.warehouse_id = sb.warehouse_id
JOIN products p ON p.product_id = sb.product_id
ORDER BY w.name, p.name;