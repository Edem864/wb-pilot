import time
from flask import Flask, render_template_string, request, redirect
import psycopg2
import psycopg2.extras
from wb_api import get_prices

app = Flask(__name__)

DB_CONFIG = dict(host="localhost", dbname="wbpilot", user="wbpilot_user", password="wbpilot_pass_2026")


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


TEMPLATE_LIST = """
<!doctype html>
<html>
<head><meta charset="utf-8"><title>WB Pilot - Товары</title></head>
<body style="font-family: sans-serif; max-width: 900px; margin: 40px auto;">
<h1>Товары</h1>
<p>
  <a href="/add">+ Добавить товар вручную</a> &nbsp;|&nbsp;
  <a href="/sync">Синхронизировать с Wildberries</a>
</p>
<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse;">
<tr>
<th>Артикул</th><th>Название</th><th>Себестоимость</th><th>Мин.маржа</th><th>Мин.прибыль</th><th>Цель прибыль</th><th></th>
</tr>
{% for s in skus %}
<tr>
<td>{{ s.nm_id }}</td><td>{{ s.name }}</td><td>{{ s.cost }}</td><td>{{ s.min_margin }}</td><td>{{ s.min_profit }}</td><td>{{ s.target_profit }}</td>
<td><a href="/add?nm_id={{ s.nm_id }}">Редактировать</a></td>
</tr>
{% endfor %}
</table>
</body>
</html>
"""

TEMPLATE_FORM = """
<!doctype html>
<html>
<head><meta charset="utf-8"><title>Добавить товар</title></head>
<body style="font-family: sans-serif; max-width: 500px; margin: 40px auto;">
<h1>Добавить / обновить товар</h1>
<form method="post">
{% for field, label in fields %}
<p><label>{{ label }}<br>
<input type="text" name="{{ field }}" value="{{ values.get(field, '') }}" required style="width:100%; box-sizing: border-box; padding:6px;" {% if field == 'nm_id' and values.get('nm_id') %}readonly{% endif %}>
</label></p>
{% endfor %}
<button type="submit" style="padding:8px 20px;">Сохранить</button>
</form>
<p><a href="/">К списку товаров</a></p>
</body>
</html>
"""

FIELDS = [
    ("nm_id", "Артикул (nmID)"),
    ("name", "Название"),
    ("cost", "Себестоимость, руб"),
    ("packaging", "Упаковка, руб"),
    ("logistics_forward", "Логистика прямая, руб"),
    ("logistics_backward", "Логистика обратная, руб"),
    ("buyout_rate", "Процент выкупа (0-1, напр. 0.7)"),
    ("commission", "Комиссия WB (0-1, напр. 0.17)"),
    ("acquiring", "Эквайринг (0-1, напр. 0.015)"),
    ("tax_rate", "Налог (0-1, напр. 0.06)"),
    ("opex_rate", "Операционные расходы (0-1, напр. 0.05)"),
    ("min_margin", "Мин. маржа (0-1, напр. 0.15)"),
    ("min_profit", "Мин. прибыль, руб"),
    ("target_profit", "Целевая прибыль, руб"),
]


@app.route("/")
def index():
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM skus ORDER BY nm_id")
    skus = cur.fetchall()
    cur.close()
    conn.close()
    return render_template_string(TEMPLATE_LIST, skus=skus)


@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        data = {f: request.form[f] for f, _ in FIELDS}
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO skus (nm_id, name, cost, packaging, logistics_forward, logistics_backward,
                buyout_rate, commission, acquiring, tax_rate, opex_rate, min_margin, min_profit, target_profit)
            VALUES (%(nm_id)s, %(name)s, %(cost)s, %(packaging)s, %(logistics_forward)s, %(logistics_backward)s,
                %(buyout_rate)s, %(commission)s, %(acquiring)s, %(tax_rate)s, %(opex_rate)s, %(min_margin)s, %(min_profit)s, %(target_profit)s)
            ON CONFLICT (nm_id) DO UPDATE SET
                name=EXCLUDED.name, cost=EXCLUDED.cost, packaging=EXCLUDED.packaging,
                logistics_forward=EXCLUDED.logistics_forward, logistics_backward=EXCLUDED.logistics_backward,
                buyout_rate=EXCLUDED.buyout_rate, commission=EXCLUDED.commission, acquiring=EXCLUDED.acquiring,
                tax_rate=EXCLUDED.tax_rate, opex_rate=EXCLUDED.opex_rate, min_margin=EXCLUDED.min_margin,
                min_profit=EXCLUDED.min_profit, target_profit=EXCLUDED.target_profit
        """, data)
        conn.commit()
        cur.close()
        conn.close()
        return redirect("/")

    values = {}
    nm_id = request.args.get("nm_id")
    if nm_id:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM skus WHERE nm_id = %s", (nm_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            values = dict(row)
    return render_template_string(TEMPLATE_FORM, fields=FIELDS, values=values)


@app.route("/sync")
def sync():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT nm_id FROM skus")
    existing = {row[0] for row in cur.fetchall()}

    offset = 0
    limit = 100
    while True:
        status, data = get_prices(limit=limit, offset=offset)
        if status == 429:
            time.sleep(6)
            continue
        if status != 200:
            break
        goods = data.get("data", {}).get("listGoods", [])
        if not goods:
            break
        for item in goods:
            nm_id_val = item["nmID"]
            if nm_id_val in existing:
                continue
            name = item.get("vendorCode", str(nm_id_val))
            cur.execute("""
                INSERT INTO skus (nm_id, name, cost, packaging, logistics_forward, logistics_backward,
                    buyout_rate, commission, acquiring, tax_rate, opex_rate, min_margin, min_profit, target_profit)
                VALUES (%s, %s, 0, 0, 0, 0, 0, 0.17, 0.015, 0.06, 0.05, 0.15, 0, 0)
            """, (nm_id_val, name))
            existing.add(nm_id_val)
        conn.commit()
        offset += limit
        time.sleep(6)

    cur.close()
    conn.close()
    return redirect("/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
