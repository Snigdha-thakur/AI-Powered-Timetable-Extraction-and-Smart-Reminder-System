from fastapi import APIRouter, HTTPException, Depends
from app.schemas.auth import (
    EmailInitiateRequest, PhoneInitiateRequest, OTPVerifyRequest,
    SetPasswordRequest, LoginRequest, RefreshRequest, ProfileRequest,
    ForgotPasswordInitiateRequest, ForgotPasswordResetRequest
)
from app.services import auth_service
from app.utils.jwt_handler import decode_token, create_access_token, revoke_refresh_token
from app.utils.dependencies import get_current_user
from app.models.user import update_profile, get_user_by_id

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/signup/initiate/email")
def signup_initiate_email(body: EmailInitiateRequest):
    try:
        auth_service.initiate_email_signup(body.email, body.role)
        return {"message": "OTP sent"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/signup/initiate/phone")
def signup_initiate_phone(body: PhoneInitiateRequest):
    try:
        auth_service.initiate_phone_signup(body.phone)
        return {"message": "OTP sent"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/signup/verify")
def signup_verify(body: OTPVerifyRequest):
    try:
        auth_service.verify_signup_otp(body.email_or_phone, body.otp)
        return {"message": "OTP verified"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/signup/set-password")
def signup_set_password(body: SetPasswordRequest):
    try:
        auth_service.set_password_and_create_user(body.email_or_phone, body.password)
        return {"message": "Account created successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
def login(body: LoginRequest):
    try:
        result = auth_service.login_user(body.email_or_phone, body.password)
        return {"message": "Login successful", **result}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/refresh")
def refresh_token(body: RefreshRequest):
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError("The provided token is not a valid refresh token.")
        revoke_refresh_token(body.refresh_token)
        new_access = create_access_token(payload["sub"])
        return {"token": new_access}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/profile/setup")
def setup_profile(body: ProfileRequest, user_id: str = Depends(get_current_user)):
    try:
        profile = update_profile(
            user_id=user_id,
            full_name=body.full_name,
            registration_number=body.registration_number,
            employee_id=body.employee_id,
            phone=body.phone,
            department=body.department,
            degree=body.degree,
            batch=body.sem,
        )
        return {"message": "Profile updated successfully", "profile": profile}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/profile")
def get_profile(user_id: str = Depends(get_current_user)):
    profile = get_user_by_id(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.post("/forgot-password/initiate")
def forgot_password_initiate(body: ForgotPasswordInitiateRequest):
    try:
        auth_service.forgot_password_initiate(body.email_or_phone, body.role)
        return {"message": "OTP sent"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/forgot-password/verify")
def forgot_password_verify(body: OTPVerifyRequest):
    try:
        auth_service.forgot_password_verify(body.email_or_phone, body.otp)
        return {"message": "OTP verified"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/forgot-password/reset")
def forgot_password_reset(body: ForgotPasswordResetRequest):
    try:
        auth_service.forgot_password_reset(body.email_or_phone, body.password)
        return {"message": "Password reset successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
