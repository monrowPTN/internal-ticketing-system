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

# ✅ Submit Ticket Endpoint
@app.route('/submit-ticket', methods=['POST'])
def submit_ticket():
    data = request.get_json()
    print("🔁 Incoming data:", data)

    if not data:
        return jsonify({'error': 'Invalid JSON received'}), 400

    name = data.get('full_name')
    department = data.get('department')
    email = data.get('email')
    service_type = data.get('subject')
    description = data.get('message')

    if not all([name, email, service_type, description]):
        return jsonify({'error': 'Missing fields'}), 400

    if not email.endswith('@dubizzle.com.lb'):
        return jsonify({'status': 'forbidden'}), 403

    try:
        # 🔁 Now inside your /submit-ticket route:
        # ✅ Insert the ticket into the Neon database
        ticket = Ticket(
            name=name,
            email=email,
            service_type=service_type,
            description=description,
            status="Received"
        )
        db.session.add(ticket)
        db.session.commit()

        ticket_id = ticket.id  # ✅ Use the real ticket ID from Neon DB

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

        return jsonify({'status': 'success', 'ticket_id': ticket_id})

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