# Timetable Extraction System — Backend API

A FastAPI backend that accepts OCR-like timetable data, parses it into structured JSON, stores it in Supabase, and provides reminder functionality.

---

## Tech Stack

- **FastAPI** — API framework
- **Supabase** — PostgreSQL database
- **APScheduler** — background reminder scheduler
- **Pydantic** — request/response validation
- **Python 3.11+**

---

## Project Structure

```
SDP Project/
├── app/
│   ├── main.py
│   ├── routes/
│   │   └── timetable.py
│   ├── services/
│   │   ├── parser.py
│   │   ├── supabase_client.py
│   │   └── reminder.py
│   └── models/
│       └── schemas.py
├── schema.sql
├── requirements.txt
└── .env.local
```

---

## Setup

**1. Install dependencies**
```bash
pip install -r requirements.txt
```

**2. Configure environment — `.env.local`**
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-public-key
```

**3. Create database tables**

Run `schema.sql` in your Supabase SQL Editor.

**4. Start the server**
```bash
uvicorn app.main:app --reload
```

**5. Open interactive API docs**
```
http://127.0.0.1:8000/docs
```

---

## Raw Data Format (Input Convention)

Each row in `raw_data` follows this column layout:

| Index | 0   | 1    | 2        | 3        | 4        | 5        | ... |
|-------|-----|------|----------|----------|----------|----------|-----|
| Value | Day | Type | Subject1 | Faculty1 | Subject2 | Faculty2 | ... |

- **Day** — full weekday name e.g. `"Monday"`, `"Tuesday"`
- **Type** — `"THEORY"` or `"LAB"`
- **Subject + Faculty** — separate paired columns from index 2 onward
- Use `"-"` or `"--"` to mark empty slots

Each subject+faculty pair maps to a time slot in order:
```
Pair (col2, col3)  →  08:00-08:50
Pair (col4, col5)  →  09:00-09:50
Pair (col6, col7)  →  10:00-10:50
... and so on up to 19:00-19:50
```

---

## API Endpoints

> Base URL: `http://127.0.0.1:8000`
> Header for all POST requests: `Content-Type: application/json`

---

### 1. POST `/upload`

Upload raw OCR timetable data. Parses it into structured JSON and stores both raw and parsed data in Supabase.

**Postman Setup**
```
Method  : POST
URL     : http://127.0.0.1:8000/upload
Headers : Content-Type: application/json
Body    : raw → JSON
```

**Request Body**

```json
{
  "user_id": "student_001",
  "raw_data": [
    ["Monday", "THEORY", "DBMS",   "Dr. Shah",  "OS",   "Dr. Rao",  "-", "-", "CN",   "Dr. Mehta"],
    ["Monday", "LAB",    "DBMS-L", "Dr. Shah",  "-",    "-",        "-", "-", "OS-L", "Dr. Rao"  ],
    ["Tuesday","THEORY", "TEE1",   "Dr. Kumar", "TEE2", "Dr. Nair", "-", "-", "FLAT", "Dr. Joshi"]
  ]
}
```

| Field      | Type            | Required | Description                                         |
|------------|-----------------|----------|-----------------------------------------------------|
| `user_id`  | string          | ✅       | Unique identifier for the student                   |
| `raw_data` | array of arrays | ✅       | OCR rows — each row is `[Day, Type, Subject, Faculty, ...]` |

**Response — 200 OK**

```json
{
  "message": "Timetable stored",
  "timetable_id": "b3f1c2d4-e5a6-7890-bcde-f01234567890"
}
```

| Field          | Type   | Description                              |
|----------------|--------|------------------------------------------|
| `message`      | string | Confirmation message                     |
| `timetable_id` | string | UUID of the stored timetable — save this |

**Response — 400 Bad Request**

```json
{
  "detail": "No valid timetable data found in input."
}
```

**Response — 422 Unprocessable Entity** *(missing or wrong field types)*

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "user_id"],
      "msg": "Field required"
    }
  ]
}
```

---

### 2. GET `/timetable/{timetable_id}`

Fetch a stored timetable by its ID. Returns the structured parsed JSON.

**Postman Setup**
```
Method  : GET
URL     : http://127.0.0.1:8000/timetable/b3f1c2d4-e5a6-7890-bcde-f01234567890
Headers : (none required)
Body    : (none)
```

**URL Parameter**

| Parameter      | Type   | Required | Description                                    |
|----------------|--------|----------|------------------------------------------------|
| `timetable_id` | string | ✅       | UUID returned from POST /upload                |

**Response — 200 OK**

```json
{
  "Monday": [
    {
      "type": "THEORY",
      "time": "08:00-08:50",
      "subject": "DBMS",
      "faculty": "Dr. Shah"
    },
    {
      "type": "THEORY",
      "time": "09:00-09:50",
      "subject": "OS",
      "faculty": "Dr. Rao"
    },
    {
      "type": "THEORY",
      "time": "11:00-11:50",
      "subject": "CN",
      "faculty": "Dr. Mehta"
    },
    {
      "type": "LAB",
      "time": "08:00-08:50",
      "subject": "DBMS-L",
      "faculty": "Dr. Shah"
    },
    {
      "type": "LAB",
      "time": "11:00-11:50",
      "subject": "OS-L",
      "faculty": "Dr. Rao"
    }
  ],
  "Tuesday": [
    {
      "type": "THEORY",
      "time": "08:00-08:50",
      "subject": "TEE1",
      "faculty": "Dr. Kumar"
    },
    {
      "type": "THEORY",
      "time": "09:00-09:50",
      "subject": "TEE2",
      "faculty": "Dr. Nair"
    },
    {
      "type": "THEORY",
      "time": "11:00-11:50",
      "subject": "FLAT",
      "faculty": "Dr. Joshi"
    }
  ]
}
```

| Field     | Type   | Description                     |
|-----------|--------|---------------------------------|
| `type`    | string | `"THEORY"` or `"LAB"`          |
| `time`    | string | Time slot e.g. `"08:00-08:50"` |
| `subject` | string | Subject code e.g. `"DBMS"`     |
| `faculty` | string | Faculty name e.g. `"Dr. Shah"` |

**Response — 404 Not Found**

```json
{
  "detail": "Timetable not found."
}
```

---

### 3. POST `/reminder`

Create a reminder for a specific class. The scheduler checks every minute and prints an alert when the day and time match.

**Postman Setup**
```
Method  : POST
URL     : http://127.0.0.1:8000/reminder
Headers : Content-Type: application/json
Body    : raw → JSON
```

**Request Body**

```json
{
  "timetable_id": "b3f1c2d4-e5a6-7890-bcde-f01234567890",
  "day": "Monday",
  "time": "09:00",
  "subject": "DBMS",
  "faculty": "Dr. Shah"
}
```

| Field          | Type   | Required | Description                                    |
|----------------|--------|----------|------------------------------------------------|
| `timetable_id` | string | ✅       | UUID from POST /upload                         |
| `day`          | string | ✅       | Full weekday name e.g. `"Monday"`              |
| `time`         | string | ✅       | Time in `HH:MM` format e.g. `"09:00"`         |
| `subject`      | string | ✅       | Subject name e.g. `"DBMS"`                    |
| `faculty`      | string | ❌       | Faculty name (optional) — defaults to `""`    |

**Response — 200 OK**

```json
{
  "message": "Reminder created",
  "reminder_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

| Field         | Type   | Description                  |
|---------------|--------|------------------------------|
| `message`     | string | Confirmation message         |
| `reminder_id` | string | UUID of the created reminder |

**Response — 404 Not Found** *(timetable_id does not exist)*

```json
{
  "detail": "Timetable not found."
}
```

**Response — 422 Unprocessable Entity** *(missing required fields)*

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "day"],
      "msg": "Field required"
    }
  ]
}
```

---

## Postman Test Order

```
Step 1 → POST /upload        → copy timetable_id from response
Step 2 → GET  /timetable/id  → paste timetable_id in URL, verify parsed data
Step 3 → POST /reminder      → paste timetable_id in body, create reminder
```

---

## Reminder Scheduler

APScheduler runs a background job **every minute**. When the current day and time match a stored reminder, it prints to the console:

```
Reminder: DBMS (Dr. Shah) at 09:00
Reminder: OS at 10:00
```

- Starts automatically when the server starts
- Stops cleanly when the server shuts down

---

## Database Schema

### timetables

| Column       | Type        | Description                 |
|--------------|-------------|-----------------------------|
| `id`         | uuid (PK)   | Auto-generated UUID         |
| `user_id`    | text        | Student/user identifier     |
| `data`       | jsonb       | Parsed structured timetable |
| `raw_data`   | jsonb       | Original OCR input rows     |
| `created_at` | timestamptz | Auto-set on insert          |

### reminders

| Column         | Type        | Description                         |
|----------------|-------------|-------------------------------------|
| `id`           | uuid (PK)   | Auto-generated UUID                 |
| `timetable_id` | uuid (FK)   | References `timetables(id)`         |
| `day`          | text        | Weekday name                        |
| `time`         | text        | Time in `HH:MM` format             |
| `subject`      | text        | Subject name                        |
| `faculty`      | text        | Faculty name (default empty string) |
| `created_at`   | timestamptz | Auto-set on insert                  |

---

## Time Slots Reference

| Slot | Time        | Slot | Time        |
|------|-------------|------|-------------|
| 0    | 08:00-08:50 | 6    | 14:00-14:50 |
| 1    | 09:00-09:50 | 7    | 15:00-15:50 |
| 2    | 10:00-10:50 | 8    | 16:00-16:50 |
| 3    | 11:00-11:50 | 9    | 17:00-17:50 |
| 4    | 12:00-12:50 | 10   | 18:00-18:50 |
| 5    | 13:00-13:50 | 11   | 19:00-19:50 |

---

## Ignored Values

The parser skips these and does not create entries for them:

