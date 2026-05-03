import os
import psycopg2
import psycopg2.extras
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Твои оригинальные веса и ранги
RANK_WEIGHT = {"High Priority": 4, "Rinehart": 3, "Young": 2, "Test": 1}

def get_db_connection():
    return psycopg2.connect(os.environ.get('DATABASE_URL'))

# Функция для CSS-классов (возвращает hp, rinehart, young, test)
def role_class(rank):
    mapping = {
        "High Priority": "hp",
        "Rinehart": "rinehart",
        "Young": "young",
        "Test": "test"
    }
    return mapping.get(rank, "test")

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS players (
            name TEXT PRIMARY KEY,
            score INTEGER DEFAULT 0,
            rank TEXT DEFAULT 'Test'
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS active (
            name TEXT PRIMARY KEY,
            present BOOLEAN DEFAULT FALSE
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()

init_db()

@app.route("/")
def index():
    conn = get_db_connection()
    # Используем RealDictCursor, чтобы обращаться к данным как p['name']
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # 1. Получаем всех игроков
    cur.execute("SELECT * FROM players")
    players_raw = cur.fetchall()
    
    # 2. Группируем и сортируем (как в твоем старом коде)
    groups = {rank: [] for rank in RANK_WEIGHT.keys()}
    for p in players_raw:
        rank = p["rank"] if p["rank"] in groups else "Test"
        groups[rank].append(p)
    
    # Сортируем внутри групп по очкам
    for rank in groups:
        groups[rank].sort(key=lambda x: x['score'], reverse=True)

    # 3. Получаем список мероприятия с данными из таблицы players (JOIN)
    cur.execute("""
        SELECT p.*, a.present 
        FROM active a 
        JOIN players p ON a.name = p.name
    """)
    active_raw = cur.fetchall()
    # Сортировка мероприятия по весу ранга и очкам
    active_sorted = sorted(active_raw, 
                           key=lambda x: (RANK_WEIGHT.get(x['rank'], 0), x['score']), 
                           reverse=True)
    
    cur.close()
    conn.close()
    
    return render_template(
        "index.html",
        players_grouped=groups,
        active=active_sorted,
        role_class=role_class
    )

@app.route("/add_player", methods=["POST"])
def add_player():
    name = request.form.get("name", "").strip()
    if name:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO players (name, score, rank) VALUES (%s, 0, 'Test') ON CONFLICT DO NOTHING", (name,))
        conn.commit()
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

    if points > 0 and name:
        conn = get_db_connection()
        cur = conn.cursor()
        if mode == "add":
            cur.execute("UPDATE players SET score = score + %s WHERE name = %s", (points, name))
        else:
            cur.execute("UPDATE players SET score = score - %s WHERE name = %s", (points, name))
        conn.commit()
        cur.close()
        conn.close()
    return redirect("/")

@app.route("/set_rank", methods=["POST"])
def set_rank():
    name = request.form.get("name")
    rank = request.form.get("rank")
    if name and rank:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE players SET rank = %s WHERE name = %s", (rank, name))
        conn.commit()
        cur.close()
        conn.close()
    return redirect("/")

@app.route("/add_to_active", methods=["POST"])
def add_to_active():
    name = request.form.get("name")
    if name:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO active (name, present) VALUES (%s, FALSE) ON CONFLICT DO NOTHING", (name,))
        conn.commit()
        cur.close()
        conn.close()
    return redirect("/")

@app.route("/remove_active", methods=["POST"])
def remove_active():
    name = request.form.get("name")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM active WHERE name = %s", (name,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect("/")

@app.route("/delete_player", methods=["POST"])
def delete_player():
    name = request.form.get("name")
    conn = get_db_connection()
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
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE active SET present = NOT present WHERE name = %s", (name,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect("/")

@app.route("/clear")
def clear():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM active")
    conn.commit()
    cur.close()
    conn.close()
    return redirect("/")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
