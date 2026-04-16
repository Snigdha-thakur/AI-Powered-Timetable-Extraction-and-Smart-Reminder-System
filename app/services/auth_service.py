import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
import bcrypt
from twilio.rest import Client as TwilioClient
from app.models.user import get_user, create_user
from app.services.supabase_client import _supabase as db
from app.utils import otp as otp_util
from app.utils.jwt_handler import create_access_token, create_refresh_token

load_dotenv(dotenv_path=".env.local", override=True)

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
print(f"[SMTP] Loaded user: {SMTP_USER}")

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_VERIFY_SID = os.getenv("TWILIO_VERIFY_SID", "")
twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def send_otp_email(email: str, otp: str):
    body = f"""Dear Student,

Your One-Time Password (OTP) for the AI-Powered Timetable & Smart Reminder System is:

    {otp}

This OTP is valid for 5 minutes. Do not share it with anyone.

If you did not request this, please ignore this email.

Regards,
Timetable App Team"""
    msg = MIMEText(body)
    msg["Subject"] = "Your OTP - Timetable App"
    msg["From"] = SMTP_USER
    msg["To"] = email
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, email, msg.as_string())
    print(f"[EMAIL] OTP sent to {email}")


def send_otp_sms(phone: str):
    twilio_client.verify.v2.services(TWILIO_VERIFY_SID).verifications.create(
        to=f"+91{phone}",
        channel="sms"
    )
    print(f"[SMS] OTP sent to {phone}")


def verify_twilio_otp(phone: str, otp: str) -> bool:
    result = twilio_client.verify.v2.services(TWILIO_VERIFY_SID).verification_checks.create(
        to=f"+91{phone}",
        code=otp
    )
    return result.status == "approved"


def initiate_email_signup(email: str):
    if get_user(email):
        raise ValueError("User already exists. Please login.")
    otp = otp_util.generate_otp(email)
    send_otp_email(email, otp)


def initiate_phone_signup(phone: str):
    if get_user(phone):
        raise ValueError("User already exists. Please login.")
    send_otp_sms(phone)


def verify_signup_otp(email_or_phone: str, otp: str):
    if "@" in email_or_phone:
        # Email OTP — use in-memory store
        if not otp_util.verify_otp(email_or_phone, otp):
            raise ValueError("Invalid or expired OTP")
        otp_util.consume_otp(email_or_phone)
    else:
        # Phone OTP — use Twilio Verify
        if not verify_twilio_otp(email_or_phone, otp):
            raise ValueError("Invalid or expired OTP")


def set_password_and_create_user(email_or_phone: str, password: str):
    existing = get_user(email_or_phone)
    if existing:
        raise ValueError("An account with this email or phone already exists. Please log in.")
    hashed = hash_password(password)
    email = email_or_phone if "@" in email_or_phone else None
    phone = email_or_phone if "@" not in email_or_phone else None
    user = create_user(email, phone, hashed)
    return user


def login_user(email_or_phone: str, password: str) -> dict:
    user = get_user(email_or_phone)
    if not user:
        raise ValueError("No account found with this email or phone. Please sign up.")
    if not user.get("is_verified"):
        raise ValueError("Your account is not verified. Please complete the signup process.")
    if not verify_password(password, user["password"]):
        raise ValueError("Incorrect password. Please try again.")
    access_token = create_access_token(user["id"])
    refresh_token = create_refresh_token(user["id"])
    return {
        "token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "id": user["id"],
            "email": user.get("email"),
            "phone": user.get("phone"),
        }
    }


def forgot_password_initiate(email_or_phone: str):
    user = get_user(email_or_phone)
    if not user:
        raise ValueError("No account found with this email or phone")
    if "@" in email_or_phone:
        otp = otp_util.generate_otp(f"reset:{email_or_phone}")
        send_otp_email(email_or_phone, otp)
    else:
        send_otp_sms(email_or_phone)


def forgot_password_verify(email_or_phone: str, otp: str):
    if "@" in email_or_phone:
        if not otp_util.verify_otp(f"reset:{email_or_phone}", otp):
            raise ValueError("Invalid or expired OTP")
        otp_util.consume_otp(f"reset:{email_or_phone}")
        # Mark as verified for reset
        otp_util._otp_store[f"reset_verified:{email_or_phone}"] = True
    else:
        if not verify_twilio_otp(email_or_phone, otp):
            raise ValueError("Invalid or expired OTP")
        otp_util._otp_store[f"reset_verified:{email_or_phone}"] = True


def forgot_password_reset(email_or_phone: str, password: str):
    key = f"reset_verified:{email_or_phone}"
    if not otp_util._otp_store.get(key):
        raise ValueError("OTP verification required. Please verify your OTP before resetting your password.")
    hashed = hash_password(password)
    if "@" in email_or_phone:
        db.table("users").update({"password": hashed}).eq("email", email_or_phone).execute()
    else:
        db.table("users").update({"password": hashed}).eq("phone", email_or_phone).execute()
    otp_util._otp_store.pop(key, None)
