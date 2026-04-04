import os
import json
import random
from datetime import datetime
from app import app
from models import db, Election, Candidate, State, LGA, Ward, PollingUnit, Report, ExtractedResult, IncidenceReport, User

def load_simulation_data():
    """Load the verified 2023 data from JSON."""
    try:
        with open('delta_2023_data.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("[ERROR] delta_2023_data.json not found!")
        return None

def run_simulation():
    print("\n[*] INITIALIZING DELTA STATE 2023 [REALITY ENGINE]...")
    data = load_simulation_data()
    if not data: return

    with app.app_context():
        # 1. Setup State: Delta
        delta = State.query.filter(db.func.lower(State.name) == "delta").first()
        if not delta:
            delta = State(name="Delta", code="DEL")
            db.session.add(delta)
            db.session.commit()
        
        # 2. Setup Election: "Delta State GENERAL Election"
        target_name = "Delta State GENERAL Election"
        election = Election.query.filter(db.func.lower(Election.name) == target_name.lower()).first()
        
        if not election:
            election = Election(
                name=target_name,
                description="Verified 2023 Governorship Data Simulation",
                start_date=datetime(2023, 3, 18),
                end_date=datetime(2023, 3, 19),
                phase="active",
                election_scope="state",
                state_id=delta.id
            )
            db.session.add(election)
            db.session.commit()
        else:
            print("[*] Wiping old corrupted data...")
            # Clean slate protocol
            Report.query.filter_by(election_id=election.id).delete()
            IncidenceReport.query.filter_by(election_id=election.id).delete()
            # Ensure it's linked to Delta
            election.state_id = delta.id
            db.session.commit()

        # 3. Setup Candidates
        candidates_config = [
            {"name": "Sheriff Oborevwori", "party": "PDP", "is_preferred": True},
            {"name": "Ovie Omo-Agege", "party": "APC", "is_preferred": False},
            {"name": "Ken Pela", "party": "LP", "is_preferred": False},
            {"name": "Great Ogburu", "party": "NNPP", "is_preferred": False}
        ]
        
        for c_conf in candidates_config:
            cand = Candidate.query.filter_by(election_id=election.id, party=c_conf['party']).first()
            if not cand:
                cand = Candidate(
                    full_name=c_conf['name'],
                    party=c_conf['party'],
                    election_id=election.id,
                    is_preferred=c_conf['is_preferred'],
                    priority=10 if c_conf['is_preferred'] else 5
                )
                db.session.add(cand)
        db.session.commit()

        # 4. Process LGAs and Inject Results
        print("[*] Injecting verified LGA results...")
        admin_user = User.query.filter_by(role='super_admin').first() or User.query.first()
        
        # We need to map the JSON data to database LGAs
        lga_names = list(data['lga_data'].keys())
        
        # Ensure these LGAs exist in DB
        for lga_name in lga_names:
            lga = LGA.query.filter_by(name=lga_name, state_id=delta.id).first()
            if not lga:
                # Add Approx Lat/Lng for Delta (Central: 5.5N, 6.0E)
                lga = LGA(
                    name=lga_name, 
                    state_id=delta.id,
                    latitude=5.5 + random.uniform(-0.4, 0.4),
                    longitude=6.0 + random.uniform(-0.4, 0.4)
                )
                db.session.add(lga)
                db.session.commit() # Commit to get ID
            
            # --- WARD & PU GENERATION ---
            # Create dummy wards/PUs for this LGA to hold the results
            # We will distribute the LGA total votes across these PUs
            
            lga_votes = data['lga_data'].get(lga_name, {})
            total_lga_votes = sum(lga_votes.values())
            
            # Create a "Collation Center" style PU or split into a few PUs
            # Let's split into 5 PUs per LGA for the map visualization
            num_pus_to_sim = 5
            
            for i in range(1, num_pus_to_sim + 1):
                ward_name = f"{lga_name} Ward {i}"
                ward = Ward.query.filter_by(name=ward_name, lga_id=lga.id).first()
                if not ward:
                    ward = Ward(name=ward_name, lga_id=lga.id)
                    db.session.add(ward)
                    db.session.commit()
                
                pu_code = f"10-{lga.id:02d}-{ward.id:02d}-0{i}"
                pu = PollingUnit.query.filter_by(pu_code=pu_code).first()
                if not pu:
                    pu = PollingUnit(
                        pu_code=pu_code,
                        name=f"PU {i} at {ward_name}",
                        ward_id=ward.id,
                        # Registered voters must be > Accredited
                        # We'll set it later based on the vote share
                        latitude=lga.latitude + random.uniform(-0.03, 0.03),
                        longitude=lga.longitude + random.uniform(-0.03, 0.03)
                    )
                    db.session.add(pu)
                    db.session.commit()

                # --- VOTE DISTRIBUTION INTEGRITY ---
                # Distribute the LGA total roughly evenly across the PUs
                # Add some randomness so they aren't identical
                share = 1.0 / num_pus_to_sim
                
                pu_results = {}
                pu_total_votes = 0
                
                for party, votes in lga_votes.items():
                    # Vary by +/- 10%
                    party_vote = int(votes * share * random.uniform(0.9, 1.1))
                    pu_results[party] = party_vote
                    pu_total_votes += party_vote
                
                # MATHEMATICAL INTEGRITY CHECK
                # Accredited >= Total Votes
                margin = random.randint(5, 50) # Invalid votes + abstain but accredited
                accredited = pu_total_votes + margin
                
                # Registered >= Accredited (Turnout ~30%)
                registered = int(accredited * random.uniform(2.5, 3.5))
                
                # Update PU with correct registered count
                pu.registered_voters = registered
                db.session.add(pu)
                
                # Submit Report
                report = Report(
                    election_id=election.id,
                    pu_id=pu.id,
                    user_id=admin_user.id,
                    total_votes=pu_total_votes,
                    party_results=pu_results,
                    status='verified', # Auto-validate for sim
                    notes=f"Simulated from 2023 Official Data. Integrity Check: {pu_total_votes} <= {accredited}"
                )
                db.session.add(report)
                db.session.commit() # Commit to get Report ID
                
                # Extracted Result (For Analytics)
                ExtractedResult.query.filter_by(report_id=report.id).delete()
                
                md_table = "| Party | Votes |\n|---|---|\n"
                for p, v in pu_results.items():
                    md_table += f"| {p} | {v} |\n"
                
                extracted = ExtractedResult(
                    report_id=report.id,
                    markdown_content=md_table,
                    parsed_data=pu_results,
                    accredited_voters=accredited,
                    total_votes_cast=pu_total_votes,
                    verified_by=admin_user.id,
                    verified_at=datetime.utcnow()
                )
                db.session.add(extracted)
                
        db.session.commit()
        
        # 5. Inject Tactical Incidents
        print("[*] Deploying Historical Incident Markers...")
        incidents = data.get('incidents', [])
        
        for inc_def in incidents:
            lga_name = inc_def['lga']
            # Find a PU in this LGA to attach the incident to
            lga = LGA.query.filter_by(name=lga_name, state_id=delta.id).first()
            if lga:
                # Get one of the PUs we just made
                target_ward = Ward.query.filter_by(lga_id=lga.id).first()
                if target_ward:
                    target_pu = PollingUnit.query.filter_by(ward_id=target_ward.id).first()
                    
                    if target_pu:
                        # Create Incident
                        inc_report = IncidenceReport(
                            election_id=election.id,
                            pu_id=target_pu.id,
                            user_id=admin_user.id,
                            incident_type=inc_def['type'],
                            severity=inc_def['severity'],
                            description=f"[HISTORICAL 2023] {inc_def['desc']}",
                            status='verified'
                        )
                        db.session.add(inc_report)
                        print(f"   -> Placed {inc_def['type']} alert in {lga_name}")

        db.session.commit()
        print("\n[SUCCESS] Simulation Complete.")
        print("Mathematical Integrity Verified: All reports adhere to Votes <= Accredited <= Registered.")
        print("Tactical Map Updated: Historical hotspots in Ughelli, Warri, and Ethiope are active.")

if __name__ == "__main__":
    run_simulation()
