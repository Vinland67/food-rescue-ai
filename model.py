import pandas as pd


def _safe_float(value, default):
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value, default):
    try:
        if pd.isna(value):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


class FoodRescueAI:
    def __init__(self):
        pass

    def process_inventory(self, df):
        data_records = []
        for _, row in df.iterrows():
            item_name = str(row.get('name', 'N/A'))
            if item_name.lower() == 'nan':
                item_name = 'N/A'

            category = str(row.get('category', 'Ümumi'))
            if category.lower() == 'nan':
                category = 'Ümumi'

            daily_sales = _safe_float(row.get('daily_sales'), 5.0)
            temperature = _safe_float(row.get('temperature'), 18.0)
            days_to_expire = _safe_int(row.get('days_to_expire'), 5)
            stock = _safe_int(row.get('stock'), 50)
            price = _safe_float(row.get('price'), 10.0)
            cost_price = _safe_float(row.get('cost_price'), price * 0.7)

            projected_demand = daily_sales * days_to_expire
            temp_risk = temperature > 22 and days_to_expire <= 5

            if days_to_expire <= 1 or temp_risk:
                action_label = "Donation / Write-off"
                risk_status = "Critical"
                badge_color = "red"
                filter_group = "critical"
                discount_percentage = 100
                optimal_price = 0.0
            elif days_to_expire <= 9 or projected_demand < stock:
                risk_status = "At Risk"
                badge_color = "amber"
                filter_group = "discount"
                target_price = round(cost_price * 1.15, 2)
                if target_price >= price:
                    target_price = round(price * 0.9, 2)
                optimal_price = target_price
                discount_percentage = int(round((1 - optimal_price / price) * 100)) if price > 0 else 15
                action_label = f"Smart Discount (-{discount_percentage}%)"
            else:
                discount_percentage = 0
                optimal_price = price
                action_label = "Optimal / Normal"
                risk_status = "Secure"
                badge_color = "emerald"
                filter_group = "normal"

            if risk_status == "Critical":
                risk_level = "High"
            elif risk_status == "At Risk":
                risk_level = "Medium"
            else:
                risk_level = "Low"

            if filter_group == "critical":
                carbon_saved = round(stock * 0.18, 2)
            elif filter_group == "discount":
                carbon_saved = round(stock * 0.10, 2)
            else:
                carbon_saved = 0.0

            data_records.append({
                "product": item_name,
                "category": category,
                "daily_sales": daily_sales,
                "temperature": temperature,
                "days_to_expire": days_to_expire,
                "stock": stock,
                "original_price": price,
                "cost_price": cost_price,
                "discount_pct": discount_percentage,
                "recommended_price": optimal_price,
                "action": action_label,
                "status": risk_status,
                "risk_level": risk_level,
                "carbon_saved": carbon_saved,
                "ml_forecast_days": days_to_expire,
                "color": badge_color,
                "filter_type": filter_group
            })
        return data_records