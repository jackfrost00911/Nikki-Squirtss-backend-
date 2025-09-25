import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify, g
from flask_cors import CORS
import sqlite3
from flask import Flask, request, jsonify, g
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

app.config.update(
    DATABASE='bookings.db',
    BOOKINGS_PER_DAY_LIMIT
)

NOTIFY_PHONE_NUMBER = os.getenv('+17755071747')  # e.g. '+15555551234'


EMAIL_HOST = os.getenv('smtp.mail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_HOST_USER = os.getenv('frostydasnowman00911@mail.com')
EMAIL_HOST_PASSWORD = os.getenv('AtH3nA818!')
NOTIFY_EMAIL_TO = os.getenv('frostydasnowman00911@mail.com')

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT,
                datetime TEXT NOT NULL,
                service TEXT NOT NULL,
                location TEXT,
                notes TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        db.commit()
        init_reviews_table()

def init_reviews_table():
    db = get_db()
    db.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    db.commit()

@app.route('/api/bookings', methods=['POST'])
def add_booking():
    data = request.json
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip()
    datetime_str = data.get('datetime', '').strip()
    service = data.get('service', '').strip()
    location = data.get('location', '').strip()
    notes = data.get('notes', '').strip()

    if not name or not email or not datetime_str or not service:
        return jsonify({'error': 'Name, email, datetime, and service are required'}), 400

    db = get_db()
    db.execute(
        'INSERT INTO bookings (name, email, phone, datetime, service, location, notes) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (name, email, phone, datetime_str, service, location, notes)
    )
    db.commit()
    return jsonify({'message': 'Booking added successfully'}), 201

@app.route('/api/reviews', methods=['GET'])
def get_reviews():
    db = get_db()
    cursor = db.execute('SELECT name, text, created_at FROM reviews ORDER BY created_at DESC')
    reviews = [dict(row) for row in cursor.fetchall()]
    return jsonify(reviews)

@app.route('/api/reviews', methods=['POST'])
def add_review():
    data = request.json
    name = data.get('name', '').strip()
    text = data.get('text', '').strip()
    if not name or not text:
        return jsonify({'error': 'Name and text are required'}), 400

    db = get_db()
    db.execute('INSERT INTO reviews (name, text) VALUES (?, ?)', (name, text))
    db.commit()
    return jsonify({'name': name, 'text': text}), 201

if __name__ == '__main__':
    init_db()
    app.run(debug=True))