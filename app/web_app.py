import time
from flask import Flask, render_template_string, request, redirect
import psycopg2
import psycopg2.extras
from wb_api import get_prices

app = Flask(__name__)
DB_CONFIG = dict(host="localhost", dbname="wbpilot", user="wbpilot_user", password="wbpilot_pass_2026")

def get_conn():
    return psycopg2.connect(**DB_CONFIG)

BASE = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>WB Pilot</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f0f2f5; display: flex; min-height: 100vh; }
.sidebar { width: 220px; background: #1a1a2e; color: #fff; padding: 24px 0; flex-shrink: 0; }
.sidebar h2 { font-size: 20px; font-weight: 700; padding: 0 24px 24px; border-bottom: 1px solid #ffffff22; color: #7c6aff; }
.sidebar a { display: block; padding: 12px 24px; color: #ccc; text-decoration: none; font-size: 14px; }
.sidebar a:hover, .sidebar a.active { background: #ffffff11; color: #fff; }
.main { flex: 1; padding: 32px; }
.page-title { font-size: 24px; font-weight: 700; color: #1a1a2e; margin-bottom: 24px; }
.card { background: #fff; border-radius: 12px; padding: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); margin-bottom: 24px; }
.btn { display: inline-block; padding: 10px 20px; border-radius: 8px; text-decoration: none; font-size: 14px; font-weight: 600; cursor: pointer; border: none; }
.btn-primary { background: #7c6aff; color: #fff; }
.btn-primary:hover { background: #6a58e0; }
.btn-success { background: #22c55e; color: #fff; }
.btn-success:hover { background: #16a34a; }
.btn-sm { padding: 6px 12px; font-size: 13px; }
.btn-bar { display: flex; gap: 12px; margin-bottom: 24px; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
thead tr { background: #f8f8ff; }
th { text-align: left; padding: 12px 16px; color: #666; font-weight: 600; border-bottom: 2px solid #e5e7eb; font-size: 13px; }
td { padding: 12px 16px; border-bottom: 1px solid #f0f0f0; color: #333; }
tr:hover td { background: #fafafa; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 20px; font-size: 12px; font-weight: 600; }
.badge-zero { background: #fee2e2; color: #dc2626; }
.badge-ok { background: #dcfce7; color: #16a34a; }
label { display: block; font-size: 14px; font-weight: 600; color: #444; margin-bottom: 4px; }
.hint { font-size: 12px; color: #999; font-weight: 400; margin-bottom: 4px; display: block; }
input[type=text] { width: 100%; padding: 10px 12px; border: 1px solid #e5e7eb; border-radius: 8px; font-size: 14px; outline: none; }
input[type=text]:focus { border-color: #7c6aff; box-shadow: 0 0 0 3px #7c6aff22; }
input[readonly] { background: #f8f8f8; color: #888; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.form-group { margin-bottom: 0; }
</style>
</head>
<body>
<div class="sidebar">
  <h2>WB Pilot</h2>
  <a href="/" class="{% if page=='товары' %}active{% endif %}">Товары</a>
  <a href="/report" class="{% if page=='отчёт' %}active{% endif %}">Отчёт по ценам</a>
</div>
<div class="main">
{% block content %}{% endblock %}
</div>
</body>
</html>
"""

TMPL_LIST = BASE.replace("{% block content %}{% endblock %}", """
<div class="page-title">Товары</div>
<div class="btn-bar">
  <a href="/add" class="btn btn-primary">+ Добавить товар</a>
  <a href="/sync" class="btn btn-success">Синхронизировать с WB</a>
</div>
<div class="card">
<table>
<thead><tr>
<th>Артикул</th>
<th>Название</th>
<th>Себестоимость, руб</th>
<th>Мин. маржа, %</th>
<th>Мин. прибыль, руб</th>
<th>Цель прибыль, руб</th>
<th>Статус</th>
<th></th>
</tr></thead>
<tbody>
{% for s in skus %}
<tr>
<td>{{ s.nm_id }}</td>
<td>{{ s.name }}</td>
<td>{{ s.cost }} руб</td>
<td>{{ (s.min_margin * 100)|int }} %</td>
<td>{{ s.min_profit }} руб</td>
<td>{{ s.target_profit }} руб</td>
<td>{% if s.cost == 0 %}<span class="badge badge-zero">Нет данных</span>{% else %}<span class="badge badge-ok">Заполнен</span>{% endif %}</td>
<td><a href="/add?nm_id={{ s.nm_id }}" class="btn btn-sm btn-primary">Редактировать</a></td>
</tr>
{% endfor %}
</tbody>
</table>
</div>
""")

TMPL_FORM = BASE.replace("{% block content %}{% endblock %}", """
<div class="page-title">{% if edit %}Редактировать товар{% else %}Добавить товар{% endif %}</div>
<div class="card">
<form method="post">
<div class="form-grid">
{% for field, label, hint in fields %}
<div class="form-group">
<label>{{ label }}<span class="hint">{{ hint }}</span></label>
<input type="text" name="{{ field }}" value="{{ values.get(field, '') }}" required {% if field == 'nm_id' and values.get('nm_id') %}readonly{% endif %}>
</div>
{% endfor %}
</div>
<div style="margin-top: 24px; display: flex; gap: 12px;">
<button type="submit" class="btn btn-primary">Сохранить</button>
<a href="/" class="btn" style="background:#f0f2f5; color:#333;">Отмена</a>
</div>
</form>
</div>
""")

TMPL_REPORT = BASE.replace("{% block content %}{% endblock %}", """
<div class="page-title">Отчёт по ценам</div>
<div class="card">
<table>
<thead><tr>
<th>Артикул</th><th>Название</th><th>Текущая цена, руб</th><th>Прибыль, руб</th><th>Маржа, %</th><th>Новая цена, руб</th><th>Рекомендация</th>
</tr></thead>
<tbody>
{% for r in rows %}
<tr>
<td>{{ r.nm_id }}</td>
<td>{{ r.name }}</td>
<td>{{ r.price }} руб</td>
<td>{{ r.profit }} руб</td>
<td>{{ r.margin }} %</td>
<td><b>{{ r.new_price }} руб</b></td>
<td><span class="badge {% if r.action == 'up' %}badge-ok{% elif r.action == 'down' %}badge-zero{% else %}badge-ok{% endif %}">{{ r.rec }}</span></td>
</tr>
{% endfor %}
</tbody>
</table>
</div>
""")

FIELDS = [
    ("nm_id", "Артикул (nmID)", "Номер артикула Wildberries"),
    ("name", "Название товара", "Любое удобное название"),
    ("cost", "Себестоимость", "В рублях — сколько стоит закупка/производство"),
    ("packaging", "Упаковка", "В рублях — стоимость упаковки"),
    ("logistics_forward", "Логистика прямая", "В рублях — доставка до покупателя"),
    ("logistics_backward", "Логистика обратная", "В рублях — стоимость возврата"),
    ("buyout_rate", "Процент выкупа", "Доля от 1, например 0.7 = 70%"),
    ("commission", "Комиссия WB", "Доля от 1, например 0.17 = 17%"),
    ("acquiring", "Эквайринг", "Доля от 1, например 0.015 = 1.5%"),
    ("tax_rate", "Налог", "Доля от 1, например 0.06 = 6% (УСН)"),
    ("opex_rate", "Операц. расходы", "Доля от 1, например 0.05 = 5%"),
    ("min_margin", "Минимальная маржа", "Доля от 1, например 0.15 = 15%"),
    ("min_profit", "Минимальная прибыль", "В рублях — меньше этой суммы не продавать"),
    ("target_profit", "Целевая прибыль", "В рублях — желаемая прибыль с продажи"),
]

@app.route("/")
def index():
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM skus ORDER BY nm_id")
    skus = cur.fetchall()
    cur.close(); conn.close()
    return render_template_string(TMPL_LIST, skus=skus, page="товары")

@app.route("/add", methods=["GET","POST"])
def add():
    if request.method == "POST":
        data = {f: request.form[f] for f, _, _ in FIELDS}
        conn = get_conn(); cur = conn.cursor()
        cur.execute("""
            INSERT INTO skus (nm_id,name,cost,packaging,logistics_forward,logistics_backward,
                buyout_rate,commission,acquiring,tax_rate,opex_rate,min_margin,min_profit,target_profit)
            VALUES (%(nm_id)s,%(name)s,%(cost)s,%(packaging)s,%(logistics_forward)s,%(logistics_backward)s,
                %(buyout_rate)s,%(commission)s,%(acquiring)s,%(tax_rate)s,%(opex_rate)s,%(min_margin)s,%(min_profit)s,%(target_profit)s)
            ON CONFLICT (nm_id) DO UPDATE SET
                name=EXCLUDED.name,cost=EXCLUDED.cost,packaging=EXCLUDED.packaging,
                logistics_forward=EXCLUDED.logistics_forward,logistics_backward=EXCLUDED.logistics_backward,
                buyout_rate=EXCLUDED.buyout_rate,commission=EXCLUDED.commission,acquiring=EXCLUDED.acquiring,
                tax_rate=EXCLUDED.tax_rate,opex_rate=EXCLUDED.opex_rate,min_margin=EXCLUDED.min_margin,
                min_profit=EXCLUDED.min_profit,target_profit=EXCLUDED.target_profit
        """, data)
        conn.commit(); cur.close(); conn.close()
        return redirect("/")
    values = {}
    nm_id = request.args.get("nm_id")
    if nm_id:
        conn = get_conn(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM skus WHERE nm_id=%s",(nm_id,))
        row = cur.fetchone(); cur.close(); conn.close()
        if row: values = {k: str(v) for k,v in dict(row).items()}
    return render_template_string(TMPL_FORM, fields=FIELDS, values=values, edit=bool(nm_id), page="товары")

@app.route("/sync")
def sync():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT nm_id FROM skus")
    existing = {row[0] for row in cur.fetchall()}
    offset = 0
    while True:
        status, data = get_prices(limit=100, offset=offset)
        if status == 429:
            time.sleep(6); continue
        if status != 200: break
        goods = data.get("data", {}).get("listGoods", [])
        if not goods: break
        for item in goods:
            nm_id_val = item["nmID"]
            if nm_id_val in existing: continue
            name = item.get("vendorCode", str(nm_id_val))
            cur.execute("""
                INSERT INTO skus (nm_id,name,cost,packaging,logistics_forward,logistics_backward,
                    buyout_rate,commission,acquiring,tax_rate,opex_rate,min_margin,min_profit,target_profit)
                VALUES (%s,%s,0,0,0,0,0,0.17,0.015,0.06,0.05,0.15,0,0)
            """, (nm_id_val, name))
            existing.add(nm_id_val)
        conn.commit(); offset += 100; time.sleep(6)
    cur.close(); conn.close()
    return redirect("/")

@app.route("/report")
def report():
    from pricing_engine import SKU, simulate, propose_price
    conn = get_conn(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM skus WHERE cost > 0")
    rows_db = cur.fetchall(); cur.close(); conn.close()
    if not rows_db:
        return render_template_string(TMPL_REPORT, rows=[], page="отчёт")
    status, data = get_prices(limit=100)
    if status != 200:
        return render_template_string(TMPL_REPORT, rows=[], page="отчёт")
    goods = {str(g["nmID"]): g for g in data["data"]["listGoods"]}
    rows = []
    for fin in rows_db:
        nm_id = str(fin["nm_id"])
        if nm_id not in goods: continue
        price = goods[nm_id]["sizes"][0]["discountedPrice"]
        sku = SKU(name=fin["name"],cost=float(fin["cost"]),packaging=float(fin["packaging"]),
            logistics_forward=float(fin["logistics_forward"]),logistics_backward=float(fin["logistics_backward"]),
            buyout_rate=float(fin["buyout_rate"]),commission=float(fin["commission"]),spp=0,
            acquiring=float(fin["acquiring"]),tax_rate=float(fin["tax_rate"]),opex_rate=float(fin["opex_rate"]),
            min_margin=float(fin["min_margin"]),min_profit=float(fin["min_profit"]),target_profit=float(fin["target_profit"]))
        res = simulate(sku, price)
        new_price = propose_price(sku, price)
        action = "up" if new_price > price else ("down" if new_price < price else "ok")
        rec = f"Повысить до {new_price:.0f}р" if action=="up" else (f"Снизить до {new_price:.0f}р" if action=="down" else "В норме")
        rows.append(dict(nm_id=nm_id,name=fin["name"],price=price,profit=res["profit"],
            margin=res["margin_pct"],new_price=new_price,action=action,rec=rec))
    return render_template_string(TMPL_REPORT, rows=rows, page="отчёт")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
