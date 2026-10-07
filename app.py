from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import io
import sqlite3
from datetime import datetime
from model import FoodRescueAI

app = Flask(__name__)
ai_engine = FoodRescueAI()

DB_PATH = 'inventory_history.db'


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            total_skus INTEGER,
            high_risk INTEGER,
            saved_carbon REAL
        )
    ''')
    conn.commit()
    conn.close()


init_db()


def save_snapshot(inventory):
    if not inventory:
        return
    total_skus = len(inventory)
    high_risk = sum(1 for i in inventory if i.get('risk_level') == 'High')
    saved_carbon = sum(i.get('carbon_saved', 0.0) for i in inventory)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO snapshots (timestamp, total_skus, high_risk, saved_carbon) VALUES (?, ?, ?, ?)',
        (timestamp, total_skus, high_risk, saved_carbon)
    )
    conn.commit()
    conn.close()


def get_history_trend():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT timestamp, high_risk FROM snapshots ORDER BY id DESC LIMIT 5')
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return [0, 0, 0, 0, 0]
    values = [r[1] for r in reversed(rows)]
    if len(values) < 5:
        values = [None] * (5 - len(values)) + values
    return values


database_state = {
    "inventory": []
}


@app.route('/')
def index():
    active_filter = request.args.get('filter', 'all')
    raw_inventory = database_state["inventory"]

    if active_filter == 'critical':
        filtered_data = [i for i in raw_inventory if i['filter_type'] == 'critical']
    elif active_filter == 'discount':
        filtered_data = [i for i in raw_inventory if i['filter_type'] == 'discount']
    elif active_filter == 'normal':
        filtered_data = [i for i in raw_inventory if i['filter_type'] == 'normal']
    else:
        filtered_data = raw_inventory

    total_stock = sum([i['stock'] for i in raw_inventory]) if raw_inventory else 0
    saved_food_tons = round(total_stock * 0.015, 2)
    total_cost = sum([i['stock'] * i['cost_price'] for i in raw_inventory]) if raw_inventory else 0
    total_revenue = sum([i['stock'] * i['recommended_price'] for i in raw_inventory]) if raw_inventory else 0
    net_profit = total_revenue - total_cost
    recovered_capital = sum(
        [i['stock'] * (i['original_price'] - i['recommended_price']) for i in raw_inventory if i['discount_pct'] > 0]
    ) if raw_inventory else 0

    risk_items = [i for i in raw_inventory if i['filter_type'] in ['critical', 'discount']]
    secure_items = [i for i in raw_inventory if i['filter_type'] == 'normal']

    return render_template('index.html',
                           inventory=filtered_data,
                           current_filter=active_filter,
                           saved_food=saved_food_tons,
                           saved_money=round(recovered_capital, 2),
                           total_cost_value=round(total_cost, 2),
                           total_sales_value=round(total_revenue, 2),
                           total_potential_profit=round(net_profit, 2),
                           wasted_risk_items=risk_items,
                           safe_sold_items=secure_items)


@app.route('/powerbi')
def powerbi_analytics():
    raw_inventory = database_state["inventory"]

    if not raw_inventory:
        metrics = {
            "total_skus": 0, "total_cost": 0.0, "total_revenue": 0.0,
            "high_risk_count": 0, "medium_risk_count": 0, "low_risk_count": 0,
            "efficiency": "0.0%", "secure_pct": 0.0, "trend_data": get_history_trend()
        }
        return render_template('powerbi.html', inventory=[], metrics=metrics, categories_json={})

    total_skus = len(raw_inventory)
    total_cost = sum([i['stock'] * i['cost_price'] for i in raw_inventory])
    total_revenue = sum([i['stock'] * i['recommended_price'] for i in raw_inventory])

    high_risk_count = 0
    medium_risk_count = 0
    low_risk_count = 0
    secure_count = 0
    category_counts = {}

    for item in raw_inventory:
        risk = item.get('risk_level', 'Low')
        cat = item.get('category', 'General Stock')

        category_counts[cat] = category_counts.get(cat, 0) + 1

        if risk == 'High':
            high_risk_count += 1
        elif risk == 'Medium':
            medium_risk_count += 1
        else:
            low_risk_count += 1
            if item.get('filter_type') == 'normal':
                secure_count += 1

    secure_pct = round((secure_count / total_skus) * 100, 1) if total_skus > 0 else 0.0
    efficiency_val = round(90.0 + (secure_pct * 0.1), 1)
    trend_vals = get_history_trend()

    metrics = {
        "total_skus": total_skus,
        "total_cost": round(total_cost, 2),
        "total_revenue": round(total_revenue, 2),
        "high_risk_count": high_risk_count,
        "medium_risk_count": medium_risk_count,
        "low_risk_count": low_risk_count,
        "efficiency": f"{efficiency_val}%",
        "secure_pct": secure_pct,
        "trend_data": trend_vals
    }

    return render_template('powerbi.html', inventory=raw_inventory, metrics=metrics, categories_json=category_counts)


@app.route('/api/optimize', methods=['POST'])
def api_optimize():
    try:
        raw_inventory = database_state["inventory"]
        if not raw_inventory:
            return jsonify({"status": "error", "message": "No inventory loaded to optimize."}), 400

        changed = 0
        for item in raw_inventory:
            if item['filter_type'] == 'discount':
                item['recommended_price'] = round(item['original_price'] * 0.5, 2)
                item['action'] = "Deep Smart Discount (-50%)"
                changed += 1

        save_snapshot(raw_inventory)
        return jsonify({
            "status": "success",
            "message": f"Pipeline executed. {changed} items re-priced.",
            "saved_food": f"{changed} items optimized",
            "saved_money": "recalculated"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/load_demo', methods=['POST'])
def load_demo():
    try:
        mock_df = pd.DataFrame([
            {'name': 'Organic Fresh Milk 1L', 'category': 'Dairy Products', 'daily_sales': 16, 'temperature': 4.2, 'days_to_expire': 1, 'stock': 80, 'price': 2.80, 'cost_price': 1.95},
            {'name': 'Artisan Sourdough Bread', 'category': 'Bakery & Grains', 'daily_sales': 35, 'temperature': 20.0, 'days_to_expire': 0, 'stock': 50, 'price': 1.20, 'cost_price': 0.70},
            {'name': 'Free-Range Chicken Breast', 'category': 'Meat & Poultry', 'daily_sales': 10, 'temperature': 24.5, 'days_to_expire': 2, 'stock': 30, 'price': 10.50, 'cost_price': 7.50},
            {'name': 'Greek Yogurt 500g', 'category': 'Dairy Products', 'daily_sales': 22, 'temperature': 3.8, 'days_to_expire': 5, 'stock': 65, 'price': 2.10, 'cost_price': 1.40},
            {'name': 'Energy Drink 250ml', 'category': 'Beverages', 'daily_sales': 40, 'temperature': 12.0, 'days_to_expire': 25, 'stock': 120, 'price': 2.50, 'cost_price': 1.50},
            {'name': 'Natural Orange Juice 1L', 'category': 'Beverages', 'daily_sales': 18, 'temperature': 14.0, 'days_to_expire': 4, 'stock': 45, 'price': 4.50, 'cost_price': 3.00},
            {'name': 'Farm Eggs Grade A', 'category': 'Dairy Products', 'daily_sales': 15, 'temperature': 18.0, 'days_to_expire': 12, 'stock': 90, 'price': 5.80, 'cost_price': 4.30},
            {'name': 'Smoked Beef Salami', 'category': 'Meat & Poultry', 'daily_sales': 7, 'temperature': 16.5, 'days_to_expire': 3, 'stock': 25, 'price': 14.00, 'cost_price': 9.80},
            {'name': 'Aged Gouda Cheese', 'category': 'Dairy Products', 'daily_sales': 5, 'temperature': 19.0, 'days_to_expire': 15, 'stock': 40, 'price': 16.50, 'cost_price': 11.00}
        ])
        processed = ai_engine.process_inventory(mock_df)
        database_state["inventory"] = processed
        save_snapshot(processed)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/upload_excel', methods=['POST'])
def upload_excel():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file uploaded"}), 400

    uploaded_file = request.files['file']
    if uploaded_file.filename == '':
        return jsonify({"status": "error", "message": "Empty filename"}), 400

    allowed_ext = ('.csv', '.xlsx', '.xls')
    if not uploaded_file.filename.lower().endswith(allowed_ext):
        return jsonify({"status": "error", "message": "Only .csv, .xlsx, .xls files are supported"}), 400

    try:
        if uploaded_file.filename.lower().endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        processed = ai_engine.process_inventory(df)
        database_state["inventory"] = processed
        save_snapshot(processed)
        return jsonify({"status": "success", "message": "File processed successfully"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/clear', methods=['POST'])
def clear_data():
    database_state["inventory"] = []
    return jsonify({"status": "success"})


@app.route('/api/export_report', methods=['GET'])
def export_report():
    raw_inventory = database_state["inventory"]
    if not raw_inventory:
        df = pd.DataFrame([{'Message': 'No active inventory data loaded.'}])
    else:
        export_rows = []
        for i in raw_inventory:
            export_rows.append({
                'Product': i['product'],
                'Category': i['category'],
                'Stock': i['stock'],
                'Days To Expire': i['days_to_expire'],
                'Original Price': i['original_price'],
                'Cost Price': i['cost_price'],
                'Recommended Price': i['recommended_price'],
                'Discount %': i['discount_pct'],
                'Action': i['action'],
                'Risk Level': i['risk_level'],
                'Carbon Saved (kg)': i['carbon_saved'],
            })
        df = pd.DataFrame(export_rows)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='FoodRescue_Analytics_Report')
    output.seek(0)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='FoodRescue_AI_Analytics_Report.xlsx'
    )


if __name__ == '__main__':
    app.run(debug=True, port=5000)