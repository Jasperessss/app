import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, redirect

app = Flask(__name__)
app.secret_key = "event_system_key"

# Берем ссылку из переменных окружения Render
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db():
    # Подключение к Supabase
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    return conn

# Веса для рангов
RANK_WEIGHT = {"High Priority": 4, "Rinehart": 3, "Young": 2, "Test": 1}

def sort_logic(player):
    return (RANK_WEIGHT.get(player["rank"], 0), player["score"])

@app.route("/")
def index():
    conn = get_db()
    # RealDictCursor позволяет обращаться к полям по именам, как в твоем коде
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
    conn.close()

    # Сортировка и группировка
    sorted_players = sorted(players_raw, key=sort_logic, reverse=True)
    groups = {rank: [] for rank in RANK_WEIGHT.keys()}
    for p in sorted_players:
        rank = p["rank"] if p["rank"] in groups else "Test"
        groups[rank].append(p)

    active_sorted = sorted(active_raw, key=sort_logic, reverse=True)

    return render_template(
        "index.html",
        players_grouped=groups,
        active=active_sorted,
        role_class=lambda r: {"High Priority": "hp", "Rinehart": "rinehart", "Young": "young", "Test": "test"}.get(r, "test")
    )

@app.route("/add_player", methods=["POST"])
def add_player():
    name = request.form.get("name", "").strip()
    if name:
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO players (name, score, rank) VALUES (%s, 0, 'Test') ON CONFLICT DO NOTHING", (name,))
            conn.commit()
        except: pass
        finally: 
            cur.close()
            conn.close()
    return redirect("/")

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
        cur = conn.cursor()
        op = "+" if mode == "add" else "-"
        # В PostgreSQL используем %s вместо ?
        cur.execute(f"UPDATE players SET score = score {op} %s WHERE name = %s", (points, name))
        conn.commit()
        cur.close()
        conn.close()
    return redirect("/")

@app.route("/set_rank", methods=["POST"])
def set_rank():
    name = request.form.get("name")
    rank = request.form.get("rank")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE players SET rank = %s WHERE name = %s", (rank, name))
    conn.commit()
    cur.close()
    conn.close()
    return redirect("/")

@app.route("/add_to_active", methods=["POST"])
def add_to_active():
    name = request.form.get("name")
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO active (name, present) VALUES (%s, 0) ON CONFLICT DO NOTHING", (name,))
        conn.commit()
    except: pass
    finally: 
        cur.close()
        conn.close()
    return redirect("/")

@app.route("/remove_active", methods=["POST"])
def remove_active():
    name = request.form.get("name")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM active WHERE name = %s", (name,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect("/")

@app.route("/delete_player", methods=["POST"])
def delete_player():
    name = request.form.get("name")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM players WHERE name = %s", (name,))
    cur.execute("DELETE FROM active WHERE name = %s", (name,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect("/")

@app.route("/toggle", methods=["POST"])
def toggle():
    name = request.form.get("name")
    conn = get_db()
    cur = conn.cursor()
    # Специальный синтаксис инверсии для PostgreSQL
    cur.execute("UPDATE active SET present = (NOT present::boolean)::integer WHERE name = %s", (name,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect("/")

@app.route("/clear")
def clear():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM active")
    conn.commit()
    cur.close()
    conn.close()
    return redirect("/")

if __name__ == "__main__":
    # Создание таблиц при запуске, если они не существуют
    if DATABASE_URL:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS players (name TEXT PRIMARY KEY, score INTEGER DEFAULT 0, rank TEXT DEFAULT 'Test')")
        cur.execute("CREATE TABLE IF NOT EXISTS active (name TEXT PRIMARY KEY, present INTEGER DEFAULT 0)")
        conn.commit()
        cur.close()
        conn.close()
    
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
