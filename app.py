import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime
import psycopg2


class Database:
    def __init__(self):
        try:
            self.conn = psycopg2.connect(
                host="localhost",
                port="5432",
                user="postgres",
                password="1441",
                dbname="for_term_paper"
            )
            self.cur = self.conn.cursor()
            
        except Exception as e:
            print("Ошибка подключения:", e)
            messagebox.showerror("Ошибка подключения", str(e))
            raise


    def fetch(self, query, params=None):
        try:
            self.cur.execute(query, params)
            return self.cur.fetchall()
        except Exception as e:
            print("Ошибка fetch:", e)
            self.conn.rollback()
            raise

    def execute(self, query, params=None):
        try:
            self.cur.execute(query, params)
            self.conn.commit()
        except Exception as e:
            print("Ошибка execute:", e)
            self.conn.rollback()
            raise

    

    def get_columns(self, table_name):
        """Получить список колонок таблицы"""
        try:
            query = """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = %s 
                ORDER BY ordinal_position
            """
            self.cur.execute(query, (table_name,))
            return [row[0] for row in self.cur.fetchall()]
        except Exception as e:
            print(f"Ошибка получения колонок для {table_name}:", e)
            return []


#  CRUD
class TableManagerWindow(tk.Toplevel):
    def __init__(self, db, table_name, columns):
        super().__init__()
        self.db = db
        self.table_name = table_name
        self.columns = columns

        self.title(f"Управление таблицей: {table_name}")
        self.geometry("1200x600")

        # Фрейм для поиска и фильтрации
        search_frame = tk.Frame(self)
        search_frame.pack(fill="x", padx=5, pady=5)

        tk.Label(search_frame, text="Поиск по полю:").pack(side="left")
        self.search_col = ttk.Combobox(search_frame, values=columns[1:], width=15)
        self.search_col.pack(side="left", padx=5)
        self.search_entry = tk.Entry(search_frame, width=20)
        self.search_entry.pack(side="left", padx=5)
        tk.Button(search_frame, text="Поиск", command=self.apply_filter).pack(side="left", padx=5)
        tk.Button(search_frame, text="Сброс", command=self.load_data).pack(side="left", padx=5)

        tk.Label(search_frame, text="Сортировка:").pack(side="left", padx=10)
        self.sort_col = ttk.Combobox(search_frame, values=columns, width=15)
        self.sort_col.pack(side="left", padx=5)
        self.sort_order = ttk.Combobox(search_frame, values=["ASC", "DESC"], width=5)
        self.sort_order.current(0)
        self.sort_order.pack(side="left", padx=5)
        tk.Button(search_frame, text="Сортировать", command=self.apply_sort).pack(side="left", padx=5)

        # Таблица с прокруткой
        table_frame = tk.Frame(self)
        table_frame.pack(fill="both", expand=True, padx=5, pady=5)

        scrollbar_y = ttk.Scrollbar(table_frame, orient="vertical")
        scrollbar_x = ttk.Scrollbar(table_frame, orient="horizontal")

        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings",
                                 yscrollcommand=scrollbar_y.set,
                                 xscrollcommand=scrollbar_x.set)
        
        scrollbar_y.config(command=self.tree.yview)
        scrollbar_x.config(command=self.tree.xview)
        scrollbar_y.pack(side="right", fill="y")
        scrollbar_x.pack(side="bottom", fill="x")
        self.tree.pack(side="left", fill="both", expand=True)

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120)

        # Контекстное меню
        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(label="Редактировать", command=self.edit_record)
        self.menu.add_command(label="Удалить", command=self.delete_record)
        self.tree.bind("<Button-3>", self.show_menu)
        self.tree.bind("<Double-1>", lambda e: self.edit_record())

        # Кнопки управления
        btn_frame = tk.Frame(self)
        btn_frame.pack(fill="x", pady=5, padx=5)
        tk.Button(btn_frame, text="Обновить", command=self.load_data, width=15).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Добавить", command=self.add_record, width=15).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Редактировать", command=self.edit_record, width=15).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Удалить", command=self.delete_record, width=15).pack(side="left", padx=5)

        self.load_data()

    def show_menu(self, event):
        selected = self.tree.identify_row(event.y)
        if selected:
            self.tree.selection_set(selected)
            self.menu.post(event.x_root, event.y_root)

    # def load_data(self):
    #     try:
    #         query = f"SELECT * FROM {self.table_name}"
    #         rows = self.db.fetch(query)
    #     except Exception as e:
    #         messagebox.showerror("Ошибка загрузки", str(e))
    #         return

    #     self.tree.delete(*self.tree.get_children())
    #     for row in rows:
    #         self.tree.insert("", "end", values=row)

    def load_data(self):
        try:
            if self.table_name == "staff":
                query = """
                    SELECT 
                        s.staff_id,
                        w.name AS warehouse,
                        s.full_name,
                        p.name AS position,
                        s.inn,
                        s.hired_at
                    FROM staff s
                    JOIN warehouses w ON w.warehouse_id = s.warehouse_id
                    JOIN positions p ON p.position_id = s.position_id
                    ORDER BY s.staff_id
                """

            elif self.table_name == "incoming_invoices":
                query = """
                    SELECT 
                        i.incoming_id,
                        w.name AS warehouse,
                        i.supplier,
                        i.invoice_number,
                        i.invoice_date,
                        i.total_amount
                    FROM incoming_invoices i
                    JOIN warehouses w ON w.warehouse_id = i.warehouse_id
                    ORDER BY i.incoming_id
                """

            elif self.table_name == "incoming_items":
                query = """
                    SELECT 
                        it.incoming_item_id,
                        inv.invoice_number AS invoice,
                        p.name AS product,
                        it.quantity,
                        it.unit_price,
                        it.line_total
                    FROM incoming_items it
                    JOIN incoming_invoices inv ON inv.incoming_id = it.incoming_id
                    JOIN products p ON p.product_id = it.product_id
                    ORDER BY it.incoming_item_id
                """

            elif self.table_name == "outgoing_invoices":
                query = """
                    SELECT 
                        o.outgoing_id,
                        w.name AS warehouse,
                        o.customer,
                        o.invoice_number,
                        o.invoice_date,
                        o.total_amount
                    FROM outgoing_invoices o
                    JOIN warehouses w ON w.warehouse_id = o.warehouse_id
                    ORDER BY o.outgoing_id
                """

            elif self.table_name == "outgoing_items":
                query = """
                    SELECT 
                        ot.outgoing_item_id,
                        inv.invoice_number AS invoice,
                        p.name AS product,
                        ot.quantity,
                        ot.unit_price,
                        ot.line_total
                    FROM outgoing_items ot
                    JOIN outgoing_invoices inv ON inv.outgoing_id = ot.outgoing_id
                    JOIN products p ON p.product_id = ot.product_id
                    ORDER BY ot.outgoing_item_id
                """

            elif self.table_name == "stock_balances":
                query = """
                    SELECT
                        w.name AS warehouse,
                        p.sku,
                        p.name AS product,
                        sb.qty,
                        sb.last_updated
                    FROM stock_balances sb
                    JOIN warehouses w ON w.warehouse_id = sb.warehouse_id
                    JOIN products p ON p.product_id = sb.product_id
                    ORDER BY w.name, p.name
                """

            elif self.table_name == "products":
                query = """
                    SELECT product_id, sku, name, unit, price, created_at
                    FROM products
                """

            else:
                query = f"SELECT * FROM {self.table_name}"

            rows = self.db.fetch(query)

        except Exception as e:
            messagebox.showerror("Ошибка загрузки", str(e))
            return

        self.tree.delete(*self.tree.get_children())
        for row in rows:
            self.tree.insert("", "end", values=row)



    def apply_filter(self):
        col = self.search_col.get()
        val = self.search_entry.get()
        
        if not col or not val:
            messagebox.showinfo("Поиск", "Выберите поле и введите значение для поиска")
            return

        query = f"SELECT * FROM {self.table_name} WHERE CAST({col} AS TEXT) ILIKE %s"
        params = [f"%{val}%"]

        try:
            rows = self.db.fetch(query, params)
        except Exception as e:
            messagebox.showerror("Ошибка поиска", str(e))
            return

        self.tree.delete(*self.tree.get_children())
        for row in rows:
            self.tree.insert("", "end", values=row)

    def apply_sort(self):
        order_col = self.sort_col.get()
        order = self.sort_order.get() or "ASC"

        if not order_col:
            messagebox.showinfo("Сортировка", "Выберите колонку для сортировки")
            return

        query = f"SELECT * FROM {self.table_name} ORDER BY {order_col} {order.upper()}"
        try:
            rows = self.db.fetch(query)
        except Exception as e:
            messagebox.showerror("Ошибка сортировки", str(e))
            return

        self.tree.delete(*self.tree.get_children())
        for row in rows:
            self.tree.insert("", "end", values=row)

    def edit_record(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Редактирование", "Выберите запись для редактирования")
            return
        item = self.tree.item(selected[0])
        values = item['values']
        record_id = values[0]

        edit_win = tk.Toplevel(self)
        edit_win.title("Редактировать запись")
        edit_win.geometry("400x500")

        # Создаём фрейм с прокруткой
        canvas = tk.Canvas(edit_win)
        scrollbar = ttk.Scrollbar(edit_win, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        entries = []
        for i, col in enumerate(self.columns[1:], start=1):
            tk.Label(scrollable_frame, text=col).grid(row=i-1, column=0, padx=5, pady=5, sticky="w")
            entry = tk.Entry(scrollable_frame, width=30)
            entry.grid(row=i-1, column=1, padx=5, pady=5)
            entry.insert(0, str(values[i]) if values[i] is not None else "")
            entries.append(entry)

        def save_changes():
            new_values = [e.get() for e in entries]
            set_clause = ", ".join(f"{col}=%s" for col in self.columns[1:])
            query = f"UPDATE {self.table_name} SET {set_clause} WHERE {self.columns[0]}=%s"
            try:
                self.db.execute(query, new_values + [record_id])
                messagebox.showinfo("Редактирование", "Запись обновлена")
                edit_win.destroy()
                self.load_data()
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

        tk.Button(scrollable_frame, text="Сохранить", command=save_changes).grid(
            row=len(entries), column=0, columnspan=2, pady=10
        )

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def delete_record(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Удаление", "Выберите запись для удаления")
            return
        item = self.tree.item(selected[0])
        record_id = item['values'][0]
        
        if messagebox.askyesno("Удаление", "Вы действительно хотите удалить запись?"):
            try:
                query = f"DELETE FROM {self.table_name} WHERE {self.columns[0]}=%s"
                self.db.execute(query, (record_id,))
                messagebox.showinfo("Удаление", "Запись удалена")
                self.load_data()
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

    def add_record(self):
        add_win = tk.Toplevel(self)
        add_win.title("Добавить запись")
        add_win.geometry("400x500")

        # Создаём фрейм с прокруткой
        canvas = tk.Canvas(add_win)
        scrollbar = ttk.Scrollbar(add_win, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        entries = []

        for i, col in enumerate(self.columns[1:], start=1):
            tk.Label(scrollable_frame, text=col).grid(row=i-1, column=0, padx=5, pady=5, sticky="w")

            lower_col = col.lower()

            # Дата
            if "date" in lower_col and "time" not in lower_col and "updated" not in lower_col:
                var = tk.StringVar()
                var.set(date.today().strftime("%Y-%m-%d"))
                entry = tk.Entry(scrollable_frame, textvariable=var, width=30)
                entry.grid(row=i-1, column=1, padx=5, pady=5)

            # Timestamp (только если явно created_at)
            elif "created_at" in lower_col or ("timestamp" in lower_col and "created" in lower_col):
                var = tk.StringVar()
                var.set(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                entry = tk.Entry(scrollable_frame, textvariable=var, width=30)
                entry.grid(row=i-1, column=1, padx=5, pady=5)

            else:
                # Обычное поле
                entry = tk.Entry(scrollable_frame, width=30)
                entry.grid(row=i-1, column=1, padx=5, pady=5)

            entries.append(entry)

        def save_new():
            new_values = [e.get() if e.get() != '' else None for e in entries]
            placeholders = ", ".join(["%s"] * len(new_values))
            columns_str = ", ".join(self.columns[1:])
            query = f"INSERT INTO {self.table_name} ({columns_str}) VALUES ({placeholders})"

            try:
                self.db.execute(query, new_values)
                messagebox.showinfo("Добавление", "Запись добавлена")
                add_win.destroy()
                self.load_data()
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

        tk.Button(scrollable_frame, text="Сохранить", command=save_new).grid(
            row=len(entries), column=0, columnspan=2, pady=10
        )

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")


# Приходная/расходная накладная
class InvoiceItemsWindow(tk.Toplevel):
    def __init__(self, db, invoice_type):
        super().__init__()
        self.db = db
        self.invoice_type = invoice_type  
        
        if invoice_type == 'incoming':
            self.invoice_table = "incoming_invoices"
            self.items_table = "incoming_items"
            self.invoice_id_col = "incoming_id"
            self.item_id_col = "incoming_item_id"
            self.title_text = "Приходные накладные и позиции"
        else:
            self.invoice_table = "outgoing_invoices"
            self.items_table = "outgoing_items"
            self.invoice_id_col = "outgoing_id"
            self.item_id_col = "outgoing_item_id"
            self.title_text = "Расходные накладные и позиции"

        self.title(self.title_text)
        self.geometry("1400x700")

        # Верхняя часть: накладные
        invoice_frame = tk.LabelFrame(self, text="Накладные", padx=5, pady=5)
        invoice_frame.pack(fill="both", expand=True, padx=5, pady=5)

        invoice_cols = ["ID", "Склад", "Контрагент", "Номер накладной", "Дата", "Сумма"]
        self.invoice_tree = ttk.Treeview(invoice_frame, columns=invoice_cols, show="headings", height=8)
        
        scrollbar_y = ttk.Scrollbar(invoice_frame, orient="vertical", command=self.invoice_tree.yview)
        scrollbar_x = ttk.Scrollbar(invoice_frame, orient="horizontal", command=self.invoice_tree.xview)
        self.invoice_tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        scrollbar_y.pack(side="right", fill="y")
        scrollbar_x.pack(side="bottom", fill="x")
        self.invoice_tree.pack(side="left", fill="both", expand=True)

        for col in invoice_cols:
            self.invoice_tree.heading(col, text=col)
            self.invoice_tree.column(col, width=120)

        self.invoice_tree.bind("<<TreeviewSelect>>", self.load_items)

        # Кнопки для накладных
        invoice_btn_frame = tk.Frame(self)
        invoice_btn_frame.pack(fill="x", padx=5, pady=2)
        tk.Button(invoice_btn_frame, text="Обновить накладные", command=self.load_invoices, width=20).pack(side="left", padx=5)

        # Нижняя часть: позиции накладной
        items_frame = tk.LabelFrame(self, text="Позиции выбранной накладной", padx=5, pady=5)
        items_frame.pack(fill="both", expand=True, padx=5, pady=5)

        items_cols = ["ID", "Товар", "SKU", "Количество", "Цена за единицу", "Сумма"]
        self.items_tree = ttk.Treeview(items_frame, columns=items_cols, show="headings", height=10)
        
        scrollbar_y2 = ttk.Scrollbar(items_frame, orient="vertical", command=self.items_tree.yview)
        scrollbar_x2 = ttk.Scrollbar(items_frame, orient="horizontal", command=self.items_tree.xview)
        self.items_tree.configure(yscrollcommand=scrollbar_y2.set, xscrollcommand=scrollbar_x2.set)
        
        scrollbar_y2.pack(side="right", fill="y")
        scrollbar_x2.pack(side="bottom", fill="x")
        self.items_tree.pack(side="left", fill="both", expand=True)

        for col in items_cols:
            self.items_tree.heading(col, text=col)
            self.items_tree.column(col, width=120)

        # Кнопки для позиций
        items_btn_frame = tk.Frame(self)
        items_btn_frame.pack(fill="x", padx=5, pady=2)
        tk.Button(items_btn_frame, text="Добавить позицию", command=self.add_item, width=20).pack(side="left", padx=5)
        tk.Button(items_btn_frame, text="Редактировать позицию", command=self.edit_item, width=20).pack(side="left", padx=5)
        tk.Button(items_btn_frame, text="Удалить позицию", command=self.delete_item, width=20).pack(side="left", padx=5)

        self.load_invoices()

    def load_invoices(self):
        try:
            if self.invoice_type == 'incoming':
                query = """
                    SELECT i.incoming_id,
                           w.name AS warehouse,
                           i.supplier AS counterparty,
                           i.invoice_number,
                           i.invoice_date,
                           i.total_amount
                    FROM incoming_invoices i
                    JOIN warehouses w ON w.warehouse_id = i.warehouse_id
                    ORDER BY i.invoice_date DESC
                """
            else:
                query = """
                    SELECT o.outgoing_id,
                           w.name AS warehouse,
                           o.customer AS counterparty,
                           o.invoice_number,
                           o.invoice_date,
                           o.total_amount
                    FROM outgoing_invoices o
                    JOIN warehouses w ON w.warehouse_id = o.warehouse_id
                    ORDER BY o.invoice_date DESC
                """
            rows = self.db.fetch(query)
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
            return
        
        self.invoice_tree.delete(*self.invoice_tree.get_children())
        for row in rows:
            self.invoice_tree.insert("", "end", values=row)

    def load_items(self, event=None):
        selected = self.invoice_tree.selection()
        if not selected:
            return
        invoice_id = self.invoice_tree.item(selected[0])['values'][0]
        
        try:
            if self.invoice_type == 'incoming':
                query = """
                    SELECT it.incoming_item_id,
                           p.name AS product,
                           p.sku,
                           it.quantity,
                           it.unit_price,
                           it.line_total
                    FROM incoming_items it
                    JOIN products p ON p.product_id = it.product_id
                    WHERE it.incoming_id = %s
                    ORDER BY it.incoming_item_id
                """
            else:
                query = """
                    SELECT it.outgoing_item_id,
                           p.name AS product,
                           p.sku,
                           it.quantity,
                           it.unit_price,
                           it.line_total
                    FROM outgoing_items it
                    JOIN products p ON p.product_id = it.product_id
                    WHERE it.outgoing_id = %s
                    ORDER BY it.outgoing_item_id
                """
            rows = self.db.fetch(query, (invoice_id,))
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
            return
        
        self.items_tree.delete(*self.items_tree.get_children())
        for row in rows:
            self.items_tree.insert("", "end", values=row)


    def add_item(self):
        selected = self.invoice_tree.selection()
        if not selected:
            messagebox.showinfo("Добавление", "Сначала выберите накладную")
            return
        invoice_id = self.invoice_tree.item(selected[0])['values'][0]

        add_win = tk.Toplevel(self)
        add_win.title("Добавить позицию")
        add_win.geometry("400x300")

        # Получаем список товаров
        try:
            products = self.db.fetch("SELECT product_id, name, sku, price FROM products ORDER BY name")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
            return

        tk.Label(add_win, text="Товар:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        product_var = tk.StringVar()
        product_combo = ttk.Combobox(add_win, textvariable=product_var, width=30, state="readonly")
        product_combo['values'] = [f"{p[0]} - {p[1]} ({p[2]})" for p in products]
        product_combo.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(add_win, text="Количество:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        qty_entry = tk.Entry(add_win, width=30)
        qty_entry.grid(row=1, column=1, padx=5, pady=5)

        tk.Label(add_win, text="Цена за единицу:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        price_entry = tk.Entry(add_win, width=30)
        price_entry.grid(row=2, column=1, padx=5, pady=5)

        # Автозаполнение цены при выборе товара
        def on_product_select(event):
            selection = product_combo.get()
            if selection:
                product_id = int(selection.split(' - ')[0])
                for p in products:
                    if p[0] == product_id:
                        price_entry.delete(0, tk.END)
                        price_entry.insert(0, str(p[3]))
                        break

        product_combo.bind("<<ComboboxSelected>>", on_product_select)

        def save_item():
            selection = product_combo.get()
            if not selection:
                messagebox.showwarning("Ошибка", "Выберите товар")
                return
            
            product_id = int(selection.split(' - ')[0])
            qty = qty_entry.get()
            price = price_entry.get()

            if not qty or not price:
                messagebox.showwarning("Ошибка", "Заполните все поля")
                return

            try:
                query = f"""
                    INSERT INTO {self.items_table} ({self.invoice_id_col}, product_id, quantity, unit_price)
                    VALUES (%s, %s, %s, %s)
                """
                self.db.execute(query, (invoice_id, product_id, qty, price))
                messagebox.showinfo("Успех", "Позиция добавлена")
                add_win.destroy()
                self.load_items()
                self.load_invoices()  # Обновляем для пересчёта total_amount
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

        tk.Button(add_win, text="Сохранить", command=save_item).grid(row=3, column=0, columnspan=2, pady=15)

    def edit_item(self):
        selected = self.items_tree.selection()
        if not selected:
            messagebox.showinfo("Редактирование", "Выберите позицию для редактирования")
            return
        
        item = self.items_tree.item(selected[0])
        values = item['values']
        item_id = values[0]

        edit_win = tk.Toplevel(self)
        edit_win.title("Редактировать позицию")
        edit_win.geometry("400x300")

        # Получаем список товаров
        try:
            products = self.db.fetch("SELECT product_id, name, sku FROM products ORDER BY name")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
            return

        tk.Label(edit_win, text="Товар:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        product_var = tk.StringVar()
        product_combo = ttk.Combobox(edit_win, textvariable=product_var, width=30, state="readonly")
        product_combo['values'] = [f"{p[0]} - {p[1]} ({p[2]})" for p in products]
        
        # Установить текущий товар
        current_product_id = values[2]
        for i, p in enumerate(products):
            if p[0] == current_product_id:
                product_combo.current(i)
                break
        product_combo.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(edit_win, text="Количество:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        qty_entry = tk.Entry(edit_win, width=30)
        qty_entry.insert(0, str(values[3]))
        qty_entry.grid(row=1, column=1, padx=5, pady=5)

        tk.Label(edit_win, text="Цена за единицу:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        price_entry = tk.Entry(edit_win, width=30)
        price_entry.insert(0, str(values[4]))
        price_entry.grid(row=2, column=1, padx=5, pady=5)

        def save_changes():
            selection = product_combo.get()
            if not selection:
                messagebox.showwarning("Ошибка", "Выберите товар")
                return
            
            product_id = int(selection.split(' - ')[0])
            qty = qty_entry.get()
            price = price_entry.get()

            try:
                query = f"""
                    UPDATE {self.items_table} 
                    SET product_id=%s, quantity=%s, unit_price=%s 
                    WHERE {self.item_id_col}=%s
                """
                self.db.execute(query, (product_id, qty, price, item_id))
                messagebox.showinfo("Успех", "Позиция обновлена")
                edit_win.destroy()
                self.load_items()
                self.load_invoices()
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

        tk.Button(edit_win, text="Сохранить", command=save_changes).grid(row=3, column=0, columnspan=2, pady=15)

    def delete_item(self):
        selected = self.items_tree.selection()
        if not selected:
            messagebox.showinfo("Удаление", "Выберите позицию для удаления")
            return
        
        item = self.items_tree.item(selected[0])
        item_id = item['values'][0]

        if messagebox.askyesno("Удаление", "Удалить эту позицию?"):
            try:
                query = f"DELETE FROM {self.items_table} WHERE {self.item_id_col}=%s"
                self.db.execute(query, (item_id,))
                messagebox.showinfo("Успех", "Позиция удалена")
                self.load_items()
                self.load_invoices()
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))


# Отчёты с фильтрами
class ReportWindow(tk.Toplevel):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.title("Отчёты")
        self.geometry("1200x700")

        # Выбор отчёта
        top = tk.Frame(self)
        top.pack(fill="x", padx=10, pady=10)

        tk.Label(top, text="Выберите отчёт:", font=("Arial", 12)).pack(side="left")
        self.report_type = ttk.Combobox(top, values=[
            "1. Остатки на складе",
            "2. Прибыль от реализации",
            "3. Движение товара"
        ], width=40, state="readonly")
        self.report_type.current(0)
        self.report_type.pack(side="left", padx=10)

        tk.Button(top, text="Построить отчёт", command=self.build_report).pack(side="left", padx=10)

        # Фильтры (динамически меняются)
        self.filter_frame = tk.LabelFrame(self, text="Фильтры")
        self.filter_frame.pack(fill="x", padx=10, pady=10)

        # Таблица для показа отчёта
        table_frame = tk.Frame(self)
        table_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(table_frame, show="headings")
        self.tree.pack(fill="both", expand=True)

        scrollbar_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scrollbar_y.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar_y.set)

    # Фильтры 
    def clear_filters(self):
        for widget in self.filter_frame.winfo_children():
            widget.destroy()

    # Построение отчёта 
    def build_report(self):
        report = self.report_type.get()

        if report.startswith("1"):
            self.report_stock()
        elif report.startswith("2"):
            self.report_profit()
        elif report.startswith("3"):
            self.report_movement()


    #  ОТЧЁТ 1 — Остатки на складе (vw_current_stock)
    def report_stock(self):
        self.clear_filters()

        # Фильтр по складам
        warehouses = self.db.fetch("SELECT warehouse_id, name FROM warehouses ORDER BY name")
        tk.Label(self.filter_frame, text="Склад:").grid(row=0, column=0)
        self.f_warehouse = ttk.Combobox(self.filter_frame, width=40, state="readonly")
        self.f_warehouse['values'] = ["Все"] + [f"{w[0]} - {w[1]}" for w in warehouses]
        self.f_warehouse.current(0)
        self.f_warehouse.grid(row=0, column=1, padx=5)

        tk.Button(self.filter_frame, text="Применить", command=self.load_stock).grid(row=1, column=0, columnspan=2, pady=10)

        self.load_stock()

    def load_stock(self):
        wh = self.f_warehouse.get()

        query = """
            SELECT warehouse_name, sku, product_name, unit, qty, price, stock_value, last_updated
            FROM vw_current_stock
        """
        params = []

        if wh != "Все":
            wh_name = wh.split(" - ", 1)[1]
            query += " WHERE warehouse_name = %s"
            params.append(wh_name)

        query += " ORDER BY warehouse_name, product_name"

        rows = self.db.fetch(query, params)

        cols = ["Склад", "SKU", "Товар", "Ед", "Кол-во", "Цена", "Сумма", "Обновлено"]
        self.update_table(cols, rows)


    #  ОТЧЁТ 2 — Прибыль от реализации (outgoing_items + products)
    def report_profit(self):
        self.clear_filters()

        # Фильтр по датам
        tk.Label(self.filter_frame, text="Дата с:").grid(row=0, column=0)
        self.f_date_from = tk.Entry(self.filter_frame, width=15)
        self.f_date_from.insert(0, "2025-01-01")
        self.f_date_from.grid(row=0, column=1)

        tk.Label(self.filter_frame, text="Дата по:").grid(row=0, column=2)
        self.f_date_to = tk.Entry(self.filter_frame, width=15)
        self.f_date_to.insert(0, date.today().strftime("%Y-%m-%d"))
        self.f_date_to.grid(row=0, column=3)

        tk.Button(self.filter_frame, text="Применить", command=self.load_profit).grid(row=1, column=0, columnspan=4, pady=10)

        self.load_profit()

    def load_profit(self):
        date_from = self.f_date_from.get()
        date_to = self.f_date_to.get()

        query = """
            SELECT 
                p.name AS product,
                SUM(oi.quantity) AS qty_sold,
                AVG(oi.unit_price) AS avg_sell_price,
                AVG(p.price) AS avg_buy_price,
                SUM(oi.line_total - oi.quantity * p.price) AS profit
            FROM outgoing_items oi
            JOIN outgoing_invoices inv ON inv.outgoing_id = oi.outgoing_id
            JOIN products p ON p.product_id = oi.product_id
            WHERE inv.invoice_date BETWEEN %s AND %s
            GROUP BY p.name
            ORDER BY profit DESC
        """

        rows = self.db.fetch(query, (date_from, date_to))

        cols = ["Товар", "Продано", "Цена продажи (ср.)", "Цена закупки (ср.)", "Прибыль"]
        self.update_table(cols, rows)


    #  ОТЧЁТ 3 — Движение товара (приход + расход)
    def report_movement(self):
        self.clear_filters()

        tk.Label(self.filter_frame, text="SKU:").grid(row=0, column=0)
        products = self.db.fetch("SELECT sku FROM products ORDER BY sku")
        self.f_sku = ttk.Combobox(self.filter_frame, values=["Все"] + [p[0] for p in products], width=20)
        self.f_sku.current(0)
        self.f_sku.grid(row=0, column=1, padx=5)

        tk.Button(self.filter_frame, text="Применить", command=self.load_movement).grid(row=1, column=0, columnspan=2, pady=10)

        self.load_movement()

    def load_movement(self):
        sku = self.f_sku.get()

        params = []
        where = ""

        if sku != "Все":
            where = "WHERE p.sku = %s"
            params = [sku]

        # Приход + Расход
        query = f"""
        SELECT 
            p.sku,
            p.name,
            COALESCE(inc_qty, 0) AS incoming_qty,
            COALESCE(out_qty, 0) AS outgoing_qty,
            COALESCE(inc_qty, 0) - COALESCE(out_qty, 0) AS balance_change
        FROM products p
        LEFT JOIN (
            SELECT product_id, SUM(quantity) AS inc_qty
            FROM incoming_items
            GROUP BY product_id
        ) i ON i.product_id = p.product_id
        LEFT JOIN (
            SELECT product_id, SUM(quantity) AS out_qty
            FROM outgoing_items
            GROUP BY product_id
        ) o ON o.product_id = p.product_id
        {where}
        ORDER BY p.sku
        """

        rows = self.db.fetch(query, params)

        cols = ["SKU", "Товар", "Приход", "Расход", "Изменение остатков"]
        self.update_table(cols, rows)

    # Обновление таблицы 
    def update_table(self, cols, rows):
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = cols
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150)

        for row in rows:
            self.tree.insert("", "end", values=row)


# Главное окно
class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Склад — клиентское приложение")
        self.geometry("400x400")

        self.db = Database()

        tk.Label(self, text="Управление складом",
                 font=("Arial", 16, "bold")).pack(pady=15)

        btns = [
            ("Склады", "warehouses"),
            ("Должности", "positions"),
            ("Персонал", "staff"),
            ("Товары", "products"),
            ("Приходные накладные", "incoming_invoices"),
            ("Расходные накладные", "outgoing_invoices"),
        ]

        for title, table in btns:
            tk.Button(self, text=title, width=30,
                      command=lambda t=table: self.open_table(t)).pack(pady=5)

        tk.Button(self, text="Приход + позиции", width=30,
                  command=lambda: InvoiceItemsWindow(self.db, "incoming")).pack(pady=5)

        tk.Button(self, text="Расход + позиции", width=30,
                  command=lambda: InvoiceItemsWindow(self.db, "outgoing")).pack(pady=5)

        tk.Button(self, text="Отчёты", width=30,
                  command=lambda: ReportWindow(self.db)).pack(pady=10)

    def open_table(self, table_name):
        columns = self.db.get_columns(table_name)
        if columns:
            TableManagerWindow(self.db, table_name, columns)
        else:
            messagebox.showerror("Ошибка", f"Не удалось открыть таблицу {table_name}")


if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()