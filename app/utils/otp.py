import random
import time

# { email_or_phone: {"otp": str, "expires_at": float, "attempts": int, "issued_at": float} }
_otp_store: dict[str, dict] = {}

OTP_EXPIRY_SECONDS = 300  # 5 minutes
MAX_RESEND_INTERVAL = 60  # 1 minute between resends


def generate_otp(key: str) -> str:
    now = time.time()
    existing = _otp_store.get(key)
    if existing and (now - existing["issued_at"]) < MAX_RESEND_INTERVAL:
        raise ValueError("Please wait before requesting a new OTP")
    otp = str(random.randint(100000, 999999))
    _otp_store[key] = {"otp": otp, "expires_at": now + OTP_EXPIRY_SECONDS, "attempts": 0, "issued_at": now}
    return otp


def verify_otp(key: str, otp: str) -> bool:
    record = _otp_store.get(key)
    if not record:
        return False
    if time.time() > record["expires_at"]:
        _otp_store.pop(key, None)
        return False
    record["attempts"] += 1
    if record["attempts"] > 5:
        _otp_store.pop(key, None)
        raise ValueError("Too many failed attempts. Request a new OTP")
    if record["otp"] != otp:
        return False
    return True


def consume_otp(key: str):
    _otp_store.pop(key, None)
