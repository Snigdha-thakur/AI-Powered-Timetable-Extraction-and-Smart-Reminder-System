import random
import time
from datetime import datetime, timezone, timedelta
from app.services.supabase_client import _supabase as db

TABLE = "otps"
OTP_EXPIRY_SECONDS = 300  # 5 minutes
MAX_RESEND_INTERVAL = 60  # 1 minute between resends

# Still used for reset_verified flags (not worth a DB table)
_otp_store: dict = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def generate_otp(key: str) -> str:
    existing = db.table(TABLE).select("issued_at").eq("key", key).maybe_single().execute()
    if existing and existing.data:
        issued_at = datetime.fromisoformat(existing.data["issued_at"])
        if issued_at.tzinfo is None:
            issued_at = issued_at.replace(tzinfo=timezone.utc)
        if (_now() - issued_at).total_seconds() < MAX_RESEND_INTERVAL:
            raise ValueError("Please wait before requesting a new OTP")

    otp = str(random.randint(100000, 999999))
    now = _now()
    db.table(TABLE).upsert({
        "key":        key,
        "otp":        otp,
        "expires_at": (now + timedelta(seconds=OTP_EXPIRY_SECONDS)).isoformat(),
        "issued_at":  now.isoformat(),
        "attempts":   0,
    }).execute()
    return otp


def verify_otp(key: str, otp: str) -> bool:
    row = db.table(TABLE).select("*").eq("key", key).maybe_single().execute()
    if not row or not row.data:
        return False

    record = row.data
    expires_at = datetime.fromisoformat(record["expires_at"])
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if _now() > expires_at:
        db.table(TABLE).delete().eq("key", key).execute()
        return False

    attempts = record["attempts"] + 1
    if attempts > 5:
        db.table(TABLE).delete().eq("key", key).execute()
        raise ValueError("Too many failed attempts. Request a new OTP")

    db.table(TABLE).update({"attempts": attempts}).eq("key", key).execute()

    return record["otp"] == otp


def consume_otp(key: str):
    db.table(TABLE).delete().eq("key", key).execute()
