import os
import psycopg2
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Функция для подключения к базе данных (используем DATABASE_URL из настроек Render)
def get_db_connection():
    conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
    return conn

# Инициализация базы данных (создание таблиц, если их нет)
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # Таблица всех игроков
    cur.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            score INTEGER DEFAULT 0
        )
    ''')
    # Таблица активных участников мероприятия
    # Поле name должно быть UNIQUE для работы ON CONFLICT
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

# Запускаем инициализацию при старте приложения
init_db()

@app.route('/')
def index():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Получаем список всех игроков для выпадающего списка
    cur.execute("SELECT name FROM players ORDER BY name ASC")
    all_players = [row[0] for row in cur.fetchall()]
    
    # Получаем список участников текущего мероприятия
    cur.execute("SELECT name, present FROM active ORDER BY id DESC")
    active_players = cur.fetchall()
    
    # Получаем топ игроков по очкам
    cur.execute("SELECT name, score FROM players ORDER BY score DESC LIMIT 10")
    leaderboard = cur.fetchall()
    
    cur.close()
    conn.close()
    return render_template('index.html', 
                           all_players=all_players, 
                           active_players=active_players, 
                           leaderboard=leaderboard)

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

@app.route('/add_to_active', methods=['POST'])
def add_to_active():
    name = request.form.get('name')
    if name:
        conn = get_db_connection()
        cur = conn.cursor()
        # Статус False гарантирует, что человек добавится БЕЗ галочки "готов"
        cur.execute("INSERT INTO active (name, present) VALUES (%s, False) ON CONFLICT (name) DO NOTHING", (name,))
        conn.commit()
        cur.close()
        conn.close()
    return redirect(url_for('index'))

@app.route('/toggle', methods=['POST'])
def toggle_present():
    name = request.form.get('name')
    conn = get_db_connection()
    cur = conn.cursor()
    # Инвертируем статус (готов/не готов)
    cur.execute("UPDATE active SET present = NOT present WHERE name = %s", (name,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/score', methods=['POST'])
def update_score():
    name = request.form.get('name')
    change = int(request.form.get('change', 0))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE players SET score = score + %s WHERE name = %s", (change, name))
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
    # Порт берем из переменной окружения Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
