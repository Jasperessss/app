import os
import psycopg2
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Подключение к базе данных через URL из настроек Render
def get_db_connection():
    return psycopg2.connect(os.environ.get('DATABASE_URL'))

# Функция для определения CSS-класса карточки в зависимости от ранга
# Это исправляет ошибку 'role_class' is undefined
def role_class(rank):
    ranks_map = {
        'Лидер': 'rank-leader',
        'Зам': 'rank-deputy',
        'Ветеран': 'rank-veteran',
        'Боец': 'rank-soldier'
    }
    return ranks_map.get(rank, 'rank-newbie')

# Инициализация базы данных при запуске
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # Таблица всех игроков клана
    cur.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            score INTEGER DEFAULT 0,
            rank TEXT DEFAULT 'Новичок'
        )
    ''')
    # Таблица активного мероприятия
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

# Запускаем проверку таблиц
init_db()

@app.route('/')
def index():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 1. Получаем всех игроков для отображения
    cur.execute("SELECT name, score, rank FROM players ORDER BY rank, name ASC")
    rows = cur.fetchall()
    
    # 2. Группируем игроков по рангам (исправляет ошибку 'players_grouped' is undefined)
    players_grouped = {}
    for name, score, rank in rows:
        if rank not in players_grouped:
            players_grouped[rank] = []
        players_grouped[rank].append({'name': name, 'score': score, 'rank': rank})
    
    # 3. Получаем список тех, кто в текущем мероприятии
    cur.execute("SELECT name, present FROM active ORDER BY id DESC")
    active_players = cur.fetchall()
    
    # 4. Топ-10 для таблицы лидеров
    cur.execute("SELECT name, score, rank FROM players ORDER BY score DESC LIMIT 10")
    leaderboard = cur.fetchall()
    
    # Список имен для выпадающего списка
    all_players_names = [row[0] for row in rows]
    
    cur.close()
    conn.close()
    
    return render_template('index.html', 
                           players_grouped=players_grouped, 
                           all_players=all_players_names, 
                           active_players=active_players, 
                           leaderboard=leaderboard,
                           role_class=role_class)

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
        # Ставим False, чтобы при добавлении галочка НЕ стояла автоматически
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
    if name:
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
    if name and rank:
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
    # Render использует порт из переменной окружения PORT
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
