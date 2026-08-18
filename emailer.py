import smtplib
import json
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

CONFIG_FILE = "email_config.json"
DEFAULT_TEACHER_EMAIL = "rlmorgan512@gmail.com"

def save_teacher_email(email: str):
    """Saves a custom teacher email address to local config file."""
    with open(CONFIG_FILE, "w") as f:
        json.dump({"teacher_email": email}, f)

def get_teacher_email() -> str:
    """Retrieves the saved teacher email address or falls back to default."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                return data.get("teacher_email", DEFAULT_TEACHER_EMAIL)
        except Exception:
            pass
    return DEFAULT_TEACHER_EMAIL

# --- SMTP SERVER SETTINGS ---
# Note: To send actual emails through Gmail, you will need to generate a 
# 16-character 'App Password' in your Google Account security settings 
# (Google Account > Security > 2-Step Verification > App Passwords).
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "rlmorgan512@gmail.com"
SMTP_PASSWORD = "vtxd bznk oyan mzzi"  # Paste your 16-character Gmail App Password here

def send_grade_email(student_name: str, worksheet_title: str, score: float, total_problems: int, incorrect_count: int):
    """Sends an HTML formatted grade report to the teacher's email inbox."""
    recipient_email = get_teacher_email()
    
    if SMTP_PASSWORD == "your_app_password_here":
        print(f"[Email Notification Simulation]")
        print(f"Target Recipient: {recipient_email}")
        print(f"Student: {student_name} | Worksheet: '{worksheet_title}' | Score: {score:.1f}%\n")
        print("Note: To send real emails, replace 'your_app_password_here' in emailer.py with a Gmail App Password.")
        return

    subject = f"Soroban Grade Alert: {student_name} - {worksheet_title} ({score:.1f}%)"
    
    body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #1e293b; padding: 20px;">
            <div style="max-width: 500px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 12px; padding: 24px; background-color: #ffffff;">
                <h2 style="color: #4338ca; margin-top: 0;">Worksheet Submission Received</h2>
                <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 16px 0;" />
                <p style="margin: 8px 0;"><strong>Student Name:</strong> {student_name}</p>
                <p style="margin: 8px 0;"><strong>Worksheet Title:</strong> {worksheet_title}</p>
                <div style="margin: 20px 0; padding: 16px; background-color: #f8fafc; border-radius: 8px; text-align: center;">
                    <p style="margin: 0; text-transform: uppercase; font-size: 11px; font-weight: bold; color: #64748b; letter-spacing: 0.5px;">Final Score</p>
                    <p style="margin: 4px 0 0 0; font-size: 32px; font-weight: 900; color: {'#10b981' if score >= 80 else '#ef4444'};">{score:.1f}%</p>
                    <p style="margin: 4px 0 0 0; font-size: 13px; color: #64748b;">{total_problems - incorrect_count} / {total_problems} Correct ({incorrect_count} Missed)</p>
                </div>
                <p style="font-size: 12px; color: #94a3b8; text-align: center; margin-bottom: 0;">Automated Grade Report • Soroban Grader Platform</p>
            </div>
        </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = recipient_email
    msg.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SMTP_PASSWORD)
            server.sendmail(SENDER_EMAIL, recipient_email, msg.as_string())
        print(f"Grade alert successfully emailed to {recipient_email}")
    except Exception as e:
        print(f"Failed to send email alert: {e}") 