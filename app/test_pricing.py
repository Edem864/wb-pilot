from pricing_engine import SKU, simulate, find_min_price, find_target_price

sku = SKU(
    name="Артикул 541695632",
    cost=500,
    packaging=15,
    logistics_forward=60,
    logistics_backward=40,
    buyout_rate=0.7,
    commission=0.17,
    spp=0.20,
    acquiring=0.015,
    tax_rate=0.06,
    opex_rate=0.05,
    min_margin=0.15,
    min_profit=100,
    target_profit=200,
)

current_price = 1200

print("=== Текущая цена ===")
print(simulate(sku, current_price))

print("\n=== Минимальная цена (по min_profit) ===")
print(round(find_min_price(sku), 2))

print("\n=== Целевая цена (по target_profit) ===")
print(round(find_target_price(sku), 2))

print("\n=== Цена +4% ===")
print(simulate(sku, current_price * 1.04))
