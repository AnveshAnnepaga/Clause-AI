import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_otp_email(to_email: str, otp: str) -> bool:
    """Send OTP code via SMTP to the specified email."""
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")

    if not smtp_user or not smtp_pass:
        print("SMTP_USER or SMTP_PASS not set in environment variables. Falling back to mock email.")
        print(f"--- MOCK EMAIL --- Sent OTP {otp} to {to_email}")
        return True

    msg = MIMEMultipart()
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg["Subject"] = "Your Verification Code for Clause-AI"

    body = f"""Hello,

Your verification code for Clause-AI is: {otp}

This code will expire in 5 minutes.

If you did not request this code, please ignore this email.

Best regards,
Clause-AI Team
"""
    msg.attach(MIMEText(body, "plain"))

    try:
        # Start SMTP session
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Secure the connection
        server.login(smtp_user, smtp_pass)
        
        # Send email
        server.sendmail(smtp_user, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send email to {to_email}: {str(e)}")
        return False
