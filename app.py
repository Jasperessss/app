import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, redirect

app = Flask(__name__)
app.secret_key = "event_system_key"

# Ссылка на базу данных из переменных окружения Render
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

# Веса рангов для правильной сортировки
RANK_WEIGHT = {"High Priority": 4, "Rinehart": 3, "Young": 2, "Test": 1}

def sort_logic(player):
    # Если баллов нет (NULL), считаем как 0
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

    # Группировка игроков
    groups = {rank: [] for rank in RANK_WEIGHT.keys()}
    for p in sorted(players_raw, key=sort_logic, reverse=True):
        rank = p.get("rank")
        if rank in groups:
            groups[rank].append(p)
        else:
            groups["Test"].append(p)

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
        try:
            cur = conn.cursor()
            cur.execute("INSERT INTO players (name, score, rank) VALUES (%s, 0, 'Test') ON CONFLICT (name) DO NOTHING", (name,))
            conn.commit()
            cur.close()
        finally:
            conn.close()
    return redirect("/")

@app.route("/score", methods=["POST"])
def score():
    name = request.form.get("name")
    mode = request.form.get("mode")
    try:
        points = int(request.form.get("points", 0))
    except (ValueError, TypeError):
        points = 0

    if points > 0 and name:
        conn = get_db()
        try:
            cur = conn.cursor()
            op = "+" if mode == "add" else "-"
            cur.execute(f"UPDATE players SET score = score {op} %s WHERE name = %s", (points, name))
            conn.commit()
            cur.close()
        finally:
            conn.close()
    return redirect("/")

@app.route("/set_rank", methods=["POST"])
def set_rank():
    name = request.form.get("name")
    rank = request.form.get("rank")
    if name and rank:
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE players SET rank = %s WHERE name = %s", (rank, name))
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
            # ИСПОЛЬЗУЕМ True ВМЕСТО 1 ДЛЯ ТИПА BOOLEAN
            cur.execute("INSERT INTO active (name, present) VALUES (%s, True) ON CONFLICT (name) DO NOTHING", (name,))
            conn.commit()
            cur.close()
        finally:
            conn.close()
    return redirect("/")

@app.route("/toggle", methods=["POST"])
def toggle():
    name = request.form.get("name")
    if name:
        conn = get_db()
        try:
            cur = conn.cursor()
            # Переключение True <-> False
            cur.execute("UPDATE active SET present = NOT present WHERE name = %s", (name,))
            conn.commit()
            cur.close()
        finally:
            conn.close()
    return redirect("/")

@app.route("/remove_active", methods=["POST"])
def remove_active():
    name = request.form.get("name")
    if name:
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM active WHERE name = %s", (name,))
            conn.commit()
            cur.close()
        finally:
            conn.close()
    return redirect("/")

@app.route("/delete_player", methods=["POST"])
def delete_player():
    name = request.form.get("name")
    if name:
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM active WHERE name = %s", (name,))
            cur.execute("DELETE FROM players WHERE name = %s", (name,))
            conn.commit()
            cur.close()
        finally:
            conn.close()
    return redirect("/")

@app.route("/clear")
def clear():
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM active")
        conn.commit()
        cur.close()
    finally:
        conn.close()
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
