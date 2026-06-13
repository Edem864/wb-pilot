"""
Модуль расчёта юнит-экономики SKU для Wildberries.
Все проценты передаются как доли (например, 0.15 = 15%).
"""

from dataclasses import dataclass


@dataclass
class SKU:
    name: str
    cost: float                # себестоимость
    packaging: float           # упаковка
    logistics_forward: float   # прямая логистика (фикс. сумма)
    logistics_backward: float  # обратная логистика (фикс. сумма)
    buyout_rate: float         # процент выкупа (0.0 - 1.0)
    commission: float          # комиссия WB (0.0 - 1.0)
    spp: float                 # СПП (0.0 - 1.0)
    acquiring: float            # эквайринг (0.0 - 1.0)
    tax_rate: float              # налог (0.0 - 1.0)
    opex_rate: float             # операционные расходы (0.0 - 1.0)
    min_margin: float            # минимальная маржа (0.0 - 1.0)
    min_profit: float            # минимальная прибыль, руб
    target_profit: float         # целевая прибыль, руб


def _k_factor(sku: SKU) -> float:
    """Доля от 'цены со скидкой', которая остаётся после
    комиссии, эквайринга, налога и опекс."""
    return (1 - sku.commission) * (1 - sku.acquiring) - sku.tax_rate - sku.opex_rate


def _fixed_costs(sku: SKU) -> float:
    """Фиксированные затраты на единицу товара."""
    return (
        sku.cost
        + sku.packaging
        + sku.logistics_forward
        + sku.logistics_backward * (1 - sku.buyout_rate)
    )


def calculate_profit(sku: SKU, price: float) -> float:
    """Прибыль с одной продажи при заданной цене."""
    revenue = price * (1 - sku.spp)
    k = _k_factor(sku)
    return revenue * k - _fixed_costs(sku)


def calculate_margin(sku: SKU, price: float) -> float:
    """Маржа (доля прибыли от 'цены со скидкой')."""
    revenue = price * (1 - sku.spp)
    if revenue == 0:
        return 0.0
    return calculate_profit(sku, price) / revenue


def find_price_for_profit(sku: SKU, profit_target: float) -> float:
    """Находит цену, при которой прибыль равна profit_target."""
    k = _k_factor(sku)
    fixed = _fixed_costs(sku)
    if k <= 0 or sku.spp >= 1:
        raise ValueError("Некорректные параметры: k <= 0 или СПП >= 100%")
    return (profit_target + fixed) / ((1 - sku.spp) * k)


def find_min_price(sku: SKU) -> float:
    """Минимальная допустимая цена (по минимальной прибыли)."""
    return find_price_for_profit(sku, sku.min_profit)


def find_target_price(sku: SKU) -> float:
    """Цена, обеспечивающая целевую прибыль."""
    return find_price_for_profit(sku, sku.target_profit)


def simulate(sku: SKU, price: float) -> dict:
    """Полная симуляция по цене: возвращает все ключевые показатели."""
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
