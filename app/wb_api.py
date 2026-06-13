import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("WB_API_TOKEN")
BASE_URL = "https://discounts-prices-api.wildberries.ru"


def check_connection():
    """Проверка подключения к API Wildberries."""
    headers = {"Authorization": TOKEN}
    response = requests.get(f"{BASE_URL}/ping", headers=headers)
    return response.status_code, response.json()


def get_prices(limit=10, offset=0):
    """Получить список товаров с текущими ценами."""
    headers = {"Authorization": TOKEN}
    params = {"limit": limit, "offset": offset}
    response = requests.get(
        f"{BASE_URL}/api/v2/list/goods/filter", headers=headers, params=params
    )
    return response.status_code, response.json()


if __name__ == "__main__":
    print("=== Проверка подключения ===")
    status, data = check_connection()
    print("Статус:", status)
    print(data)

    print("\n=== Список товаров (первые 10) ===")
    status, data = get_prices(limit=10)
    print("Статус:", status)
    print(data)
