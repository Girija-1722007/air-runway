import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta
from models import db, Flight, Runway, Assignment


app = Flask(__name__)
app.secret_key = "supersecret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app_new.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

from flask_migrate import Migrate

# assuming you already have:
# app = Flask(__name__)
# db = SQLAlchemy(app)

migrate = Migrate(app, db)


# ---------------- ATC Login Data ----------------
ATC_USERS = [
    {"name": "John", "airport": "XYZ", "position": "Supervisor", "password": "1234"},
    {"name": "Alice", "airport": "ABC", "position": "Ground Controller", "password": "abcd"},
]

# ---------------- Custom Jinja Filter ----------------
@app.template_filter('todatetime')
def todatetime(value):
    """Convert ISO string to datetime object"""
    return datetime.fromisoformat(value)


# ---------------- HOME: ATC Login ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        name = request.form["name"]
        airport = request.form["airport"]
        position = request.form["position"]
        password = request.form["password"]

        atc = next((user for user in ATC_USERS if
                    user["name"] == name and
                    user["airport"] == airport and
                    user["position"] == position and
                    user["password"] == password), None)

        if atc:
            session["atc_name"] = name
            # Initialize login history for this session
            session["login_history"] = session.get("login_history", [])
            session["login_history"].append({
                "name": name,
                "airport": airport,
                "position": position,
                "login_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            flash(f"Welcome {name} ({position})", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid login details. Please try again.", "danger")
            return redirect(url_for("login"))

    return render_template("login.html", history=session.get("login_history", []))


# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    now = datetime.now()
    flights_pending = Flight.query.filter_by(status="pending").count()
    flights_assigned = Flight.query.filter_by(status="assigned").count()
    runways_count = Runway.query.count()
    flights = Flight.query.all()
    runways = Runway.query.all()
    
    # Prepare assignments with datetime objects
    assignments = Assignment.query.all()
    assignments_with_dt = []

    for a in assignments:
        start_dt = datetime.fromisoformat(a.start_time)
        end_dt = datetime.fromisoformat(a.end_time)
        assignments_with_dt.append({
            "assignment": a,
            "start_dt": start_dt,
            "end_dt": end_dt
        })

    return render_template(
        "dashboard.html",
        flights_pending=flights_pending,
        flights_assigned=flights_assigned,
        runways_count=runways_count,
        assignments=assignments_with_dt,  # now includes start/end datetime objects
        flights=flights,
        runways=runways,
        now=now  # current datetime for strikethrough comparison
    )



# ---------------- FLIGHTS ----------------
@app.route("/flights", methods=["GET", "POST"])
def flights_route():
    if request.method == "POST":
        flight_no = request.form["flight_no"]
        operation = request.form["operation"]
        category = request.form["category"]
        start_time = request.form["start_time"]
        end_time = request.form["end_time"]

        status = "pending"
        if datetime.fromisoformat(end_time) < datetime.now():
            status = "done"

        f = Flight(
            flight_no=flight_no,
            start_time=start_time,
            end_time=end_time,
            status=status,
            operation=operation,
            category=category
        )
        db.session.add(f)
        db.session.commit()
        return redirect(url_for("flights_route"))

    flights = Flight.query.all()
    return render_template("flights.html", flights=flights)


# ---------------- RUNWAYS ----------------
@app.route("/runways", methods=["GET", "POST"])
def runways():
    if request.method == "POST":
        name = request.form["name"]
        length = int(request.form["length"])
        time_required = int(request.form["time_required"])
        r = Runway(name=name, length=length, time_required=time_required)
        db.session.add(r)
        db.session.commit()
        return redirect(url_for("runways"))
    return render_template("runways.html", runways=Runway.query.all())


# ---------------- ALLOCATION ----------------
@app.route("/allocate", methods=["POST"])
def allocate():
    flights = Flight.query.order_by(Flight.start_time).all()  # order by start_time
    runways = Runway.query.all()

    # Clear existing assignments to recompute
    Assignment.query.delete()
    db.session.commit()

    for flight in flights:
        assigned = False
        new_start = datetime.fromisoformat(flight.start_time)
        new_end = datetime.fromisoformat(flight.end_time)

        for runway in runways:
            conflict = False
            assignments = Assignment.query.filter_by(runway_id=runway.id).all()

            for a in assignments:
                occupied_start = datetime.fromisoformat(a.start_time)
                occupied_end = datetime.fromisoformat(a.end_time)
                if not (new_end <= occupied_start or new_start >= occupied_end):
                    conflict = True
                    break

            if not conflict:
                # Assign this runway
                new_assignment = Assignment(
                    flight_id=flight.id,
                    runway_id=runway.id,
                    start_time=flight.start_time,
                    end_time=flight.end_time,
                    conflict=False
                )
                db.session.add(new_assignment)
                flight.status = "assigned"
                db.session.commit()
                assigned = True
                break

        if not assigned:
            flight.status = "pending"
            db.session.commit()

    flash("Runways allocated for all flights!", "success")
    return redirect(url_for("dashboard"))


# ---------------- ASSIGNMENTS ----------------
@app.route("/assignments")
def assignments_route():
    return render_template("assignments.html", assignments=Assignment.query.all())

# ---------------- EMERGENCY HANDLING ----------------
@app.route("/emergency", methods=["POST"])
def handle_emergency():
    flight_id = request.form.get("flight_id")
    new_start_time = request.form.get("new_start_time")
    new_end_time = request.form.get("new_end_time")

    flight = Flight.query.get(flight_id)
    if not flight:
        flash("Flight not found!", "danger")
        return redirect(url_for("dashboard"))

    # Update the flight timing
    flight.start_time = new_start_time
    flight.end_time = new_end_time
    db.session.commit()

    # Adjust nearby flights to avoid conflicts
    same_runway_assignments = Assignment.query.filter_by(runway_id=Assignment.query.filter_by(flight_id=flight.id).first().runway_id).all()
    same_runway_assignments = sorted(same_runway_assignments, key=lambda x: datetime.fromisoformat(x.start_time))

    buffer = timedelta(minutes=15)
    for i in range(1, len(same_runway_assignments)):
        prev = same_runway_assignments[i - 1]
        curr = same_runway_assignments[i]
        prev_end = datetime.fromisoformat(prev.end_time)
        curr_start = datetime.fromisoformat(curr.start_time)
        if curr_start <= prev_end + buffer:
            curr.start_time = (prev_end + buffer).isoformat()
            curr.end_time = (datetime.fromisoformat(curr.start_time) + (datetime.fromisoformat(curr.end_time) - datetime.fromisoformat(curr.start_time))).isoformat()
            db.session.commit()

    flash(f"Emergency handled: Flight {flight.flight_no} timing updated.", "info")
    return redirect(url_for("dashboard"))


# ---------------- DISASTER HANDLING ----------------
@app.route("/delete_runway", methods=["POST"])
def delete_runway():
    runway_id = request.form.get("runway_id")
    runway = Runway.query.get(runway_id)

    if not runway:
        flash("Runway not found", "danger")
        return redirect(url_for("dashboard"))

    # ✅ Delete all assignments linked to this runway first
    assignments = Assignment.query.filter_by(runway_id=runway.id).all()
    for a in assignments:
        db.session.delete(a)

    # ✅ Now delete the runway
    db.session.delete(runway)
    db.session.commit()

    flash(f"Runway '{runway.name}' and its related assignments deleted successfully!", "success")
    return redirect(url_for("dashboard"))




# ---------------- LOGIN HISTORY ----------------
@app.route("/login_history")
def show_history():
    return render_template("history.html", history=session.get("login_history", []))


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully", "info")
    return redirect(url_for("login"))


# ---------------- RUN APP ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

