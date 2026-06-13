import json
from pricing_engine import SKU, simulate, find_min_price, find_target_price, propose_price
from wb_api import get_prices

with open("skus_example.json", "r", encoding="utf-8") as f:
    financial_data = json.load(f)

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
        cost=fin["cost"],
        packaging=fin["packaging"],
        logistics_forward=fin["logistics_forward"],
        logistics_backward=fin["logistics_backward"],
        buyout_rate=fin["buyout_rate"],
        commission=fin["commission"],
        spp=0,
        acquiring=fin["acquiring"],
        tax_rate=fin["tax_rate"],
        opex_rate=fin["opex_rate"],
        min_margin=fin["min_margin"],
        min_profit=fin["min_profit"],
        target_profit=fin["target_profit"],
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
