import psycopg2
import psycopg2.extras
from pricing_engine import SKU, simulate, propose_price
from wb_api import get_prices

conn = psycopg2.connect(
    host="localhost",
    dbname="wbpilot",
    user="wbpilot_user",
    password="wbpilot_pass_2026",
)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur.execute("SELECT * FROM skus")
rows = cur.fetchall()
financial_data = {str(row["nm_id"]): row for row in rows}
cur.close()
conn.close()

status, data = get_prices(limit=100)
if status != 200:
    print("Ошибка получения данных от WB:", data)
    raise SystemExit

goods = data["data"]["listGoods"]

print(f"{'Артикул':<12}{'Название':<12}{'Цена':>8}{'Прибыль':>10}{'Маржа%':>8}{'НовЦена':>10}  Рекомендация")
print("-" * 90)

for item in goods:
    nm_id = str(item["nmID"])
    if nm_id not in financial_data:
        continue

    fin = financial_data[nm_id]
    current_price = item["sizes"][0]["discountedPrice"]

    sku = SKU(
        name=fin["name"],
        cost=float(fin["cost"]),
        packaging=float(fin["packaging"]),
        logistics_forward=float(fin["logistics_forward"]),
        logistics_backward=float(fin["logistics_backward"]),
        buyout_rate=float(fin["buyout_rate"]),
        commission=float(fin["commission"]),
        spp=0,
        acquiring=float(fin["acquiring"]),
        tax_rate=float(fin["tax_rate"]),
        opex_rate=float(fin["opex_rate"]),
        min_margin=float(fin["min_margin"]),
        min_profit=float(fin["min_profit"]),
        target_profit=float(fin["target_profit"]),
    )

    result = simulate(sku, current_price)
    new_price = propose_price(sku, current_price)

    if new_price > current_price:
        rec = f"ПОВЫСИТЬ до {new_price:.0f}р"
    elif new_price < current_price:
        rec = f"СНИЗИТЬ до {new_price:.0f}р"
    else:
        rec = "Цена в норме"

    print(f"{nm_id:<12}{fin['name']:<12}{current_price:>8}{result['profit']:>10}{result['margin_pct']:>8}{new_price:>10.0f}  {rec}")
