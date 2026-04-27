import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from app.services.supabase_client import get_reminders, get_user_email_by_timetable_id

scheduler = BackgroundScheduler()


def _send_email(to_email: str, subject: str, body: str):
    msg = MIMEText(body, "html")
    msg["Subject"] = subject
    msg["From"] = os.environ["SMTP_USER"]
    msg["To"] = to_email
    with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ["SMTP_PORT"])) as s:
        s.starttls()
        s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        s.sendmail(os.environ["SMTP_USER"], to_email, msg.as_string())


def _check_reminders():
    """Runs every minute. Sends email 1 minute before the class."""
    # Target: class starting 1 minute from now
    target = datetime.now() + timedelta(minutes=15)
    current_day = target.strftime("%A")
    target_time = target.strftime("%H:%M")

    for reminder in get_reminders():
        reminder_time = reminder.get("time", "")[:5]
        if reminder.get("day") != current_day or reminder_time != target_time:
            continue

        subject = reminder["subject"]
        faculty = reminder.get("faculty", "")
        venue = reminder.get("venue", "")
        time_str = reminder["time"]

        to_email = get_user_email_by_timetable_id(reminder["timetable_id"])
        if not to_email:
            print(f"[Reminder] No email found for timetable {reminder['timetable_id']}")
            continue

        body = f"""
        <h3>⏰ Class Reminder — Starting in 15 Minutes!</h3>
        <p><b>Subject:</b> {subject}</p>
        <p><b>Time:</b> {time_str}</p>
        {f'<p><b>Faculty:</b> {faculty}</p>' if faculty else ''}
        {f'<p><b>Venue:</b> {venue}</p>' if venue else ''}
        """
        try:
            _send_email(to_email, f"Reminder: {subject} starts in 15 mins", body)
            print(f"[Reminder] Email sent to {to_email} for {subject} at {time_str}")
        except Exception as e:
            print(f"[Reminder] Failed to send email: {e}")


def start_scheduler():
    scheduler.add_job(_check_reminders, "interval", minutes=1, id="reminder_check")
    scheduler.start()


def stop_scheduler():
    scheduler.shutdown(wait=False)
