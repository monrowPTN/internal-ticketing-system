from dotenv import load_dotenv
load_dotenv()
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from email.mime.text import MIMEText
import smtplib, os

# Load .env file
print("EMAIL_USER from .env:", os.getenv("EMAIL_USER"))

# Flask app setup
app = Flask(__name__)
CORS(app, origins=[
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://tickets.local:3000",
    "https://olx-ticketing-frontend.vercel.app"
])

# SQLAlchemy config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tickets.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Ticket model
class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100))
    department = db.Column(db.String(100))
    email = db.Column(db.String(100))
    subject = db.Column(db.String(200))
    message = db.Column(db.Text)

# Submit ticket endpoint
@app.route('/submit-ticket', methods=['POST'])
def submit_ticket():
    data = request.json
    full_name = data.get('full_name')
    department = data.get('department')
    email = data.get('email')
    message = data.get('message')
    subject = data.get('subject', 'New Internal Ticket')

    # Save to database
    ticket = Ticket(
        full_name=full_name,
        department=department,
        email=email,
        subject=subject,
        message=message
    )
    db.session.add(ticket)
    db.session.commit()

    # Optional email domain restriction
    if not email.endswith('@dubizzle.com.lb'):
        return jsonify({'status': 'forbidden'}), 403

    # Send email
    body = f"From: {full_name}\nDepartment: {department}\nEmail: {email}\n\nMessage:\n{message}"
    send_email(subject, body)

    return jsonify({'status': 'success'})

# Send email function
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

# Get all tickets
@app.route('/tickets', methods=['GET'])
def get_tickets():
    tickets = Ticket.query.order_by(Ticket.id.desc()).all()
    tickets_list = [
        {
            "id": ticket.id,
            "full_name": ticket.full_name,
            "department": ticket.department,
            "email": ticket.email,
            "subject": ticket.subject,
            "message": ticket.message
        } for ticket in tickets
    ]
    return jsonify(tickets_list)

# Home route for Render root access
@app.route('/', methods=['GET'])
def home():
    return "Internal Ticketing System is running ✅"

# Run Flask app
if __name__ == '__main__':
    app.run(debug=True, port=5050)