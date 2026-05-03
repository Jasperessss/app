import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, redirect

app = Flask(__name__)
app.secret_key = "event_system_key"

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

RANK_WEIGHT = {"High Priority": 4, "Rinehart": 3, "Young": 2, "Test": 1}

def sort_logic(player):
    # Добавлена проверка на None, чтобы избежать KeyError/TypeError
    score = player.get("score") if player.get("score") is not None else 0
    rank = player.get("rank", "Test")
    return (RANK_WEIGHT.get(rank, 0), score)

@app.route("/")
def index():
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM players")
        players_raw = cur.fetchall()
        
        cur.execute("""
            SELECT p.*, a.present 
            FROM active a 
            JOIN players p ON a.name = p.name
        """)
        active_raw = cur.fetchall()
        cur.close()
    finally:
        conn.close()

    groups = {rank: [] for rank in RANK_WEIGHT.keys()}
    for p in sorted(players_raw, key=sort_logic, reverse=True):
        rank = p["rank"] if p["rank"] in groups else "Test"
        groups[rank].append(p)

    active_sorted = sorted(active_raw, key=sort_logic, reverse=True)

    return render_template(
        "index.html",
        players_grouped=groups,
        active=active_sorted,
        role_class=lambda r: {"High Priority": "hp", "Rinehart": "rinehart", "Young": "young", "Test": "test"}.get(r, "test")
    )

@app.route("/score", methods=["POST"])
def score():
    name = request.form.get("name")
    mode = request.form.get("mode")
    try:
        points = int(request.form.get("points", 0))
    except ValueError:
        points = 0

    if points > 0:
        conn = get_db()
        try:
            cur = conn.cursor()
            op = "+" if mode == "add" else "-"
            # Безопасное обновление
            cur.execute(f"UPDATE players SET score = score {op} %s WHERE name = %s", (points, name))
            conn.commit()
            cur.close()
        finally:
            conn.close()
    return redirect("/")

@app.route("/add_to_active", methods=["POST"])
def add_to_active():
    name = request.form.get("name")
    if name:
        conn = get_db()
        try:
            cur = conn.cursor()
            # Убеждаемся, что игрок не добавится дважды и соединение не зависнет
            cur.execute("INSERT INTO active (name, present) VALUES (%s, 0) ON CONFLICT (name) DO NOTHING", (name,))
            conn.commit()
            cur.close()
        except Exception as e:
            print(f"Error adding to active: {e}")
        finally:
            conn.close()
    return redirect("/")

# Остальные функции (set_rank, delete_player и т.д.) тоже стоит обернуть в try/finally по аналогии с add_to_active
