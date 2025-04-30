from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from email.mime.text import MIMEText
import smtplib, os

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

# ✅ Database Config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tickets.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ✅ Ticket Model
class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100))
    department = db.Column(db.String(100))
    email = db.Column(db.String(100))
    subject = db.Column(db.String(200))
    message = db.Column(db.Text)
    status = db.Column(db.String(50), default='Received')

# ✅ Submit Ticket Endpoint
@app.route('/submit-ticket', methods=['POST'])
def submit_ticket():
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Invalid JSON received'}), 400

    full_name = data.get('full_name')
    department = data.get('department')
    email = data.get('email')
    subject_raw = data.get('subject', 'New Internal Ticket')
    message = data.get('message')

    if not all([full_name, department, email, subject_raw, message]):
        return jsonify({'error': 'Missing fields'}), 400

    if not email.endswith('@dubizzle.com.lb'):
        return jsonify({'status': 'forbidden'}), 403

    ticket = Ticket(
        full_name=full_name,
        department=department,
        email=email,
        subject=subject_raw,
        message=message
    )
    db.session.add(ticket)
    db.session.commit()

    ticket_id = ticket.id

    subject_with_id = f"[Ticket #{ticket_id}] {subject_raw}"
    body = f"""\
🎫 Ticket #{ticket_id}

📌 Service Type: {subject_with_id}
🧑 Name: {full_name}
🏢 Department: {department}
✉️ Email: {email}

📝 Message:
{message}
"""

    send_email(subject_with_id, body)

    return jsonify({'status': 'success', 'ticket_id': ticket_id})

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
        db.drop_all()
        db.create_all()

    app.run(debug=True, port=5050)