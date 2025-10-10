from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Flight(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    flight_no = db.Column(db.String(20), nullable=False)
    start_time = db.Column(db.String(20), nullable=False)
    end_time = db.Column(db.String(20), nullable=False)
    operation = db.Column(db.String(10), nullable=False)   # Arr / Dep
    category = db.Column(db.String(5), nullable=False)     # M/L/H/J
    status = db.Column(db.String(20), default="pending")

    assignments = db.relationship(
        "Assignment",
        back_populates="flight",
        cascade="all, delete-orphan"
    )

class Runway(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    length = db.Column(db.Integer, nullable=False)
    time_required = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(10), default="free")

    assignments = db.relationship(
        "Assignment",
        back_populates="runway",
        cascade="all, delete-orphan"
    )

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    flight_id = db.Column(
        db.Integer,
        db.ForeignKey('flight.id', ondelete="CASCADE"),
        nullable=False
    )
    runway_id = db.Column(
        db.Integer,
        db.ForeignKey('runway.id', ondelete="CASCADE"),
        nullable=False
    )
    start_time = db.Column(db.String(50))
    end_time = db.Column(db.String(50))
    conflict = db.Column(db.Boolean, default=False)

    flight = db.relationship("Flight", back_populates="assignments")
    runway = db.relationship("Runway", back_populates="assignments")

class ATCController(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    airport = db.Column(db.String(50), nullable=False)
    position = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)  # You can later hash this for security
