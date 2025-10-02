from __future__ import annotations

from datetime import datetime
from typing import Any

from dateutil.parser import parse as parse_datetime
from flask import Flask, redirect, render_template, request, url_for

from .database import Base, engine, session_scope
from .models import BodyMetric, CalendarEvent, Exercise, Reminder, WorkoutSession
from .recommendations import highlight_progress, recommend_next_focus


app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True


Base.metadata.create_all(bind=engine)


@app.route("/")
def dashboard() -> str:
    with session_scope() as session:
        sessions = session.query(WorkoutSession).order_by(WorkoutSession.session_date.desc()).limit(10).all()
        events = (
            session.query(CalendarEvent)
            .filter(CalendarEvent.start_datetime >= datetime.now())
            .order_by(CalendarEvent.start_datetime.asc())
            .limit(5)
            .all()
        )
        reminders = (
            session.query(Reminder)
            .filter(Reminder.completed.is_(False))
            .order_by(Reminder.due_date.asc())
            .limit(5)
            .all()
        )
        exercises = session.query(Exercise).join(WorkoutSession).order_by(WorkoutSession.session_date.desc()).all()

        recommendations = recommend_next_focus(sessions)
        progress_notes = highlight_progress(exercises)

    return render_template(
        "dashboard.html",
        sessions=sessions,
        events=events,
        reminders=reminders,
        recommendations=recommendations,
        progress_notes=progress_notes,
    )


@app.route("/workouts", methods=["GET", "POST"])
def workouts() -> str:
    if request.method == "POST":
        session_date = datetime.strptime(request.form["session_date"], "%Y-%m-%d").date()
        focus = request.form.get("focus", "General").strip() or "General"
        notes = request.form.get("notes") or None
        with session_scope() as session:
            workout = WorkoutSession(session_date=session_date, focus=focus, notes=notes)
            session.add(workout)
        return redirect(url_for("workouts"))

    with session_scope() as session:
        workouts_list = session.query(WorkoutSession).order_by(WorkoutSession.session_date.desc()).all()
    return render_template("workouts.html", workouts=workouts_list)


@app.route("/workouts/<int:session_id>", methods=["GET", "POST"])
def workout_detail(session_id: int) -> str:
    with session_scope() as session:
        workout = session.get(WorkoutSession, session_id)
        if not workout:
            return redirect(url_for("workouts"))
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            sets = int(request.form.get("sets", 1))
            reps = int(request.form.get("reps", 8))
            weight_str = request.form.get("weight")
            weight = int(weight_str) if weight_str else None
            exercise = Exercise(name=name, sets=sets, reps=reps, weight=weight)
            workout.exercises.append(exercise)
            session.add(exercise)
            session.flush()
            return redirect(url_for("workout_detail", session_id=session_id))
        session.expunge(workout)
    return render_template("workout_detail.html", workout=workout)


@app.route("/events", methods=["GET", "POST"])
def events() -> str:
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        start_str = request.form.get("start_datetime")
        notes = request.form.get("notes") or None
        if title and start_str:
            start_dt = parse_datetime(start_str)
            with session_scope() as session:
                event = CalendarEvent(title=title, start_datetime=start_dt, notes=notes)
                session.add(event)
        return redirect(url_for("events"))

    with session_scope() as session:
        events_list = session.query(CalendarEvent).order_by(CalendarEvent.start_datetime.asc()).all()
    return render_template("events.html", events=events_list)


@app.route("/reminders", methods=["GET", "POST"])
def reminders_view() -> str:
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        due_date = request.form.get("due_date")
        notes = request.form.get("notes") or None
        if title and due_date:
            due = datetime.strptime(due_date, "%Y-%m-%d").date()
            with session_scope() as session:
                reminder = Reminder(title=title, due_date=due, notes=notes)
                session.add(reminder)
        return redirect(url_for("reminders_view"))

    with session_scope() as session:
        reminders = session.query(Reminder).order_by(Reminder.due_date.asc()).all()
    return render_template("reminders.html", reminders=reminders)


@app.route("/reminders/<int:reminder_id>/toggle", methods=["POST"])
def toggle_reminder(reminder_id: int) -> Any:
    with session_scope() as session:
        reminder = session.get(Reminder, reminder_id)
        if reminder:
            reminder.completed = not reminder.completed
            session.add(reminder)
    return redirect(url_for("reminders_view"))


@app.route("/metrics", methods=["GET", "POST"])
def metrics() -> str:
    if request.method == "POST":
        metric_date = datetime.strptime(request.form["metric_date"], "%Y-%m-%d").date()
        weight_kg = float(request.form.get("weight_kg", 0))
        body_fat = request.form.get("body_fat")
        notes = request.form.get("notes") or None
        with session_scope() as session:
            metric = BodyMetric(
                metric_date=metric_date,
                weight_kg=weight_kg,
                body_fat=float(body_fat) if body_fat else None,
                notes=notes,
            )
            session.add(metric)
        return redirect(url_for("metrics"))

    with session_scope() as session:
        metrics_list = session.query(BodyMetric).order_by(BodyMetric.metric_date.desc()).all()
    return render_template("metrics.html", metrics=metrics_list)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
