import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify, g
from flask_cors import CORS
import sqlite3

app = Flask(__name__)
CORS(app)

app.config.update(
    DATABASE='bookings.db',
    BOOKINGS_PER_DAY_LIMIT=5
)

# Email config via environment variables
EMAIL_HOST = os.getenv('smtp.mail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_HOST_USER = os.getenv('frostydasnowman00911@mail.com')
EMAIL_HOST_PASSWORD = os.getenv('AtH3nA818!')
NOTIFY_EMAIL_TO = os.getenv('frostydasnowman00811@mail.com')

# SMS gateway config from Android SMS Gateway provider
SMS_API_KEY = os.getenv('d4b59066-c804-4f3c-a36e-6744b29b4c6a')
SMS_DEVICE_ID = os.getenv('68d675e53b8a4d33b1cf2c42')
NOTIFY_PHONE_NUMBER = os.getenv('+17755071747')

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'], detect_types=sqlite3.PARSE_DECLTYPES)
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
        db.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        db.commit()

def send_email(subject, body, to_email=NOTIFY_EMAIL_TO):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_HOST_USER
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    try:
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        app.logger.error(f"Failed to send email: {e}")

def send_sms(message, phone=NOTIFY_PHONE_NUMBER):
    url = f'https://api.textbee.dev/api/v1/gateway/devices/{SMS_DEVICE_ID}/send-sms'
    headers = {'x-api-key': SMS_API_KEY}
    payload = {'recipients': [phone], 'message': message}
    try:
        response = requests.post(url, json=payload, headers=headers)
        if not response.ok:
            app.logger.error(f"SMS sending failed: {response.text}")
    except Exception as e:
        app.logger.error(f"SMS sending exception: {e}")

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
    db.execute('''INSERT INTO bookings (name, email, phone, datetime, service, location, notes)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
               (name, email, phone, datetime_str, service, location, notes))
    db.commit()

    # Send notification emails and SMS
    send_email('New Booking', f'New booking from {name} at {datetime_str} for {service}')
    send_sms(f'New booking from {name} at {datetime_str} for {service}')

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

    # Send notification emails and SMS
    send_email('New Review', f'New review from {name}: {text}')
    send_sms(f'New review from {name}: {text}')

    return jsonify({'name': name, 'text': text}), 201

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
