# Timetable Extraction System — Backend API

## Setup & Run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Docs: `http://127.0.0.1:8000/docs`

---

## Supabase SQL

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
  venue        TEXT,
  created_at   TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Auth Flow

```
Step 1 → POST /auth/signup/initiate/email   OR   POST /auth/signup/initiate/phone
Step 2 → POST /auth/signup/verify
Step 3 → POST /auth/signup/set-password
Step 4 → POST /auth/login                        → save token + refresh_token
Step 5 → POST /auth/profile/setup
Step 6 → GET  /auth/profile
Step 7 → POST /auth/refresh                      (when token expires)
```

## Forgot Password Flow

```
Step 1 → POST /auth/forgot-password/initiate
Step 2 → POST /auth/forgot-password/verify
Step 3 → POST /auth/forgot-password/reset
```

## Timetable Flow

```
Step 1 → POST /upload-schedule                                                              → upload image, get timetable_id
Step 2 → GET  /timetable/{timetable_id}                                                     → view extracted timetable
Step 3 → GET  /timetable/{timetable_id}/calendar-view?start_date=...&end_date=...          → display on website calendar
Step 4 → GET  /timetable/{timetable_id}/add-to-google-calendar?start_date=...&end_date=... → one-click add all to Google Calendar
Step 4b→ DELETE /timetable/{timetable_id}/remove-from-google-calendar                      → remove all timetable events from Google Calendar
Step 5 → POST /reminder                                                                     → (optional) register for email alerts
```

> All timetable and reminder endpoints require `Authorization: Bearer <token>` header.

---

## POST `/auth/signup/initiate/email`

```
POST http://127.0.0.1:8000/auth/signup/initiate/email
Content-Type: application/json
```

**Body**
```json
{ "email": "user@example.com" }
```
**Response**
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
**Response**
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
{ "email_or_phone": "user@example.com", "otp": "482910" }
```
**Response**
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
{ "email_or_phone": "user@example.com", "password": "mypassword" }
```
**Response**
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
{ "email_or_phone": "user@example.com", "password": "mypassword" }
```
**Response**
```json
{
  "message": "Login successful",
  "token": "<access_token>",
  "refresh_token": "<refresh_token>",
  "user": { "id": "UI-A1B2C3", "email": "user@example.com", "phone": null }
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
**Response**
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
**Response**
```json
{
  "message": "Profile updated successfully",
  "profile": {
    "id": "UI-A1B2C3",
    "email": "user@example.com",
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

**Response**
```json
{
  "id": "UI-A1B2C3",
  "email": "user@example.com",
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
{ "email_or_phone": "user@example.com" }
```
**Response**
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
{ "email_or_phone": "user@example.com", "otp": "482910" }
```
**Response**
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
{ "email_or_phone": "user@example.com", "password": "NewPass@123" }
```
**Response**
```json
{ "message": "Password reset successfully" }
```

---

## POST `/upload-schedule`

```
POST http://127.0.0.1:8000/upload-schedule
Authorization: Bearer <token>
Content-Type: multipart/form-data
```

**Body**
```
schedule_image: <image file>
```
**Response**
```json
{ "message": "Timetable stored", "timetable_id": "TT-OJQW40" }
```

---

## GET `/timetable/{timetable_id}`

```
GET http://127.0.0.1:8000/timetable/TT-OJQW40
```

**Response**
```json
{
  "Friday": [
    { "type": "THEORY", "time": "09:00-09:50", "course_code": "MAT2003", "venue": "228-C8", "slot": "A1" },
    { "type": "THEORY", "time": "14:00-14:50", "course_code": "CSE3008", "venue": "324-C8", "slot": "C1" }
  ],
  "Tuesday": [
    { "type": "THEORY", "time": "09:00-09:50", "course_code": "MAT2005", "venue": "230-C8", "slot": "B1" }
  ]
}
```

---

## GET `/timetable/{timetable_id}/calendar-view`

Returns all classes as a flat sorted list for displaying on a website calendar. `start_date` and `end_date` are required — returns one event per actual date occurrence within the semester.

```
GET http://127.0.0.1:8000/timetable/TT-OJQW40/calendar-view?start_date=2026-01-01&end_date=2026-05-31
```

**Query Params**
| Param | Type | Required | Description |
|---|---|---|---|
| `start_date` | `YYYY-MM-DD` | Yes | Semester start date |
| `end_date` | `YYYY-MM-DD` | Yes | Semester end date |

**Response**
```json
{
  "timetable_id": "TT-OJQW40",
  "start_date": "2026-01-01",
  "end_date": "2026-05-31",
  "events": [
    {
      "day":         "Monday",
      "day_index":   0,
      "date":        "2026-01-05",
      "time":        "09:00-09:50",
      "time_start":  "09:00",
      "time_end":    "09:50",
      "course_code": "MAT2003",
      "type":        "THEORY",
      "slot":        "A1",
      "venue":       "228-C8"
    }
  ]
}
```

> Events sorted by date then time. Each event has an actual `date` field — use this to place events on a calendar grid.

---

## GET `/timetable/{timetable_id}/add-to-google-calendar`

Redirects user to Google login. After they authorize, all timetable classes are added directly to their Google Calendar with **15-minute popup reminders**. `start_date` and `end_date` are required — adds one event per class occurrence within the semester.

```
GET http://127.0.0.1:8000/timetable/TT-OJQW40/add-to-google-calendar?start_date=2026-01-01&end_date=2026-05-31
```

**Query Params**
| Param | Type | Required | Description |
|---|---|---|---|
| `start_date` | `YYYY-MM-DD` | Yes | Semester start date |
| `end_date` | `YYYY-MM-DD` | Yes | Semester end date |

> Frontend: `window.location.href = 'http://127.0.0.1:8000/timetable/TT-OJQW40/add-to-google-calendar?start_date=2026-01-01&end_date=2026-05-31'`
> After Google login, user is redirected back to `http://localhost:3000?calendar_sync=success&events=80` (80 = total events added)

---

## DELETE `/timetable/{timetable_id}/remove-from-google-calendar`

Returns a Google OAuth URL. Redirect the user to it — after they authorize, all timetable events (tagged with this `timetable_id`) are deleted from their Google Calendar.

```
DELETE http://127.0.0.1:8000/timetable/TT-OJQW40/remove-from-google-calendar
Authorization: Bearer <token>
```

**Response**
```json
{ "auth_url": "https://accounts.google.com/o/oauth2/auth?..." }
```

> Frontend: `window.location.href = response.auth_url`
> After Google login, user is redirected back to `http://localhost:3000?calendar_sync=deleted&events=80` (80 = total events deleted)

> Note: Only events added **after** this feature was deployed will be deleted (events must have been tagged with `timetable_id` at insert time).

---

## GET `/auth/google/callback`

Google calls this automatically after user logs in. Do not call this manually.

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
  "timetable_id": "TT-OJQW40",
  "day": "Friday",
  "time": "09:00",
  "subject": "MAT2003",
  "faculty": "Dr. Shah",
  "venue": "228-C8"
}
```
**Response**
```json
{ "message": "Reminder created", "reminder_id": "RM-A1B2C3" }
```

> Email sent to the user's registered address 15 minutes before the class every week.
