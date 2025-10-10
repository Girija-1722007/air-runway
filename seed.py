from models import db, Flight, Runway

def seed_data():
    if not Runway.query.first():
        runways = [Runway(name=f"R{i}") for i in range(1, 5)]
        db.session.add_all(runways)

    if not Flight.query.first():
        flights = [
            Flight(flight_no="F101", start_time="08:00", end_time="09:00"),
            Flight(flight_no="F102", start_time="08:30", end_time="09:30"),
            Flight(flight_no="F103", start_time="09:00", end_time="10:00"),
            Flight(flight_no="F104", start_time="09:15", end_time="10:15"),
        ]
        db.session.add_all(flights)

    db.session.commit()
