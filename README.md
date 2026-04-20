# Timetable Extraction System — Backend API

## Setup & Run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Docs: `http://127.0.0.1:8000/docs`

---

## Supabase SQL

Run in Supabase SQL Editor before starting:

```sql
CREATE TABLE users (
  id                  TEXT PRIMARY KEY,
  email               TEXT UNIQUE,
  phone               TEXT UNIQUE,
  password            TEXT NOT NULL,
  is_verified         BOOLEAN DEFAULT TRUE,
  full_name           TEXT,
  registration_number TEXT UNIQUE,
  department          TEXT,
  degree              TEXT,
  sem                 TEXT,
  created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE timetables (
  id         TEXT PRIMARY KEY,
  user_id    TEXT REFERENCES users(id),
  data       JSONB,
  raw_data   JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE reminders (
  id           TEXT PRIMARY KEY,
  timetable_id TEXT REFERENCES timetables(id),
  day          TEXT,
  time         TEXT,
  subject      TEXT,
  faculty      TEXT,
  created_at   TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Auth Test Order

```
Step 1 → POST /auth/signup/initiate/email   OR   POST /auth/signup/initiate/phone
Step 2 → POST /auth/signup/verify
Step 3 → POST /auth/signup/set-password
Step 4 → POST /auth/login
Step 5 → POST /auth/profile/setup
Step 6 → GET  /auth/profile
Step 7 → POST /auth/refresh  (optional)
```

---

## Forgot Password Flow

```
Step 1 → POST /auth/forgot-password/initiate
Step 2 → POST /auth/forgot-password/verify
Step 3 → POST /auth/forgot-password/reset
```

---

## POST `/auth/signup/initiate/email`

```
POST http://127.0.0.1:8000/auth/signup/initiate/email
Content-Type: application/json
```

**Body**
```json
{ "email": "snigdha.22bce8076@vitapstudent.ac.in" }
```

**Response 200**
```json
{ "message": "OTP sent" }
```

---

## POST `/auth/signup/initiate/phone`

```
POST http://127.0.0.1:8000/auth/signup/initiate/phone
Content-Type: application/json
```

**Body**
```json
{ "phone": "9876543210" }
```

**Response 200**
```json
{ "message": "OTP sent" }
```

---

## POST `/auth/signup/verify`

```
POST http://127.0.0.1:8000/auth/signup/verify
Content-Type: application/json
```

**Body**
```json
{
  "email_or_phone": "snigdha.22bce8076@vitapstudent.ac.in",
  "otp": "482910"
}
```

**Response 200**
```json
{ "message": "OTP verified" }
```

---

## POST `/auth/signup/set-password`

```
POST http://127.0.0.1:8000/auth/signup/set-password
Content-Type: application/json
```

**Body**
```json
{
  "email_or_phone": "snigdha.22bce8076@vitapstudent.ac.in",
  "password": "mypassword"
}
```

**Response 200**
```json
{ "message": "Account created successfully" }
```

---

## POST `/auth/login`

```
POST http://127.0.0.1:8000/auth/login
Content-Type: application/json
```

**Body**
```json
{
  "email_or_phone": "snigdha.22bce8076@vitapstudent.ac.in",
  "password": "NewPass@123"
}
```

**Response 200**
```json
{
  "message": "Login successful",
  "token": "<access_token>",
  "refresh_token": "<refresh_token>",
  "user": {
    "id": "uuid",
    "email": "snigdha.22bce8076@vitapstudent.ac.in",
    "phone": null
  }
}
```

---

## POST `/auth/refresh`

```
POST http://127.0.0.1:8000/auth/refresh
Content-Type: application/json
```

**Body**
```json
{ "refresh_token": "<refresh_token>" }
```

**Response 200**
```json
{ "token": "<new_access_token>" }
```

---

## POST `/auth/profile/setup`

```
POST http://127.0.0.1:8000/auth/profile/setup
Authorization: Bearer <token>
Content-Type: application/json
```

**Body**
```json
{
  "full_name": "Snigdha",
  "registration_number": "22BCE8076",
  "phone": "7070970266",
  "department": "Scope",
  "degree": "btech",
  "sem": "Fall Sem 2026-2027"
}
```

**Response 200**
```json
{
  "message": "Profile updated successfully",
  "profile": {
    "id": "UI-A1B2C3",
    "email": "snigdha.22bce8076@vitapstudent.ac.in",
    "phone": "7070970266",
    "full_name": "Snigdha",
    "registration_number": "22BCE8076",
    "department": "Scope",
    "degree": "btech",
    "sem": "Fall Sem 2026-2027"
  }
}
```

---

## GET `/auth/profile`

```
GET http://127.0.0.1:8000/auth/profile
Authorization: Bearer <token>
```

**Response 200**
```json
{
  "id": "UI-A1B2C3",
  "email": "snigdha.22bce8076@vitapstudent.ac.in",
  "phone": "7070970266",
  "full_name": "Snigdha",
  "registration_number": "22BCE8076",
  "department": "Scope",
  "degree": "btech",
  "sem": "Fall Sem 2026-2027"
}
```

---

## POST `/auth/forgot-password/initiate`

```
POST http://127.0.0.1:8000/auth/forgot-password/initiate
Content-Type: application/json
```

**Body**
```json
{ "email_or_phone": "snigdha.22bce8076@vitapstudent.ac.in" }
```

**Response 200**
```json
{ "message": "OTP sent" }
```

---

## POST `/auth/forgot-password/verify`

```
POST http://127.0.0.1:8000/auth/forgot-password/verify
Content-Type: application/json
```

**Body**
```json
{ "email_or_phone": "snigdha.22bce8076@vitapstudent.ac.in", "otp": "482910" }
```

**Response 200**
```json
{ "message": "OTP verified" }
```

---

## POST `/auth/forgot-password/reset`

```
POST http://127.0.0.1:8000/auth/forgot-password/reset
Content-Type: application/json
```

**Body**
```json
{ "email_or_phone": "snigdha.22bce8076@vitapstudent.ac.in", "password": "NewPass@123" }
```

**Response 200**
```json
{ "message": "Password reset successfully" }
```

---

## Timetable Test Order

```
Step 1 → POST /auth/login    → copy token from response
Step 2 → POST /upload        → paste token in Authorization header, copy timetable_id
Step 3 → GET  /timetable/id  → paste timetable_id in URL
Step 4 → POST /reminder      → paste token in Authorization header, paste timetable_id in body
```

> All timetable and reminder endpoints require `Authorization: Bearer <token>` header.

---

## POST `/upload`

```
POST http://127.0.0.1:8000/upload
Authorization: Bearer <token>
Content-Type: application/json
```

**Body**
```json
{
  "raw_data": [
    ["Monday", "THEORY", "DBMS",   "Dr. Shah",  "OS",   "Dr. Rao",  "-", "-", "CN",   "Dr. Mehta"],
    ["Monday", "LAB",    "DBMS-L", "Dr. Shah",  "-",    "-",        "-", "-", "OS-L", "Dr. Rao"  ],
    ["Tuesday","THEORY", "TEE1",   "Dr. Kumar", "TEE2", "Dr. Nair", "-", "-", "FLAT", "Dr. Joshi"]
  ]
}
```

**Response 200**
```json
{
  "message": "Timetable stored",
  "timetable_id": "TT-A1B2C3",
  "user_id": "UI-A1B2C3"
}
```

---

## GET `/timetable/{timetable_id}`

```
GET http://127.0.0.1:8000/timetable/TT-A1B2C3
```

**Response 200**
```json
{
  "Monday": [
    { "type": "THEORY", "time": "08:00-08:50", "subject": "DBMS",   "faculty": "Dr. Shah"  },
    { "type": "THEORY", "time": "09:00-09:50", "subject": "OS",     "faculty": "Dr. Rao"   },
    { "type": "THEORY", "time": "11:00-11:50", "subject": "CN",     "faculty": "Dr. Mehta" },
    { "type": "LAB",    "time": "08:00-08:50", "subject": "DBMS-L", "faculty": "Dr. Shah"  },
    { "type": "LAB",    "time": "11:00-11:50", "subject": "OS-L",   "faculty": "Dr. Rao"   }
  ],
  "Tuesday": [
    { "type": "THEORY", "time": "08:00-08:50", "subject": "TEE1", "faculty": "Dr. Kumar" },
    { "type": "THEORY", "time": "09:00-09:50", "subject": "TEE2", "faculty": "Dr. Nair"  },
    { "type": "THEORY", "time": "11:00-11:50", "subject": "FLAT", "faculty": "Dr. Joshi" }
  ]
}
```

---

## POST `/reminder`

```
POST http://127.0.0.1:8000/reminder
Authorization: Bearer <token>
Content-Type: application/json
```

**Body**
```json
{
  "timetable_id": "TT-A1B2C3",
  "day": "Monday",
  "time": "09:00",
  "subject": "DBMS",
  "faculty": "Dr. Shah"
}
```

**Response 200**
```json
{
  "message": "Reminder created",
  "reminder_id": "RM-A1B2C3"
}
```
