from flask import Flask, render_template, request, redirect
import sqlite3
import webbrowser
import threading

app = Flask(__name__)
app.secret_key = "event_system_key"
DB = "players.db"

RANK_WEIGHT = {"High Priority": 4, "Rinehart": 3, "Young": 2, "Test": 1}

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def sort_logic(player):
    return (RANK_WEIGHT.get(player["rank"], 0), player["score"])

@app.route("/")
def index():
    conn = get_db()
    players_raw = conn.execute("SELECT * FROM players").fetchall()
    # Используем JOIN, чтобы данные в Event всегда соответствовали таблице Players
    active_raw = conn.execute("""
        SELECT p.*, a.present 
        FROM active a 
        JOIN players p ON a.name = p.name
    """).fetchall()
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
        try:
            conn.execute("INSERT INTO players (name, score, rank) VALUES (?, 0, 'Test')", (name,))
            conn.commit()
        except: pass
        finally: conn.close()
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
        op = "+" if mode == "add" else "-"
        conn.execute(f"UPDATE players SET score = score {op} ? WHERE name = ?", (points, name))
        conn.commit()
        conn.close()
    return redirect("/")

@app.route("/set_rank", methods=["POST"])
def set_rank():
    name = request.form.get("name")
    rank = request.form.get("rank")
    conn = get_db()
    conn.execute("UPDATE players SET rank = ? WHERE name = ?", (rank, name))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/add_to_active", methods=["POST"])
def add_to_active():
    name = request.form.get("name")
    conn = get_db()
    try:
        conn.execute("INSERT INTO active (name, present) VALUES (?, 0)", (name,))
        conn.commit()
    except: pass
    finally: conn.close()
    return redirect("/")

@app.route("/remove_active", methods=["POST"])
def remove_active():
    name = request.form.get("name")
    conn = get_db()
    conn.execute("DELETE FROM active WHERE name = ?", (name,))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/delete_player", methods=["POST"])
def delete_player():
    name = request.form.get("name")
    conn = get_db()
    conn.execute("DELETE FROM players WHERE name = ?", (name,))
    conn.execute("DELETE FROM active WHERE name = ?", (name,))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/toggle", methods=["POST"])
def toggle():
    name = request.form.get("name")
    conn = get_db()
    conn.execute("UPDATE active SET present = NOT present WHERE name = ?", (name,))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/clear")
def clear():
    conn = get_db()
    conn.execute("DELETE FROM active")
    conn.commit()
    conn.close()
    return redirect("/")

def open_browser():
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == "__main__":
    conn = get_db()
    conn.execute("CREATE TABLE IF NOT EXISTS players (name TEXT PRIMARY KEY, score INTEGER DEFAULT 0, rank TEXT DEFAULT 'Test')")
    conn.execute("CREATE TABLE IF NOT EXISTS active (name TEXT PRIMARY KEY, present INTEGER DEFAULT 0)")
    conn.commit()
    conn.close()
    threading.Timer(1.5, open_browser).start()
    app.run(debug=False)