# app.py
import os
from flask import Flask, render_template, request, redirect, url_for, flash, make_response
import psycopg2
from dotenv import load_dotenv
# import pdfkit
from datetime import datetime
import csv
from io import StringIO

# Загружаем переменные окружения из .env
load_dotenv()

# Создаём Flask-приложение
app = Flask(__name__)
app.secret_key = 'warehouse_capacity_secret_key_2025'  # Обязателен для flash-сообщений

# Функция подключения к БД
def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        database=os.getenv('DB_NAME', 'warehouse_capacity'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD')
    )
    return conn

# === Главная страница ===
@app.route('/')
def index():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT name FROM clients LIMIT 5;')
        clients = cur.fetchall()  # Получаем список кортежей: [('Клиент1',), ('Клиент2',), ...]
        cur.close()
        conn.close()
        return render_template('index.html', clients=clients)
    except Exception as e:
        return f"<h1>❌ Ошибка подключения</h1><p>{str(e)}</p>"

# === CRUD: Справочник клиентов ===

@app.route('/clients')
def client_list():
    """Просмотр списка клиентов"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT client_id, name, contact_person FROM clients ORDER BY name;')
    clients = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('clients/list.html', clients=clients)

@app.route('/clients/create', methods=('GET', 'POST'))
def client_create():
    """Добавление нового клиента"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        contact = request.form.get('contact_person', '').strip()
        if not name:
            flash('Название клиента обязательно для заполнения!', 'error')
        else:
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute(
                    'INSERT INTO clients (name, contact_person) VALUES (%s, %s);',
                    (name, contact)
                )
                conn.commit()
                cur.close()
                conn.close()
                flash('Клиент успешно добавлен!', 'success')
                return redirect(url_for('client_list'))
            except Exception as e:
                flash(f'Ошибка при добавлении клиента: {e}', 'error')
    return render_template('clients/create.html')

@app.route('/clients/edit/<int:id>', methods=('GET', 'POST'))
def client_edit(id):
    """Редактирование клиента"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT client_id, name, contact_person FROM clients WHERE client_id = %s;', (id,))
    client = cur.fetchone()
    if not client:
        flash('Клиент не найден.', 'error')
        return redirect(url_for('client_list'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        contact = request.form.get('contact_person', '').strip()
        if not name:
            flash('Название клиента обязательно!', 'error')
        else:
            try:
                cur.execute(
                    'UPDATE clients SET name = %s, contact_person = %s WHERE client_id = %s;',
                    (name, contact, id)
                )
                conn.commit()
                flash('Данные клиента обновлены!', 'success')
                return redirect(url_for('client_list'))
            except Exception as e:
                flash(f'Ошибка при обновлении: {e}', 'error')
    
    cur.close()
    conn.close()
    return render_template('clients/edit.html', client=client)

@app.route('/clients/delete/<int:id>', methods=('GET', 'POST'))
def client_delete(id):
    """Удаление клиента"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT name FROM clients WHERE client_id = %s;', (id,))
    client = cur.fetchone()
    if not client:
        flash('Клиент не найден.', 'error')
        return redirect(url_for('client_list'))
    
    if request.method == 'POST':
        try:
            cur.execute('DELETE FROM clients WHERE client_id = %s;', (id,))
            conn.commit()
            flash(f'Клиент "{client[0]}" удалён.', 'success')
            return redirect(url_for('client_list'))
        except Exception as e:
            flash(f'Ошибка при удалении: {e}', 'error')
    
    cur.close()
    conn.close()
    return render_template('clients/delete.html', client_name=client[0])

# === CRUD: Справочник складов ===
@app.route('/warehouses')
def warehouse_list():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT warehouse_id, name, address, capacity_m3 FROM warehouses ORDER BY name;')
    warehouses = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('warehouses/list.html', warehouses=warehouses)

@app.route('/warehouses/create', methods=('GET', 'POST'))
def warehouse_create():
    if request.method == 'POST':
        name = request.form['name'].strip()
        address = request.form.get('address', '').strip()
        capacity = request.form.get('capacity_m3')
        if not name:
            flash('Название склада обязательно!', 'error')
        else:
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute(
                    'INSERT INTO warehouses (name, address, capacity_m3) VALUES (%s, %s, %s);',
                    (name, address, capacity or None)
                )
                conn.commit()
                flash('Склад добавлен!', 'success')
                return redirect(url_for('warehouse_list'))
            except Exception as e:
                flash(f'Ошибка: {e}', 'error')
    return render_template('warehouses/create.html')

@app.route('/warehouses/edit/<int:id>', methods=('GET', 'POST'))
def warehouse_edit(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT warehouse_id, name, address, capacity_m3 FROM warehouses WHERE warehouse_id = %s;', (id,))
    wh = cur.fetchone()
    if not wh:
        flash('Склад не найден.', 'error')
        return redirect(url_for('warehouse_list'))
    
    if request.method == 'POST':
        name = request.form['name'].strip()
        address = request.form.get('address', '').strip()
        capacity = request.form.get('capacity_m3')
        if not name:
            flash('Название обязательно!', 'error')
        else:
            cur.execute(
                'UPDATE warehouses SET name = %s, address = %s, capacity_m3 = %s WHERE warehouse_id = %s;',
                (name, address, capacity or None, id)
            )
            conn.commit()
            flash('Склад обновлён!', 'success')
            return redirect(url_for('warehouse_list'))
    
    cur.close()
    conn.close()
    return render_template('warehouses/edit.html', warehouse=wh)

@app.route('/warehouses/delete/<int:id>', methods=('GET', 'POST'))
def warehouse_delete(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT name FROM warehouses WHERE warehouse_id = %s;', (id,))
    wh = cur.fetchone()
    if not wh:
        flash('Склад не найден.', 'error')
        return redirect(url_for('warehouse_list'))
    
    if request.method == 'POST':
        cur.execute('DELETE FROM warehouses WHERE warehouse_id = %s;', (id,))
        conn.commit()
        flash(f'Склад "{wh[0]}" удалён.', 'success')
        return redirect(url_for('warehouse_list'))
    
    cur.close()
    conn.close()
    return render_template('warehouses/delete.html', name=wh[0])
    
    
# === CRUD: Справочник зон ===
@app.route('/zones')
def zone_list():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT z.zone_id, z.name, z.type, w.name AS warehouse
        FROM zones z
        JOIN warehouses w ON z.warehouse_id = w.warehouse_id
        ORDER BY w.name, z.name;
    ''')
    zones = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('zones/list.html', zones=zones)

@app.route('/zones/create', methods=('GET', 'POST'))
def zone_create():
    # Получаем список складов для выпадающего списка
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT warehouse_id, name FROM warehouses ORDER BY name;')
    warehouses = cur.fetchall()
    
    if request.method == 'POST':
        name = request.form['name'].strip()
        wh_id = request.form.get('warehouse_id')
        zone_type = request.form.get('type')
        max_cap = request.form.get('max_capacity')
        if not (name and wh_id and zone_type):
            flash('Все поля обязательны!', 'error')
        else:
            try:
                cur.execute(
                    'INSERT INTO zones (warehouse_id, name, type, max_capacity) VALUES (%s, %s, %s, %s);',
                    (wh_id, name, zone_type, max_cap or None)
                )
                conn.commit()
                flash('Зона добавлена!', 'success')
                return redirect(url_for('zone_list'))
            except Exception as e:
                flash(f'Ошибка: {e}', 'error')
    
    cur.close()
    conn.close()
    return render_template('zones/create.html', warehouses=warehouses)

@app.route('/zones/edit/<int:id>', methods=('GET', 'POST'))
def zone_edit(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT warehouse_id, name, type, max_capacity FROM zones WHERE zone_id = %s;', (id,))
    zone = cur.fetchone()
    cur.execute('SELECT warehouse_id, name FROM warehouses ORDER BY name;')
    warehouses = cur.fetchall()
    
    if not zone:
        flash('Зона не найдена.', 'error')
        return redirect(url_for('zone_list'))
    
    if request.method == 'POST':
        name = request.form['name'].strip()
        wh_id = request.form.get('warehouse_id')
        zone_type = request.form.get('type')
        max_cap = request.form.get('max_capacity')
        if not (name and wh_id and zone_type):
            flash('Все поля обязательны!', 'error')
        else:
            cur.execute(
                'UPDATE zones SET warehouse_id = %s, name = %s, type = %s, max_capacity = %s WHERE zone_id = %s;',
                (wh_id, name, zone_type, max_cap or None, id)
            )
            conn.commit()
            flash('Зона обновлена!', 'success')
            return redirect(url_for('zone_list'))
    
    cur.close()
    conn.close()
    return render_template('zones/edit.html', zone=zone, warehouses=warehouses)

@app.route('/zones/delete/<int:id>', methods=('GET', 'POST'))
def zone_delete(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT name FROM zones WHERE zone_id = %s;', (id,))
    zone = cur.fetchone()
    if not zone:
        flash('Зона не найдена.', 'error')
        return redirect(url_for('zone_list'))
    
    if request.method == 'POST':
        cur.execute('DELETE FROM zones WHERE zone_id = %s;', (id,))
        conn.commit()
        flash(f'Зона "{zone[0]}" удалена.', 'success')
        return redirect(url_for('zone_list'))
    
    cur.close()
    conn.close()
    return render_template('zones/delete.html', name=zone[0])
    
    
# === CRUD: Справочник товаров ===
@app.route('/products')
def product_list():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT p.sku_id, p.name, c.name AS client,
               p.weight_per_unit,
               p.units_per_box,
               p.units_per_pallet
        FROM products p
        JOIN clients c ON p.client_id = c.client_id
        ORDER BY c.name, p.name;
    ''')
    products = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('products/list.html', products=products)

@app.route('/products/create', methods=('GET', 'POST'))
def product_create():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT client_id, name FROM clients ORDER BY name;')
    clients = cur.fetchall()

    if request.method == 'POST':
        client_id = request.form.get('client_id')
        name = request.form.get('name', '').strip()
        weight = request.form.get('weight_per_unit')
        box = request.form.get('units_per_box')
        pallet = request.form.get('units_per_pallet')

        if not all([client_id, name, weight, box, pallet]):
            flash('Все поля обязательны!', 'error')
        else:
            try:
                cur.execute('''
                    INSERT INTO products (client_id, name, weight_per_unit, units_per_box, units_per_pallet)
                    VALUES (%s, %s, %s, %s, %s);
                ''', (client_id, name, weight, box, pallet))
                conn.commit()
                flash('Товар добавлен!', 'success')
                return redirect(url_for('product_list'))
            except Exception as e:
                flash(f'Ошибка: {e}', 'error')

    cur.close()
    conn.close()
    return render_template('products/create.html', clients=clients)

@app.route('/products/edit/<int:id>', methods=('GET', 'POST'))
def product_edit(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT sku_id, client_id, name, weight_per_unit, units_per_box, units_per_pallet
        FROM products WHERE sku_id = %s;
    ''', (id,))
    product = cur.fetchone()
    if not product:
        flash('Товар не найден.', 'error')
        return redirect(url_for('product_list'))

    cur.execute('SELECT client_id, name FROM clients ORDER BY name;')
    clients = cur.fetchall()

    if request.method == 'POST':
        client_id = request.form.get('client_id')
        name = request.form.get('name', '').strip()
        weight = request.form.get('weight_per_unit')
        box = request.form.get('units_per_box')
        pallet = request.form.get('units_per_pallet')

        if not all([client_id, name, weight, box, pallet]):
            flash('Все поля обязательны!', 'error')
        else:
            try:
                cur.execute('''
                    UPDATE products
                    SET client_id = %s, name = %s, weight_per_unit = %s,
                        units_per_box = %s, units_per_pallet = %s
                    WHERE sku_id = %s;
                ''', (client_id, name, weight, box, pallet, id))
                conn.commit()
                flash('Товар обновлён!', 'success')
                return redirect(url_for('product_list'))
            except Exception as e:
                flash(f'Ошибка: {e}', 'error')

    cur.close()
    conn.close()
    return render_template('products/edit.html', product=product, clients=clients)

@app.route('/products/delete/<int:id>', methods=('GET', 'POST'))
def product_delete(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT name FROM products WHERE sku_id = %s;', (id,))
    prod = cur.fetchone()
    if not prod:
        flash('Товар не найден.', 'error')
        return redirect(url_for('product_list'))
    
    if request.method == 'POST':
        cur.execute('DELETE FROM products WHERE sku_id = %s;', (id,))
        conn.commit()
        flash(f'Товар "{prod[0]}" удалён.', 'success')
        return redirect(url_for('product_list'))
    
    cur.close()
    conn.close()
    return render_template('products/delete.html', name=prod[0])
    
    
# === CRUD: Справочник ресурсов ===
@app.route('/resources')
def resource_list():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT 
            r.resource_id,
            r.name,
            CASE 
                WHEN r.type = 'staff' THEN 'Персонал'
                WHEN r.type = 'equipment' THEN 'Техника'
                ELSE r.type
            END AS type_ru,
            r.subtype,
            z.name AS zone
        FROM resources r
        LEFT JOIN zones z ON r.zone_id = z.zone_id
        ORDER BY r.type, r.subtype, r.name;
    ''')
    resources = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('resources/list.html', resources=resources)

@app.route('/resources/create', methods=('GET', 'POST'))
def resource_create():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        r_type = request.form.get('type')
        subtype = request.form.get('subtype')
        zone_id = request.form.get('zone_id') or None

        if not (name and r_type and subtype):
            flash('Все поля обязательны!', 'error')
        else:
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute('''
                    INSERT INTO resources (type, subtype, name, zone_id)
                    VALUES (%s, %s, %s, %s);
                ''', (r_type, subtype, name, zone_id))
                conn.commit()
                flash('Ресурс добавлен!', 'success')
                return redirect(url_for('resource_list'))
            except Exception as e:
                flash(f'Ошибка: {e}', 'error')
    
    # Загружаем зоны для выпадающего списка
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT zone_id, name FROM zones ORDER BY name;')
    zones = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('resources/create.html', zones=zones)
    
    
    
@app.route('/resources/edit/<int:id>', methods=('GET', 'POST'))
def resource_edit(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT resource_id, type, subtype, name, zone_id FROM resources WHERE resource_id = %s;', (id,))
    res = cur.fetchone()
    if not res:
        flash('Ресурс не найден.', 'error')
        return redirect(url_for('resource_list'))

    cur.execute('SELECT zone_id, name FROM zones ORDER BY name;')
    zones = cur.fetchall()
    cur.close()
    conn.close()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        r_type = request.form.get('type')
        subtype = request.form.get('subtype')
        zone_id = request.form.get('zone_id') or None

        if not (name and r_type and subtype):
            flash('Все поля обязательны!', 'error')
        else:
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute('''
                    UPDATE resources
                    SET type = %s, subtype = %s, name = %s, zone_id = %s
                    WHERE resource_id = %s;
                ''', (r_type, subtype, name, zone_id, id))
                conn.commit()
                flash('Ресурс обновлён!', 'success')
                return redirect(url_for('resource_list'))
            except Exception as e:
                flash(f'Ошибка: {e}', 'error')

    return render_template('resources/edit.html', resource=res, zones=zones)
    
    
    
    

@app.route('/resources/delete/<int:id>', methods=('GET', 'POST'))
def resource_delete(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT name FROM resources WHERE resource_id = %s;', (id,))
    res = cur.fetchone()
    if not res:
        flash('Ресурс не найден.', 'error')
        return redirect(url_for('resource_list'))
    
    if request.method == 'POST':
        cur.execute('DELETE FROM resources WHERE resource_id = %s;', (id,))
        conn.commit()
        flash(f'Ресурс "{res[0]}" удалён.', 'success')
        return redirect(url_for('resource_list'))
    
    cur.close()
    conn.close()
    return render_template('resources/delete.html', name=res[0])
    
    
# === Планы поступления ===


@app.route('/inbound')
def inbound_list():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT d.doc_id, c.name AS client, d.doc_number, d.doc_date, d.validated
        FROM inbound_documents d
        JOIN clients c ON d.client_id = c.client_id
        ORDER BY d.doc_date DESC, d.doc_id DESC;
    ''')
    docs = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('inbound/list.html', docs=docs)
    
    
@app.route('/inbound/create', methods=('GET', 'POST'))
def inbound_create():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT client_id, name FROM clients ORDER BY name;')
    clients = cur.fetchall()
    if request.method == 'POST':
        client_id = request.form.get('client_id')
        doc_number = request.form.get('doc_number', '').strip()
        doc_date = request.form.get('doc_date')
        skus = request.form.getlist('sku_id')
        qtys = request.form.getlist('qty')
        units = request.form.getlist('unit_type')


        if not (client_id and doc_number and doc_date):
            flash('Заполните реквизиты документа!', 'error')
        else:
            # === Проверка: есть ли хотя бы одна валидная позиция ===
            valid_positions = 0
            for i in range(len(skus)):
                sku_id = skus[i]
                qty_str = qtys[i] if i < len(qtys) else ''
                unit = units[i] if i < len(units) else 'шт'
                # Пропускаем пустые или некорректные значения
                if not sku_id or not qty_str.strip():
                    continue
                try:
                    qty_val = float(qty_str)
                    if qty_val > 0:
                        valid_positions += 1
                except ValueError:
                    continue  # игнорируем некорректные числа

            if valid_positions == 0:
                flash('Добавьте хотя бы одну позицию с количеством > 0!', 'error')
            else:
                try:
                    cur.execute('''
                        INSERT INTO inbound_documents (client_id, doc_number, doc_date)
                        VALUES (%s, %s, %s) RETURNING doc_id;
                    ''', (client_id, doc_number, doc_date))
                    doc_id = cur.fetchone()[0]
                    for i in range(len(skus)):
                        sku_id = skus[i]
                        qty_str = qtys[i] if i < len(qtys) else ''
                        unit = units[i] if i < len(units) else 'шт'
                        # Пропускаем пустые или некорректные значения
                        if not sku_id or not qty_str.strip():
                            continue
                        try:
                            qty_val = float(qty_str)
                            if qty_val > 0:
                                cur.execute('''
                                    INSERT INTO inbound_items (doc_id, sku_id, qty, unit_type)
                                    VALUES (%s, %s, %s, %s);
                                ''', (doc_id, sku_id, qty_val, unit))
                        except ValueError:
                            continue  # игнорируем некорректные числа
                    conn.commit()
                    flash('Поступление добавлено!', 'success')
                    return redirect(url_for('inbound_list'))
                except Exception as e:
                    conn.rollback()
                    flash(f'Ошибка: {e}', 'error')
    # Для GET: загружаем товары первого клиента (или пусто)
    products = []
    if clients:
        cur.execute('SELECT sku_id, client_id, name FROM products WHERE client_id = %s ORDER BY name;', (clients[0][0],))
        products = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('inbound/create.html', clients=clients, products=products)


    
@app.route('/inbound/edit/<int:doc_id>', methods=('GET', 'POST'))
def inbound_edit(doc_id):
    conn = get_db_connection()
    cur = conn.cursor()

    # Проверяем, существует ли документ
    cur.execute('SELECT doc_id, client_id, doc_number, doc_date FROM inbound_documents WHERE doc_id = %s;', (doc_id,))
    doc = cur.fetchone()
    if not doc:
        flash('Документ не найден.', 'error')
        return redirect(url_for('inbound_list'))

    cur.execute('SELECT client_id, name FROM clients ORDER BY name;')
    clients = cur.fetchall()
    cur.execute('SELECT sku_id, name FROM products WHERE client_id = %s ORDER BY name;', (doc[1],))
    products = cur.fetchall()
    cur.execute('SELECT item_id, sku_id, qty, unit_type FROM inbound_items WHERE doc_id = %s;', (doc_id,))
    items = cur.fetchall()

    if request.method == 'POST':
        client_id = request.form.get('client_id')
        doc_number = request.form.get('doc_number', '').strip()
        doc_date = request.form.get('doc_date')
        skus = request.form.getlist('sku_id')
        qtys = request.form.getlist('qty')
        units = request.form.getlist('unit_type')

        if not (client_id and doc_number and doc_date):
            flash('Заполните реквизиты документа!', 'error')
        elif not any(qty.strip() and float(qty) > 0 for qty in qtys if qty):
            flash('Добавьте хотя бы одну позицию!', 'error')
        else:
            try:
                # Обновляем заголовок
                cur.execute('''
                    UPDATE inbound_documents
                    SET client_id = %s, doc_number = %s, doc_date = %s
                    WHERE doc_id = %s;
                ''', (client_id, doc_number, doc_date, doc_id))

                # Удаляем старые позиции
                cur.execute('DELETE FROM inbound_items WHERE doc_id = %s;', (doc_id,))

                # Добавляем новые
                for i in range(len(skus)):
                    sku_id = skus[i]
                    qty = qtys[i]
                    unit = units[i]
                    if sku_id and qty and float(qty) > 0:
                        cur.execute('''
                            INSERT INTO inbound_items (doc_id, sku_id, qty, unit_type)
                            VALUES (%s, %s, %s, %s);
                        ''', (doc_id, sku_id, qty, unit))

                conn.commit()
                flash('Поступление обновлено!', 'success')
                return redirect(url_for('inbound_list'))
            except Exception as e:
                conn.rollback()
                flash(f'Ошибка: {e}', 'error')

    cur.close()
    conn.close()
    return render_template('inbound/edit.html', doc=doc, clients=clients, products=products, items=items)
    
    
@app.route('/inbound/delete/<int:doc_id>', methods=('GET', 'POST'))
def inbound_delete(doc_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT doc_number FROM inbound_documents WHERE doc_id = %s;', (doc_id,))
    doc = cur.fetchone()
    if not doc:
        flash('Документ не найден.', 'error')
        return redirect(url_for('inbound_list'))

    if request.method == 'POST':
        try:
            # Каскадное удаление через FOREIGN KEY (ON DELETE CASCADE)
            cur.execute('DELETE FROM inbound_documents WHERE doc_id = %s;', (doc_id,))
            conn.commit()
            flash(f'Документ {doc[0]} удалён.', 'success')
            return redirect(url_for('inbound_list'))
        except Exception as e:
            flash(f'Ошибка при удалении: {e}', 'error')

    cur.close()
    conn.close()
    return render_template('inbound/delete.html', doc_number=doc[0])


@app.route('/inbound/validate/<int:doc_id>', methods=('GET', 'POST'))
def inbound_validate(doc_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT d.doc_number, c.name
        FROM inbound_documents d
        JOIN clients c ON d.client_id = c.client_id
        WHERE d.doc_id = %s;
    ''', (doc_id,))
    doc = cur.fetchone()
    if not doc:
        flash('Документ не найден.', 'error')
        return redirect(url_for('inbound_list'))

    if request.method == 'POST':
        try:
            cur.execute('UPDATE inbound_documents SET validated = TRUE WHERE doc_id = %s;', (doc_id,))
            conn.commit()
            flash(f'Поступление {doc[0]} подтверждено!', 'success')
            return redirect(url_for('inbound_list'))
        except Exception as e:
            flash(f'Ошибка: {e}', 'error')

    cur.close()
    conn.close()
    return render_template('inbound/validate.html', doc_number=doc[0], client_name=doc[1])



    
    
# === Планы отгрузки ===
@app.route('/plans/outbound')
def outbound_list():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT op.plan_id, c.name AS client, p.name AS product, op.date, op.qty, op.validated
        FROM outbound_plan op
        JOIN clients c ON op.client_id = c.client_id
        JOIN products p ON op.sku_id = p.sku_id
        ORDER BY op.date DESC, op.plan_id;
    ''')
    plans = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('plans/outbound_list.html', plans=plans)

@app.route('/plans/outbound/create', methods=('GET', 'POST'))
def outbound_create():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT client_id, name FROM clients ORDER BY name;')
    clients = cur.fetchall()
    cur.execute('SELECT sku_id, name, client_id FROM products ORDER BY name;')
    products = cur.fetchall()
    
    if request.method == 'POST':
        client_id = request.form.get('client_id')
        sku_id = request.form.get('sku_id')
        date = request.form.get('date')
        qty = request.form.get('qty')
        if not (client_id and sku_id and date and qty):
            flash('Все поля обязательны!', 'error')
        else:
            try:
                cur.execute(
                    'INSERT INTO outbound_plan (client_id, sku_id, date, qty, validated) VALUES (%s, %s, %s, %s, %s);',
                    (client_id, sku_id, date, qty, False)
                )
                conn.commit()
                flash('План отгрузки добавлен!', 'success')
                return redirect(url_for('outbound_list'))
            except Exception as e:
                flash(f'Ошибка: {e}', 'error')
    
    cur.close()
    conn.close()
    return render_template('plans/outbound_create.html', clients=clients, products=products)


# === Расчёт потребности (A9) — обновлённая версия ===
@app.route('/requirements', methods=('GET', 'POST'))
def requirements_view():
    """Просмотр рассчитанной потребности в ресурсах с фильтром по дате"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Запрос к обновлённому VIEW
        query = '''
            SELECT 
                r.date,
                r.doc_number,
                z.name AS zone_name,
                r.resource_type,  -- уже содержит подтип на русском (Приёмщик, Ричтрак и т.д.)
                ROUND(r.required_units, 2) AS required_units
            FROM v_resource_requirements r
            JOIN zones z ON r.zone_id = z.zone_id
        '''
        params = []

        # Фильтрация по дате
        if start_date and end_date:
            query += ' WHERE r.date BETWEEN %s AND %s'
            params = [start_date, end_date]
        elif start_date:
            query += ' WHERE r.date >= %s'
            params = [start_date]
        elif end_date:
            query += ' WHERE r.date <= %s'
            params = [end_date]

        query += ' ORDER BY r.date, r.doc_number, z.name;'

        cur.execute(query, params)
        requirements = cur.fetchall()
        cur.close()
        conn.close()

        return render_template(
            'requirements/list.html',
            requirements=requirements,
            start_date=start_date,
            end_date=end_date
        )
    except Exception as e:
        flash(f'Ошибка при загрузке потребности: {e}', 'error')
        return redirect(url_for('index'))

# === CRUD: Справочник нормативов (A5) ===
@app.route('/norms')
def norm_list():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT 
            n.norm_id,
            c.name AS client_name,
            p.name AS sku_name,
            n.operation_type,
            n.zone_type,
            n.resource_subtype,  -- ✅ Используем subtype
            n.unit_type,
            n.norm_value
        FROM norms n
        JOIN clients c ON n.client_id = c.client_id
        JOIN products p ON n.sku_id = p.sku_id
        ORDER BY c.name, p.name;
    ''')
    norms = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('norms/list.html', norms=norms)



@app.route('/norms/create', methods=('GET', 'POST'))
def norm_create():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT client_id, name FROM clients ORDER BY name;')
    clients = cur.fetchall()
    cur.execute('SELECT sku_id, name FROM products ORDER BY name;')
    products = cur.fetchall()
    if request.method == 'POST':
        client_id = request.form.get('client_id')
        sku_id = request.form.get('sku_id')
        op_type = request.form.get('operation_type')
        zone_type = request.form.get('zone_type')
        resource_subtype = request.form.get('resource_subtype')  # ✅ Правильное имя
        unit_type = request.form.get('unit_type')
        norm_val = request.form.get('norm_value')

        if not all([client_id, sku_id, op_type, zone_type, resource_subtype, unit_type, norm_val]):
            flash('Все поля обязательны!', 'error')
        else:
            try:
                cur.execute('''
                    INSERT INTO norms (
                        client_id, sku_id, operation_type, zone_type,
                        resource_subtype, unit_type, norm_value
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s);
                ''', (client_id, sku_id, op_type, zone_type, resource_subtype, unit_type, norm_val))
                conn.commit()
                flash('Норматив добавлен!', 'success')
                return redirect(url_for('norm_list'))
            except psycopg2.errors.UniqueViolation:
                conn.rollback()
                flash('Такой норматив уже существует!', 'error')
            except Exception as e:
                conn.rollback()
                flash(f'Ошибка: {e}', 'error')

    cur.close()
    conn.close()
    return render_template('norms/create.html', clients=clients, products=products)
    
    
@app.route('/norms/edit/<int:id>', methods=('GET', 'POST'))
def norm_edit(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT norm_id, client_id, sku_id, operation_type, zone_type,
               resource_subtype, unit_type, norm_value
        FROM norms WHERE norm_id = %s;
    ''', (id,))
    norm = cur.fetchone()
    if not norm:
        flash('Норматив не найден.', 'error')
        return redirect(url_for('norm_list'))

    cur.execute('SELECT client_id, name FROM clients ORDER BY name;')
    clients = cur.fetchall()
    cur.execute('SELECT sku_id, name FROM products ORDER BY name;')
    products = cur.fetchall()

    if request.method == 'POST':
        client_id = request.form.get('client_id')
        sku_id = request.form.get('sku_id')
        op_type = request.form.get('operation_type')
        zone_type = request.form.get('zone_type')
        resource_subtype = request.form.get('resource_subtype')
        unit_type = request.form.get('unit_type')
        norm_val = request.form.get('norm_value')

        if not all([client_id, sku_id, op_type, zone_type, resource_subtype, unit_type, norm_val]):
            flash('Все поля обязательны!', 'error')
        else:
            try:
                cur.execute('''
                    UPDATE norms
                    SET client_id = %s, sku_id = %s, operation_type = %s, zone_type = %s,
                        resource_subtype = %s, unit_type = %s, norm_value = %s
                    WHERE norm_id = %s;
                ''', (client_id, sku_id, op_type, zone_type, resource_subtype, unit_type, norm_val, id))
                conn.commit()
                flash('Норматив обновлён!', 'success')
                return redirect(url_for('norm_list'))
            except psycopg2.errors.UniqueViolation:
                conn.rollback()
                flash('Такой норматив уже существует!', 'error')
            except Exception as e:
                conn.rollback()
                flash(f'Ошибка: {e}', 'error')

    cur.close()
    conn.close()
    return render_template('norms/edit.html', norm=norm, clients=clients, products=products)

@app.route('/norms/delete/<int:id>', methods=('GET', 'POST'))
def norm_delete(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT operation_type, zone_type, resource_subtype FROM norms WHERE norm_id = %s;', (id,))
    norm = cur.fetchone()
    if not norm:
        flash('Норматив не найден.', 'error')
        return redirect(url_for('norm_list'))
    
    if request.method == 'POST':
        cur.execute('DELETE FROM norms WHERE norm_id = %s;', (id,))
        conn.commit()
        flash('Норматив удалён.', 'success')
        return redirect(url_for('norm_list'))
    
    cur.close()
    conn.close()
    op_desc = f"{norm[0]} / {norm[1]} / {norm[2]}"
    return render_template('norms/delete.html', description=op_desc)
    
@app.route('/capacities')
def capacity_list():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT 
            ac.capacity_id,
            r.name AS resource_name,
            r.subtype,  
            ac.date,
            ac.available_hours
        FROM available_capacities ac
        JOIN resources r ON ac.resource_id = r.resource_id
        ORDER BY ac.date DESC, r.name;
    ''')
    capacities = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('capacities/list.html', capacities=capacities)
    
@app.route('/capacities/create', methods=('GET', 'POST'))
def capacity_create():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT resource_id, name, subtype FROM resources ORDER BY name;')
    resources = cur.fetchall()

    if request.method == 'POST':
        resource_id = request.form.get('resource_id')
        date = request.form.get('date')
        hours = request.form.get('available_hours')

        if not (resource_id and date and hours):
            flash('Все поля обязательны!', 'error')
        else:
            try:
                cur.execute('''
                    INSERT INTO available_capacities (resource_id, date, available_hours)
                    VALUES (%s, %s, %s);
                ''', (resource_id, date, hours))
                conn.commit()
                flash('Доступность добавлена!', 'success')
                return redirect(url_for('capacity_list'))
            except psycopg2.errors.UniqueViolation:
                flash('Для этого ресурса на эту дату уже задана доступность!', 'error')
            except Exception as e:
                flash(f'Ошибка: {e}', 'error')

    cur.close()
    conn.close()
    return render_template('capacities/create.html', resources=resources)
    
    
@app.route('/capacities/edit/<int:id>', methods=('GET', 'POST'))
def capacity_edit(id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Получаем текущую запись
    cur.execute('''
        SELECT capacity_id, resource_id, date, available_hours
        FROM available_capacities
        WHERE capacity_id = %s;
    ''', (id,))
    capacity = cur.fetchone()
    if not capacity:
        flash('Запись не найдена.', 'error')
        return redirect(url_for('capacity_list'))

    # Загружаем список ресурсов для выпадающего списка
    cur.execute('SELECT resource_id, name, subtype FROM resources ORDER BY name;')
    resources = cur.fetchall()

    if request.method == 'POST':
        resource_id = request.form.get('resource_id')
        date = request.form.get('date')
        hours = request.form.get('available_hours')

        if not (resource_id and date and hours):
            flash('Все поля обязательны!', 'error')
        else:
            try:
                cur.execute('''
                    UPDATE available_capacities
                    SET resource_id = %s, date = %s, available_hours = %s
                    WHERE capacity_id = %s;
                ''', (resource_id, date, hours, id))
                conn.commit()
                flash('Доступность обновлена!', 'success')
                return redirect(url_for('capacity_list'))
            except psycopg2.errors.UniqueViolation:
                flash('Для этого ресурса на эту дату уже задана доступность!', 'error')
            except Exception as e:
                flash(f'Ошибка: {e}', 'error')

    cur.close()
    conn.close()
    return render_template('capacities/edit.html', capacity=capacity, resources=resources)
    
    
    
@app.route('/capacities/delete/<int:id>', methods=('GET', 'POST'))
def capacity_delete(id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Получаем данные для подтверждения
    cur.execute('''
        SELECT ac.date, r.name AS resource_name
        FROM available_capacities ac
        JOIN resources r ON ac.resource_id = r.resource_id
        WHERE ac.capacity_id = %s;
    ''', (id,))
    capacity = cur.fetchone()
    if not capacity:
        flash('Запись не найдена.', 'error')
        return redirect(url_for('capacity_list'))

    if request.method == 'POST':
        try:
            cur.execute('DELETE FROM available_capacities WHERE capacity_id = %s;', (id,))
            conn.commit()
            flash('Запись удалена.', 'success')
            return redirect(url_for('capacity_list'))
        except Exception as e:
            flash(f'Ошибка при удалении: {e}', 'error')

    cur.close()
    conn.close()
    return render_template('capacities/delete.html', date=capacity[0], resource_name=capacity[1])


@app.route('/balance', methods=('GET', 'POST'))
def balance_view():
    """Просмотр баланса мощностей (A12) с фильтром по дате"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Базовый запрос
        query = '''
            SELECT 
                date,
                zone_name,
                resource_subtype,
                ROUND(required_hours, 2) AS required_hours,
                ROUND(available_hours, 2) AS available_hours,
                ROUND(balance, 2) AS balance
            FROM v_capacity_balance
        '''
        params = []

        # Фильтр по дате
        if start_date and end_date:
            query += ' WHERE date BETWEEN %s AND %s'
            params = [start_date, end_date]
        elif start_date:
            query += ' WHERE date >= %s'
            params = [start_date]
        elif end_date:
            query += ' WHERE date <= %s'
            params = [end_date]

        query += ' ORDER BY date, zone_name, resource_subtype;'

        cur.execute(query, params)
        balance_data = cur.fetchall()
        cur.close()
        conn.close()
        return render_template(
            'balance/list.html',
            balance_data=balance_data,
            start_date=start_date,
            end_date=end_date
        )
    except Exception as e:
        flash(f'Ошибка при загрузке баланса: {e}', 'error')
        return redirect(url_for('index'))


# === Страница выбора отчёта ===
@app.route('/reports')
def report_select():
    return render_template('reports/select.html')

# === Формирование отчёта ===
@app.route('/reports/generate', methods=['POST'])
def generate_report():
    report_type = request.form.get('report_type')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    action = request.form.get('action')  # 'preview', 'pdf', 'csv'

    if not (report_type and start_date and end_date):
        flash('Выберите тип отчёта и укажите период!', 'error')
        return redirect(url_for('report_select'))

    # Заголовок отчёта
    titles = {
        'balance': 'Отчёт по балансу мощностей',
        'load': 'Отчёт нагрузка за период',
        'requirement': 'Отчёт потребность за период',
        'capacity': 'Отчёт доступность за период'
    }
    title = titles.get(report_type, 'Отчёт')

    # Получение данных
    data = []
    headers = []
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        if report_type == 'balance':
            cur.execute('''
                SELECT date, zone_name, resource_subtype, required_hours, available_hours, balance
                FROM v_capacity_balance
                WHERE date BETWEEN %s AND %s
                ORDER BY date, zone_name, resource_subtype;
            ''', (start_date, end_date))
            raw_data = cur.fetchall()
            # Округляем числовые поля до 2 знаков
            data = [(row[0], row[1], row[2], round(row[3], 2), round(row[4], 2), round(row[5], 2)) for row in raw_data]
            headers = ['Дата', 'Зона', 'Ресурс', 'Требуемо, ч', 'Доступно, ч', 'Баланс, ч']

        elif report_type == 'load':
            cur.execute('''
                SELECT d.doc_date, d.doc_number, c.name, p.name, i.qty, i.unit_type
                FROM inbound_documents d
                JOIN inbound_items i ON d.doc_id = i.doc_id
                JOIN clients c ON d.client_id = c.client_id
                JOIN products p ON i.sku_id = p.sku_id
                WHERE d.doc_date BETWEEN %s AND %s AND d.validated = TRUE
                ORDER BY d.doc_date, d.doc_number;
            ''', (start_date, end_date))
            raw_data = cur.fetchall()
            # qty — может быть дробным
            data = [(row[0], row[1], row[2], row[3], round(row[4], 2), row[5]) for row in raw_data]
            headers = ['Дата', 'Документ', 'Клиент', 'Товар', 'Кол-во', 'Ед.изм.']

        elif report_type == 'requirement':
            cur.execute('''
                SELECT date, doc_number, zone_name, resource_type, required_units
                FROM v_resource_requirements r
                JOIN zones z ON r.zone_id = z.zone_id
                WHERE date BETWEEN %s AND %s
                ORDER BY date, doc_number;
            ''', (start_date, end_date))
            raw_data = cur.fetchall()
            data = [(row[0], row[1], row[2], row[3], round(row[4], 2)) for row in raw_data]
            headers = ['Дата', 'Документ', 'Зона', 'Ресурс', 'Требуемо, ед.']

        elif report_type == 'capacity':
            cur.execute('''
                SELECT ac.date, r.name, r.subtype, ac.available_hours
                FROM available_capacities ac
                JOIN resources r ON ac.resource_id = r.resource_id
                WHERE ac.date BETWEEN %s AND %s
                ORDER BY ac.date, r.name;
            ''', (start_date, end_date))
            raw_data = cur.fetchall()
            data = [(row[0], row[1], row[2], round(row[3], 2)) for row in raw_data]
            headers = ['Дата', 'Ресурс', 'Подтип', 'Доступно, ч']

        cur.close()
        conn.close()

    except Exception as e:
        flash(f'Ошибка при формировании отчёта: {e}', 'error')
        return redirect(url_for('report_select'))


"""
    # === Обработка действий ===
    if action == 'pdf':
        html = render_template('reports/pdf_template.html', title=title, headers=headers, data=data, start_date=start_date, end_date=end_date)
        options = {
            'page-size': 'A4',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': "UTF-8",
            'no-outline': None
        }
        pdf = pdfkit.from_string(html, False, options=options)
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=report_{report_type}_{start_date}_{end_date}.pdf'
        return response

    elif action == 'csv':
        # Генерация CSV
        output = StringIO()
        writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(headers)
        for row in data:
            writer.writerow(row)
        output.seek(0)
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv; charset=utf-8-sig'
        response.headers['Content-Disposition'] = f'attachment; filename=report_{report_type}_{start_date}_{end_date}.csv'
        return response

    else:  # preview
        return render_template('reports/preview.html', title=title, headers=headers, data=data, start_date=start_date, end_date=end_date)

"""

def generate_recommendations_from_balance(balance_data):
    """
    Генерирует рекомендации на основе баланса.
    balance_data: список кортежей (date, zone_name, resource_subtype, required, available, balance)
    """
    recommendations = []
    for row in balance_data:
        date, zone, resource, required, available, balance = row
        balance = float(balance)
        rec_text = ""

        # Определяем тип ресурса
        is_staff = any(t in resource for t in ['Приёмщик', 'Грузчик', 'Контролёр'])
        is_equipment = any(t in resource for t in ['Ричтрак', 'Паллетоперевозчик', 'Тележка'])

        if balance < -2.0:  # Сильный дефицит
            if is_staff:
                rec_text = "Назначить дополнительного сотрудника на смену"
            elif is_equipment:
                rec_text = "Рассмотреть аренду дополнительной техники на пиковые дни"
        elif balance < 0:   # Умеренный дефицит
            if is_staff:
                rec_text = "Привлечь сверхурочные часы для текущего сотрудника"
            elif is_equipment:
                rec_text = "Проверить график ТО — возможно, техника простаивает"
        elif balance > 3.0: # Избыток
            rec_text = "Переназначить ресурс на другую зону или сократить смену"
        else:
            continue  # в балансе — не показываем

        recommendations.append({
            'date': date,
            'zone': zone,
            'resource': resource,
            'balance': round(balance, 2),
            'recommendation': rec_text,
            'type': 'Дефицит' if balance < 0 else 'Избыток'
        })
    return recommendations
    
    
@app.route('/recommendations', methods=['GET', 'POST'])
def recommendations_view():
    """Просмотр рекомендаций по корректировке ресурсов (A14) с фильтром и экспортами"""
    # Определяем источник дат: POST (при отправке формы) или GET (при первом заходе)
    if request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        action = request.form.get('action')
    else:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        action = None

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Запрос к балансу с фильтром по дате
        query = '''
            SELECT 
                date, zone_name, resource_subtype,
                required_hours, available_hours, balance
            FROM v_capacity_balance
            WHERE balance != 0
        '''
        params = []

        if start_date and end_date:
            query += ' AND date BETWEEN %s AND %s'
            params = [start_date, end_date]
        elif start_date:
            query += ' AND date >= %s'
            params = [start_date]
        elif end_date:
            query += ' AND date <= %s'
            params = [end_date]

        query += ' ORDER BY date, zone_name, resource_subtype;'
        cur.execute(query, params)
        balance_data = cur.fetchall()
        cur.close()
        conn.close()

        # Генерация рекомендаций
        recommendations = generate_recommendations_from_balance(balance_data)
"""
        # === Обработка экспорта ===
        if action == 'pdf':
            html = render_template(
                'recommendations/pdf_template.html',
                recommendations=recommendations,
                start_date=start_date,
                end_date=end_date
            )
            options = {
                'page-size': 'A4',
                'margin-top': '0.75in',
                'margin-right': '0.75in',
                'margin-bottom': '0.75in',
                'margin-left': '0.75in',
                'encoding': "UTF-8",
                'no-outline': None
            }
            pdf = pdfkit.from_string(html, False, options=options)
            response = make_response(pdf)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'inline; filename=recommendations_{start_date or "all"}_{end_date or "all"}.pdf'
            return response

        elif action == 'csv':
            output = StringIO()
            writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(['Дата', 'Зона', 'Ресурс', 'Баланс, ч', 'Тип', 'Рекомендация'])
            for rec in recommendations:
                writer.writerow([
                    rec['date'],
                    rec['zone'],
                    rec['resource'],
                    rec['balance'],
                    rec['type'],
                    rec['recommendation']
                ])
            output.seek(0)
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'text/csv; charset=utf-8-sig'
            response.headers['Content-Disposition'] = f'attachment; filename=recommendations_{start_date or "all"}_{end_date or "all"}.csv'
            return response

        else:
            # Показываем форму с результатами (в list.html)
            return render_template(
                'recommendations/list.html',  # ← ВАЖНО: list.html, а не preview.html
                recommendations=recommendations,
                start_date=start_date,
                end_date=end_date
            )
"""
    except Exception as e:
        flash(f'Ошибка при загрузке рекомендаций: {e}', 'error')
        return redirect(url_for('index'))

# === Запуск приложения ===
if __name__ == '__main__':
    print("🚀 Запуск приложения 'Информационная система оценки мощностей склада'...")
    print("Откройте в браузере: http://localhost:5001")
    app.run(debug=True, host='127.0.0.1', port=5001)