from pydantic import BaseModel, field_validator, model_validator
import re


class EmailInitiateRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def valid_email(cls, v):
        if not re.match(r"^[\w\.-]+@vitapstudent\.ac\.in$", v, re.I):
            raise ValueError("Must be a valid VIT-AP student email (@vitapstudent.ac.in)")
        return v


class PhoneInitiateRequest(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, v):
        if not re.fullmatch(r"\d{10}", v):
            raise ValueError("Phone must be exactly 10 digits")
        return v


class OTPVerifyRequest(BaseModel):
    email_or_phone: str
    otp: str


class SetPasswordRequest(BaseModel):
    email_or_phone: str
    password: str

    @field_validator("password")
    @classmethod
    def min_length(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")
        return v


class LoginRequest(BaseModel):
    email_or_phone: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordInitiateRequest(BaseModel):
    email_or_phone: str


class ForgotPasswordResetRequest(BaseModel):
    email_or_phone: str
    password: str

    @field_validator("password")
    @classmethod
    def strong_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")
        return v


class ProfileRequest(BaseModel):
    full_name: str
    registration_number: str
    phone: str
    department: str
    degree: str
    sem: str

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, v):
        if not re.fullmatch(r"\d{10}", v):
            raise ValueError("Phone must be exactly 10 digits")
        return v

    @field_validator("registration_number")
    @classmethod
    def valid_reg(cls, v):
        if not re.fullmatch(r"[0-9]{2}[A-Z]{3}[0-9]{4}", v.upper()):
            raise ValueError("Registration number must be like 22BCE8076")
        return v.upper()

    @field_validator("sem")
    @classmethod
    def valid_batch(cls, v):
        if not v.strip():
            raise ValueError("Sem cannot be empty")
        return v
