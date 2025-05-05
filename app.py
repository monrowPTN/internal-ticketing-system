from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from email.mime.text import MIMEText
import smtplib, os
from datetime import datetime

# ✅ Flask App Setup
app = Flask(__name__)
CORS(app, origins=[
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://tickets.local:3000",
    "http://tickets.local:3001",
    "https://olx-ticketing-frontend.vercel.app"
])

# ✅ Database Config (Now Supabase)
print("✅ DB URL:", os.environ.get('SUPABASE_DB_URL'))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SUPABASE_DB_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ✅ Ticket Model — updated to match Supabase
class Ticket(db.Model):
    __tablename__ = 'tickets'  # Supabase table name

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    email = db.Column(db.String)
    description = db.Column(db.Text)
    status = db.Column(db.String, default='Received')
    service_type = db.Column(db.String)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ✅ Submit Ticket Endpoint — rewritten to match Supabase fields
@app.route('/submit-ticket', methods=['POST'])
def submit_ticket():
    data = request.get_json()

print("🔁 Incoming data:", data)  # test what the frontend sends
    
    if not data:
        return jsonify({'error': 'Invalid JSON received'}), 400

    name = data.get('full_name')  # full_name maps to 'name' in DB
    department = data.get('department')  # Ignored for now
    email = data.get('email')
    service_type = data.get('subject')  # subject → service_type
    description = data.get('message')

    if not all([name, department, email, service_type, description]):
        return jsonify({'error': 'Missing fields'}), 400

    if not email.endswith('@dubizzle.com.lb'):
        return jsonify({'status': 'forbidden'}), 403

    try:
        ticket = Ticket(
            name=name,
            email=email,
            service_type=service_type,
            description=description,
            status="Received"
        )
        db.session.add(ticket)
        db.session.commit()

        ticket_id = ticket.id
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

        return jsonify({'status': 'success', 'ticket_id': ticket_id})

    except Exception as e:
        print("❌ DB Error:", e)
        return jsonify({'error': 'Failed to save ticket'}), 500

# ✅ Send Email Function
def send_email(subject, body):
    sender = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    receiver = sender

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = receiver

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(sender, password)
        smtp.sendmail(sender, receiver, msg.as_string())

# ✅ Root Route
@app.route('/', methods=['GET'])
def home():
    return "Internal Ticketing System is running ✅"

# ✅ Launch App with DB Reset
if __name__ == '__main__':
    with app.app_context():
        app.run(debug=True, port=5050)