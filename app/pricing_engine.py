"""
Модуль расчёта юнит-экономики SKU для Wildberries.
Все проценты передаются как доли (например, 0.15 = 15%).
"""

from dataclasses import dataclass


@dataclass
class SKU:
    name: str
    cost: float
    packaging: float
    logistics_forward: float
    logistics_backward: float
    buyout_rate: float
    commission: float
    spp: float
    acquiring: float
    tax_rate: float
    opex_rate: float
    min_margin: float
    min_profit: float
    target_profit: float


def _k_factor(sku: SKU) -> float:
    return (1 - sku.commission) * (1 - sku.acquiring) - sku.tax_rate - sku.opex_rate


def _fixed_costs(sku: SKU) -> float:
    return (
        sku.cost
        + sku.packaging
        + sku.logistics_forward
        + sku.logistics_backward * (1 - sku.buyout_rate)
    )


def calculate_profit(sku: SKU, price: float) -> float:
    revenue = price * (1 - sku.spp)
    k = _k_factor(sku)
    return revenue * k - _fixed_costs(sku)


def calculate_margin(sku: SKU, price: float) -> float:
    revenue = price * (1 - sku.spp)
    if revenue == 0:
        return 0.0
    return calculate_profit(sku, price) / revenue


def find_price_for_profit(sku: SKU, profit_target: float) -> float:
    k = _k_factor(sku)
    fixed = _fixed_costs(sku)
    if k <= 0 or sku.spp >= 1:
        raise ValueError("Некорректные параметры: k <= 0 или СПП >= 100%")
    return (profit_target + fixed) / ((1 - sku.spp) * k)


def find_min_price(sku: SKU) -> float:
    return find_price_for_profit(sku, sku.min_profit)


def find_target_price(sku: SKU) -> float:
    return find_price_for_profit(sku, sku.target_profit)


def simulate(sku: SKU, price: float) -> dict:
    profit = calculate_profit(sku, price)
    margin = calculate_margin(sku, price)
    revenue = price * (1 - sku.spp)
    return {
        "price": round(price, 2),
        "revenue_after_spp": round(revenue, 2),
        "profit": round(profit, 2),
        "margin_pct": round(margin * 100, 2),
        "meets_min_profit": profit >= sku.min_profit,
        "meets_min_margin": margin >= sku.min_margin,
    }


def propose_price(sku: SKU, current_price: float, max_change: float = 0.05) -> float:
    if calculate_profit(sku, current_price) < sku.min_profit or calculate_margin(sku, current_price) < sku.min_margin:
        desired = find_min_price(sku)
    else:
        desired = find_target_price(sku)

    max_price = current_price * (1 + max_change)
    min_price_step = current_price * (1 - max_change)

    proposed = max(min(desired, max_price), min_price_step)
    proposed = max(proposed, find_min_price(sku))

    return round(proposed, 2)
