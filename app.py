import os
import psycopg2
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

def get_db_connection():
    return psycopg2.connect(os.environ.get('DATABASE_URL'))

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            score INTEGER DEFAULT 0,
            rank TEXT DEFAULT 'Новичок'
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS active (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            present BOOLEAN DEFAULT FALSE
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()

init_db()

@app.route('/')
def index():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT name, score, rank FROM players ORDER BY name ASC")
    all_players = cur.fetchall()
    cur.execute("SELECT name, present FROM active ORDER BY id DESC")
    active_players = cur.fetchall()
    cur.execute("SELECT name, score, rank FROM players ORDER BY score DESC LIMIT 10")
    leaderboard = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('index.html', all_players=all_players, active_players=active_players, leaderboard=leaderboard)

@app.route('/add_player', methods=['POST'])
def add_player():
    name = request.form.get('name')
    if name:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO players (name) VALUES (%s) ON CONFLICT (name) DO NOTHING", (name,))
        conn.commit()
        cur.close()
        conn.close()
    return redirect(url_for('index'))

@app.route('/delete_player', methods=['POST'])
def delete_player():
    name = request.form.get('name')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM players WHERE name = %s", (name,))
    cur.execute("DELETE FROM active WHERE name = %s", (name,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/add_to_active', methods=['POST'])
def add_to_active():
    name = request.form.get('name')
    if name:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO active (name, present) VALUES (%s, False) ON CONFLICT (name) DO NOTHING", (name,))
        conn.commit()
        cur.close()
        conn.close()
    return redirect(url_for('index'))

@app.route('/remove_active', methods=['POST'])
def remove_active():
    name = request.form.get('name')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM active WHERE name = %s", (name,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/toggle', methods=['POST'])
def toggle_present():
    name = request.form.get('name')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE active SET present = NOT present WHERE name = %s", (name,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/score', methods=['POST'])
def update_score():
    name = request.form.get('name')
    change = request.form.get('change', 0)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE players SET score = score + %s WHERE name = %s", (int(change), name))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/set_rank', methods=['POST'])
def set_rank():
    name = request.form.get('name')
    rank = request.form.get('rank')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE players SET rank = %s WHERE name = %s", (rank, name))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/clear_active', methods=['POST'])
def clear_active():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM active")
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
