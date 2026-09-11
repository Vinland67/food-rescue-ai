# model.py - Smart Business Logic Engine for Pricing & Waste
import pandas as pd

class FoodRescueAI:
    def __init__(self):
        pass

    def analyze_dataframe(self, df):
        results = []
        for _, row in df.iterrows():
            name = str(row.get('name', 'Naməlum'))
            daily_sales = float(row.get('daily_sales', 5))
            temperature = float(row.get('temperature', 18.0))
            days_to_expire = int(row.get('days_to_expire', 5))
            stock = int(row.get('stock', 50))
            price = float(row.get('price', 10.0))
            cost_price = float(row.get('cost_price', price * 0.7))

            projected_demand = daily_sales * days_to_expire
            temp_risk = temperature > 22 and days_to_expire <= 5

            # BİZNES MƏNTİQİ:
            # 1. QIRMIZI ZONA (Kritik / İanə): Ya tam ianə edilir, ya da maya dəyərinin çox az üzərinə qoyulub dərhal elənməlidir.
            if days_to_expire <= 1 or temp_risk:
                action = "🎁 Təmənnasız İanəyə Ayır"
                status = "Kritik Risk"
                color = "red"
                filter_type = "critical"
                discount_pct = 100
                recommended_price = 0.0  # İanə olduğu üçün 0 və ya simvolik

            # 2. SARI ZONA (İsraf Riski / Endirim): Maya dəyərindən yuxarı, orijinal qiymətdən aşağı (məsələn, maya üzərinə 15% qoyuruq ki, zərər etməyək, amma tez satılsın)
            elif days_to_expire <= 9 or projected_demand < stock:
                status = "İsraf Riski"
                color = "amber"
                filter_type = "discount"
                
                # Maya dəyərinin üzərinə təhlükəsiz 15% marja əlavə edirik ki, supermarket zərər çəkməsin
                target_price = round(cost_price * 1.15, 2)
                
                # Əgər hədəf qiymət orijinal qiymətdən yüksək alınarsa, orijinal qiymətdə saxlayırıq
                if target_price >= price:
                    target_price = round(price * 0.9, 2) # ən azı 10% endirim olsun
                
                recommended_price = target_price
                # Endirim faizini orijinal qiymətə əsasən hesablayırıq
                if price > 0:
                    discount_pct = int(round((1 - recommended_price / price) * 100))
                else:
                    discount_pct = 15
                
                action = f"⚠️ Ağıllı Endirim ({discount_pct}% - Maya Qorunur)"

            # 3. YAŞIL ZONA (Normal): Heç bir endirim yoxdur, orijinal qiymət qalır
            else:
                discount_pct = 0
                recommended_price = price
                action = "✅ Normal Satış"
                status = "Təhlükəsiz"
                color = "emerald"
                filter_type = "normal"

            results.append({
                "product": name,
                "daily_sales": daily_sales,
                "temperature": temperature,
                "days_to_expire": days_to_expire,
                "stock": stock,
                "original_price": price,
                "cost_price": cost_price,
                "discount_pct": discount_pct,
                "recommended_price": recommended_price,
                "action": action,
                "status": status,
                "color": color,
                "filter_type": filter_type
            })
        return results