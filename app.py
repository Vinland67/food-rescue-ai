# app.py - Flask Server with Enhanced Financial Metrics & Analytics
from flask import Flask, render_template, request, redirect, url_for, jsonify
import pandas as pd
from model import FoodRescueAI

app = Flask(__name__)
ai_engine = FoodRescueAI()

analyzed_inventory = []

@app.route('/')
def index():
    filter_category = request.args.get('filter', 'all')
    
    if filter_category == 'critical':
        filtered_inventory = [item for item in analyzed_inventory if item['filter_type'] == 'critical']
    elif filter_category == 'discount':
        filtered_inventory = [item for item in analyzed_inventory if item['filter_type'] == 'discount']
    elif filter_category == 'normal':
        filtered_inventory = [item for item in analyzed_inventory if item['filter_type'] == 'normal']
    else:
        filtered_inventory = analyzed_inventory

    # Yeni Maliyyə Göstəriciləri
    total_stock = sum([item['stock'] for item in analyzed_inventory]) if analyzed_inventory else 0
    saved_food = round(total_stock * 0.015, 2)
    
    # 1. Ümumi malların maya dəyəri (stok * maya dəyəri)
    total_cost_value = sum([item['stock'] * item['cost_price'] for item in analyzed_inventory]) if analyzed_inventory else 0
    
    # 2. Bütün malların satışından əldə olunan potensial ümumi dəyər (stok * tövsiyə olunan/satış qiyməti)
    total_sales_value = sum([item['stock'] * item['recommended_price'] for item in analyzed_inventory]) if analyzed_inventory else 0
    
    # 3. Potensial ümumi mənfəət (Ümumi Satış - Maya Dəyəri)
    total_potential_profit = total_sales_value - total_cost_value
    
    # 4. Zərərdən qurtarılan dəyər
    saved_money = sum([item['stock'] * (item['original_price'] - item['recommended_price']) for item in analyzed_inventory if item['discount_pct'] > 0]) if analyzed_inventory else 0

    # Əlavə Analitika: Tez satılanlar vs İsraf olunan riskli mallar
    wasted_risk_items = [item for item in analyzed_inventory if item['filter_type'] in ['critical', 'discount']]
    safe_sold_items = [item for item in analyzed_inventory if item['filter_type'] == 'normal']

    return render_template('index.html', 
                           inventory=filtered_inventory, 
                           current_filter=filter_category,
                           saved_food=saved_food, 
                           saved_money=round(saved_money, 2),
                           total_cost_value=round(total_cost_value, 2),
                           total_sales_value=round(total_sales_value, 2),
                           total_potential_profit=round(total_potential_profit, 2),
                           wasted_risk_items=wasted_risk_items,
                           safe_sold_items=safe_sold_items)

@app.route('/api/upload_excel', methods=['POST'])
def upload_excel():
    if 'file' not in request.files:
        return redirect(url_for('index'))
    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('index'))
    
    if file:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
        
        global analyzed_inventory
        analyzed_inventory = ai_engine.analyze_dataframe(df)
        
    return redirect(url_for('index'))

@app.route('/api/clear', methods=['POST'])
def clear_data():
    global analyzed_inventory
    analyzed_inventory = []
    return redirect(url_for('index'))

@app.route('/api/optimize', methods=['POST'])
def optimize_all():
    if not analyzed_inventory:
        return jsonify({
            "status": "success",
            "saved_food": "0.0 Ton",
            "saved_money": "0 AZN",
            "message": "Yüklənmiş məlumat yoxdur!"
        })
    total_stock = sum([item['stock'] for item in analyzed_inventory])
    saved_food = round(total_stock * 0.015, 2)
    saved_money = sum([item['stock'] * (item['original_price'] - item['recommended_price']) for item in analyzed_inventory if item['discount_pct'] > 0])
    
    return jsonify({
        "status": "success",
        "saved_food": f"{saved_food} Ton",
        "saved_money": f"{round(saved_money, 2)} AZN",
        "message": "Bütün maliyyə və qiymət optimizasiyaları uğurla tamamlandı!"
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)