from flask import Flask, request, redirect, jsonify
from flask_cors import CORS
import psycopg2
import os
from datetime import datetime
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
CORS(app)

# Environment variables - Set these in your Render dashboard
DATABASE_URL = os.environ.get('DATABASE_URL')
# Fix Render's postgres:// to postgresql:// for psycopg2
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
MAILCHIMP_API_KEY = os.environ.get('MAILCHIMP_API_KEY')
MAILCHIMP_SERVER = os.environ.get('MAILCHIMP_SERVER')
MAILCHIMP_LIST_ID = os.environ.get('MAILCHIMP_LIST_ID')
TEXTBEE_API_KEY = os.environ.get('TEXTBEE_API_KEY')
TEXTBEE_DEVICE_ID = os.environ.get('TEXTBEE_DEVICE_ID')
YOUR_PHONE_NUMBER = os.environ.get('YOUR_PHONE_NUMBER')
YOUR_EMAIL = os.environ.get('YOUR_EMAIL')
SMTP_EMAIL = os.environ.get('SMTP_EMAIL')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')


def get_db_connection():
    """Create database connection"""
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def add_to_mailchimp(email, first_name, last_name=''):
    """Add subscriber to MailChimp list"""
    try:
        url = f"https://{MAILCHIMP_SERVER}.api.mailchimp.com/3.0/lists/{MAILCHIMP_LIST_ID}/members"
        
        headers = {
            "Authorization": f"Bearer {MAILCHIMP_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "email_address": email,
            "status": "subscribed",
            "merge_fields": {
                "FNAME": first_name,
                "LNAME": last_name
            }
        }
        
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code in [200, 201]:
            print(f"Added {email} to MailChimp successfully")
            return True
        else:
            print(f"MailChimp error: {response.json()}")
            return False
            
    except Exception as e:
        print(f"MailChimp exception: {str(e)}")
        return False

def send_sms_notification(message):
    """Send SMS via TextBee"""
    try:
        url = f"https://api.textbee.dev/api/v1/gateway/devices/{TEXTBEE_DEVICE_ID}/send-sms"
        
        headers = {
            'x-api-key': TEXTBEE_API_KEY,
            'Content-Type': 'application/json'
        }
        
        data = {
            "recipients": [YOUR_PHONE_NUMBER],
            "message": message
        }
        
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code == 200:
            print("SMS notification sent successfully")
            return True
        else:
            print(f"TextBee error: {response.text}")
            return False
            
    except Exception as e:
        print(f"SMS exception: {str(e)}")
        return False

def send_email_notification(subject, body):
    """Send email notification"""
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_EMAIL
        msg['To'] = YOUR_EMAIL
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print("Email notification sent successfully")
        return True
        
    except Exception as e:
        print(f"Email exception: {str(e)}")
        return False

# Email subscription endpoint
@app.route('/submit-email', methods=['POST'])
def submit_email():
    try:
        email = request.form.get('email')
        
        if not email:
            return "Email is required", 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO email_subscribers (email, subscribed_at)
            VALUES (%s, %s)
            ON CONFLICT (email) DO NOTHING
        """, (email, datetime.now()))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        add_to_mailchimp(email, "VIP", "Subscriber")
        
        return redirect('/?success=subscribed')
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return f"Error: {str(e)}", 500

# Booking submission endpoint
@app.route('/submit-booking', methods=['POST'])
def submit_booking():
    try:
        data = request.json
        
        first_name = data.get('firstName')
        last_name = data.get('lastName', '')
        email = data.get('email')
        phone = data.get('phone')
        service = data.get('service')
        date = data.get('date')
        time = data.get('time')
        location = data.get('location', '')
        message = data.get('message', '')
        
        if not all([first_name, email, phone, service, date, time]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO bookings 
            (first_name, last_name, email, phone, service, booking_date, booking_time, location, message, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (first_name, last_name, email, phone, service, date, time, location, message, datetime.now()))
        
        booking_id = cursor.fetchone()[0]
        
        conn.commit()
        cursor.close()
        conn.close()
        
        add_to_mailchimp(email, first_name, last_name)
        
        sms_message = f"""🔔 NEW BOOKING #{booking_id}

Name: {first_name} {last_name}
Phone: {phone}
Service: {service}
Date: {date} at {time}
Location: {location}

Check dashboard for details."""
        
        send_sms_notification(sms_message)
        
        email_subject = f"🔔 New Booking Request #{booking_id} - {first_name} {last_name}"
        email_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color: #d35a9a;">New Booking Request Received</h2>
            <div style="background: #f5f5f5; padding: 20px; border-radius: 8px;">
                <p><strong>Booking ID:</strong> #{booking_id}</p>
                <p><strong>Name:</strong> {first_name} {last_name}</p>
                <p><strong>Email:</strong> {email}</p>
                <p><strong>Phone:</strong> {phone}</p>
                <p><strong>Service:</strong> {service}</p>
                <p><strong>Date:</strong> {date}</p>
                <p><strong>Time:</strong> {time}</p>
                <p><strong>Location:</strong> {location}</p>
                <p><strong>Special Requests:</strong><br>{message if message else 'None'}</p>
                <p><strong>Submitted:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        </body>
        </html>
        """
        
        send_email_notification(email_subject, email_body)
        
        return jsonify({
            'success': True,
            'bookingId': booking_id,
            'message': 'Booking request submitted successfully'
        }), 200
        
    except Exception as e:
        print(f"Booking error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Get all bookings (for admin view)
@app.route('/api/bookings', methods=['GET'])
def get_bookings():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, first_name, last_name, email, phone, service, 
                   booking_date, booking_time, location, message, created_at
            FROM bookings
            ORDER BY created_at DESC
        """)
        
        bookings = cursor.fetchall()
        cursor.close()
        conn.close()
        
        booking_list = []
        for booking in bookings:
            booking_list.append({
                'id': booking[0],
                'firstName': booking[1],
                'lastName': booking[2],
                'email': booking[3],
                'phone': booking[4],
                'service': booking[5],
                'date': str(booking[6]),
                'time': booking[7],
                'location': booking[8],
                'message': booking[9],
                'createdAt': str(booking[10])
            })
        
        return jsonify(booking_list)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
