# ✅ Load environment variables from .env file (for secrets)
from dotenv import load_dotenv
load_dotenv()

# ✅ Flask core libraries
from flask import Flask, request, jsonify
from flask_cors import CORS
from email.mime.text import MIMEText
import smtplib, os
from datetime import datetime

# ✅ Initialize Flask app FIRST (before referencing config)
app = Flask(__name__)  # ❗️Moved up (needed before config settings)

# ✅ Set up CORS to allow frontend domains
CORS(app, origins=[
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://tickets.local:3000",
    "http://tickets.local:3001",
    "https://olx-ticketing-frontend.vercel.app"
])

# ✅ SQLAlchemy config (after app is initialized)
from flask_sqlalchemy import SQLAlchemy
print("✅ DB URL loaded:", os.environ.get("SUPABASE_DB_URL"))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SUPABASE_DB_URL')  # Uses Neon
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ✅ Ticket database model
class Ticket(db.Model):
    __tablename__ = 'tickets'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    email = db.Column(db.String)
    description = db.Column(db.Text)
    status = db.Column(db.String, default='Received')
    service_type = db.Column(db.String)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

from time import time

# Track last submission times by email
last_submission_times = {}

# ✅ Submit Ticket Endpoint
@app.route('/tickets', methods=['POST'])
def submit_ticket():
    data = request.get_json()
    print("🔁 Incoming data:", data)

    if not data:
        return jsonify({'error': 'Invalid JSON received'}), 400

        name = data.get('full_name')
    department = data.get('department')
    # ✅ normalize email early
    email = (data.get('email') or "").strip().lower()
    service_type = data.get('subject')
    description = data.get('message')

    if not all([name, email, service_type, description]):
        return jsonify({'error': 'Missing fields'}), 400

    # ✅ get allowed domain from env (fallback to @olx.com.lb)
    allowed_domain = (os.getenv("ALLOWED_DOMAIN", "@olx.com.lb") or "").strip().lower()

    # ✅ DEBUG: print exactly what we’re checking (repr shows hidden spaces)
    print(f"🔎 EMAIL={repr(email)}  ALLOWED_DOMAIN={repr(allowed_domain)}")

    # ✅ strict end-of-string match (regex) to avoid weird edge cases
    import re
    if not re.search(re.escape(allowed_domain) + r'$', email):
        return jsonify({
            'status': 'forbidden',
            'message': f'Only {allowed_domain} emails are allowed'
        }), 403

    # ✅ NEW: Check for rapid duplicate submissions (same email within 10 seconds)
    now = time()
    if email in last_submission_times and now - last_submission_times[email] < 10:
        return jsonify({'error': 'Duplicate submission detected. Please wait a few seconds before trying again.'}), 429

    # ✅ Update last submission time
    last_submission_times[email] = now

    try:
        # ✅ Check if duplicate already in DB
        existing_ticket = Ticket.query.filter_by(
            email=email,
            service_type=service_type,
            description=description,
            status="Received"
        ).first()

        if existing_ticket:
            return jsonify({'error': 'Duplicate ticket already exists.'}), 409

        # 🔁 Insert the ticket into the Neon database
        ticket = Ticket(
            name=name,
            email=email,
            service_type=service_type,
            description=description,
            status="Received"
        )

        db.session.add(ticket)
        db.session.commit()

        ticket_id = ticket.id  # ✅ Get the real ticket ID from Neon DB

        subject_with_id = f"[Ticket #{ticket_id}] {service_type}"

        body = f"""\
🎫 Ticket #{ticket_id}

Service Type: {service_type}
Name: {name}
Department: {department}
Email: {email}

Message:
{description}
"""

        send_email(subject_with_id, body)
        print(f"✅ Ticket #{ticket_id} submitted and email sent.")

        return jsonify({'status': 'success', 'ticket_id': ticket_id}), 201

    except Exception as e:
        print("❌ Runtime Error:", e)
        return jsonify({'error': str(e)}), 500

# ✅ Email Function — uses Gmail App Password (secure)
def send_email(subject, body):
    sender = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    receiver = sender  # Can be changed if needed

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = receiver

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(sender, password)
        smtp.sendmail(sender, receiver, msg.as_string())

# ✅ Root Route for health check
@app.route('/', methods=['GET'])
def home():
    return "Internal Ticketing System is running ✅"

# ✅ Start Flask app with context
if __name__ == '__main__':
    with app.app_context():
        app.run(debug=True, port=5050)