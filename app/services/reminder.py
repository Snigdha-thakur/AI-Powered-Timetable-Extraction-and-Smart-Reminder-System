from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from app.services.supabase_client import get_reminders

scheduler = BackgroundScheduler()


def _check_reminders():
    """Runs every minute. Prints a reminder if current day+time matches."""
    now = datetime.now()
    current_day = now.strftime("%A")       # e.g. "Tuesday"
    current_time = now.strftime("%H:%M")   # e.g. "10:00"

    for reminder in get_reminders():
        # time stored as "HH:MM", day stored as full name
        reminder_time = reminder.get("time", "")[:5]  # trim seconds if any
        if reminder.get("day") == current_day and reminder_time == current_time:
            faculty = reminder.get('faculty', '')
            faculty_str = f" ({faculty})" if faculty else ""
            print(f"Reminder: {reminder['subject']}{faculty_str} at {reminder['time']}")


def start_scheduler():
    scheduler.add_job(_check_reminders, "interval", minutes=1, id="reminder_check")
    scheduler.start()


def stop_scheduler():
    scheduler.shutdown(wait=False)
