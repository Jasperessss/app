import os
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Настройка базы данных
# Файл database.db будет создан автоматически в корне папки
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_PATH'] = os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + app.config['SQLALCHEMY_DATABASE_PATH']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- МОДЕЛИ ДАННЫХ ---

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    rank = db.Column(db.String(50), nullable=False)
    score = db.Column(db.Integer, default=0)

class ActivePlayer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    present = db.Column(db.Boolean, default=True)
    score = db.Column(db.Integer, default=0)

# --- АВТОМАТИЧЕСКОЕ СОЗДАНИЕ ТАБЛИЦ ---
# Этот блок решает проблему "Internal Server Error" при первом запуске
with app.app_context():
    db.create_all()

# --- МАРШРУТЫ (ROUTES) ---

@app.route('/')
def index():
    try:
        players = Player.query.all()
        active = ActivePlayer.query.all()
        
        ranks = ['High Priority', 'Rinehart', 'Young', 'Test']
        # Группируем игроков по рангам для отображения
        players_grouped = {rank: [p for p in players if p.rank == rank] for rank in ranks}
        
        return render_template('index.html', 
                               players_grouped=players_grouped, 
                               active=active,
                               role_class=lambda r: str(r).lower().replace(' ', '-'))
    except Exception as e:
        return f"Ошибка базы данных: {e}. Попробуйте обновить страницу."

@app.route('/add_player', methods=['POST'])
def add_player():
    name = request.form.get('name')
    rank = request.form.get('rank')
    if name and rank:
        new_player = Player(name=name, rank=rank)
        db.session.add(new_player)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/toggle_active', methods=['POST'])
def toggle_active():
    name = request.form.get('name')
    # Проверяем, есть ли уже такой игрок в активных
    existing = ActivePlayer.query.filter_by(name=name).first()
    if existing:
        db.session.delete(existing)
    else:
        new_active = ActivePlayer(name=name)
        db.session.add(new_active)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/api/get_data')
def get_data():
    players = Player.query.all()
    active = ActivePlayer.query.all()
    return jsonify({
        "players": [{"name": p.name, "score": p.score} for p in players],
        "active": [{"name": a.name, "score": a.score} for a in active]
    })

if __name__ == '__main__':
    app.run(debug=True)
