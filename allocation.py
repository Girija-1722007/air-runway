def allocate_runways():
    flights = Flight.query.all()
    runways = Runway.query.all()
    
    for flight in flights:
        existing_assignment = Assignment.query.filter_by(flight_id=flight.id).first()
        if existing_assignment:
            continue  # Already assigned
        
        assigned = False
        for runway in runways:
            overlap = Assignment.query.filter(
                Assignment.runway_id == runway.id,
                Assignment.departure_time < flight.arrival_time,
                Assignment.arrival_time > flight.departure_time
            ).first()
            
            if not overlap:
                new_assign = Assignment(
                    flight_id=flight.id,
                    runway_id=runway.id,
                    arrival_time=flight.arrival_time,
                    departure_time=flight.departure_time
                )
                db.session.add(new_assign)
                assigned = True
                break
        
        if not assigned:
            print(f"No free runway for flight {flight.flight_no}")
    
    db.session.commit()
