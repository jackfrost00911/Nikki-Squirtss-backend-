import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify, g
from flask_cors import CORS
import sqlite3
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler

load_dotenv()
app = Flask(__name__)
CORS(app)

# Configure logger with rotation
handler = RotatingFileHandler('submissions.log', maxBytes=1_000_000, backupCount=3)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
handler.setFormatter(formatter)
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

app.config.update(
    DATABASE='bookings.db',
    BOOKINGS_PER_DAY_LIMIT=5
)

MAILCHIMP_API_KEY = os.getenv('MAILCHIMP_API_KEY')
MAILCHIMP_SERVER_PREFIX = os.getenv('MAILCHIMP_SERVER_PREFIX', 'us18')
MAILCHIMP_AUDIENCE_ID = os.getenv('MAILCHIMP_AUDIENCE_ID')

EMAIL_HOST = os.getenv('EMAIL_HOST')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
NOTIFY_EMAIL_TO = os.getenv('NOTIFY_EMAIL_TO')

SMS_API_KEY = os.getenv('SMS_API_KEY')
SMS_DEVICE_ID = os.getenv('SMS_DEVICE_ID')
NOTIFY_PHONE_NUMBER = os.getenv('NOTIFY_PHONE_NUMBER')


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
                text TEXT,
                rating INTEGER NOT NULL DEFAULT 5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        db.commit()
        app.logger.info('✅ Database initialized with reviews table including rating column')


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
        app.logger.error(f'Failed to send email: {e}')


def send_sms(message, phone=NOTIFY_PHONE_NUMBER):
    url = f'https://api.textbee.dev/api/v1/gateway/devices/{SMS_DEVICE_ID}/send-sms'
    headers = {'x-api-key': SMS_API_KEY}
    payload = {'recipients': [phone], 'message': message}
    try:
        response = requests.post(url, json=payload, headers=headers)
        if not response.ok:
            app.logger.error(f'SMS sending failed: {response.text}')
    except Exception as e:
        app.logger.error(f'SMS sending exception: {e}')


@app.route('/submit-email', methods=['POST'])
def submit_email():
    data = request.get_json() or request.form
    email = data.get('email')
    if not email or '@' not in email:
        return jsonify({'error': 'Valid email required'}), 400

    app.logger.info(f'New email submission: {email} from IP: {request.remote_addr}')
    url = f'https://{MAILCHIMP_SERVER_PREFIX}.api.mailchimp.com/3.0/lists/{MAILCHIMP_AUDIENCE_ID}/members'
    headers = {'Content-Type': 'application/json'}
    payload = {'email_address': email, 'status': 'subscribed'}
    response = requests.post(url, json=payload, headers=headers, auth=('anystring', MAILCHIMP_API_KEY))
    if response.status_code in [200, 201]:
        return jsonify({'message': 'Subscription successful'})
    else:
        return jsonify({'error': response.json().get('detail', 'Subscription failed')}), response.status_code


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

    app.logger.info(f'Booking from {email} from IP: {request.remote_addr}')

    # Mailchimp subscription
    url = f'https://{MAILCHIMP_SERVER_PREFIX}.api.mailchimp.com/3.0/lists/{MAILCHIMP_AUDIENCE_ID}/members'
    headers = {'Content-Type': 'application/json'}
    payload = {'email_address': email, 'status': 'subscribed'}
    response = requests.post(url, json=payload, headers=headers, auth=('anystring', MAILCHIMP_API_KEY))
    if response.status_code in (200, 201):
        app.logger.info(f'Successfully subscribed: {email}')
    else:
        error_detail = response.json().get('detail', 'Unknown error')
        app.logger.error(f'Failed subscribing {email}: {error_detail}')

    # Send notifications
    send_email('New Booking', f'New booking from {name} at {datetime_str} for {service}')
    send_sms(f'New booking from {name} at {datetime_str} for {service}')

    return jsonify({'message': 'Booking added successfully'}), 201


# GET all reviews
@app.route('/api/reviews', methods=['GET'])
def get_reviews():
    db = get_db()
    cursor = db.execute('SELECT id, name, text, rating, created_at FROM reviews ORDER BY created_at DESC')
    reviews = []
    for row in cursor.fetchall():
        reviews.append({
            'id': row['id'],
            'name': row['name'],
            'text': row['text'],
            'rating': row['rating'],
            'created_at': row['created_at']
        })
    return jsonify(reviews)


# POST new review
@app.route('/api/reviews', methods=['POST'])
def add_review():
    data = request.json
    name = data.get('name', '').strip()
    text = data.get('text', '').strip()
    rating = data.get('rating')
    
    # Validation
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    
    if rating is None:
        return jsonify({'error': 'Rating is required'}), 400
    
    if not isinstance(rating, int) or rating < 1 or rating > 5:
        return jsonify({'error': 'Rating must be between 1 and 5'}), 400

    try:
        db = get_db()
        cursor = db.execute(
            'INSERT INTO reviews (name, text, rating) VALUES (?, ?, ?)',
            (name, text, rating)
        )
        db.commit()
        
        # Get the newly created review
        new_id = cursor.lastrowid
        new_review = db.execute('SELECT id, name, text, rating, created_at FROM reviews WHERE id = ?', (new_id,)).fetchone()
        
        return jsonify({
            'id': new_review['id'],
            'name': new_review['name'],
            'text': new_review['text'],
            'rating': new_review['rating'],
            'created_at': new_review['created_at']
        }), 201
        
    except Exception as e:
        app.logger.error(f'Error adding review: {e}')
        return jsonify({'error': str(e)}), 500
        
    if __name__ == '__main__':
    init_db()
    app.run(debug=True)
