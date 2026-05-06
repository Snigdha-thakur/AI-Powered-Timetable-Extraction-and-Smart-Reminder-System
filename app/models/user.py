import random
import string
from app.services.supabase_client import _supabase as db

TABLE = "users"


def generate_user_id() -> str:
    chars = string.ascii_uppercase + string.digits
    suffix = "".join(random.choices(chars, k=6))
    return f"UI-{suffix}"


def get_user(email_or_phone: str):
    if "@" in email_or_phone:
        res = db.table(TABLE).select("*").eq("email", email_or_phone).execute()
    else:
        res = db.table(TABLE).select("*").eq("phone", email_or_phone).execute()
    return res.data[0] if res.data else None


def get_user_by_id(user_id: str):
    res = db.table(TABLE).select("id,email,phone,full_name,registration_number,employee_id,department,degree,sem").eq("id", user_id).execute()
    return res.data[0] if res.data else None


def update_profile(user_id: str, full_name: str, registration_number: str, employee_id: str, phone: str, department: str, degree: str, batch: str):
    payload = {
        "full_name": full_name,
        "department": department,
        "sem": batch,
    }
    if phone:
        payload["phone"] = phone
    if registration_number:
        payload["registration_number"] = registration_number.upper()
    if employee_id:
        payload["employee_id"] = employee_id
    if degree:
        payload["degree"] = degree
    res = db.table(TABLE).update(payload).eq("id", user_id).execute()
    data = res.data[0] if res.data else None
    if data:
        data.pop("password", None)
        data.pop("is_verified", None)
        data.pop("created_at", None)
    return data


def create_user(email: str | None, phone: str | None, hashed_password: str):
    payload = {
        "id": generate_user_id(),
        "email": email,
        "phone": phone,
        "password": hashed_password,
        "is_verified": True,
    }
    res = db.table(TABLE).insert(payload).execute()
    return res.data[0] if res.data else None
