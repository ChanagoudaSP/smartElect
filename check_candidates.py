from app import create_app
from app.models.models import Election, Candidate
from datetime import datetime

app = create_app()

with app.app_context():
    # Get all elections
    elections = Election.query.all()
    
    print("\nChecking Candidates in Elections:")
    print("-" * 50)
    
    for election in elections:
        print(f"\nElection: {election.title}")
        print(f"Active: {election.is_active}")
        print(f"Start Date: {election.start_date}")
        print(f"End Date: {election.end_date}")
        
        # Get candidates for this election
        candidates = Candidate.query.filter_by(election_id=election.id).all()
        
        if candidates:
            print("\nCandidates:")
            for candidate in candidates:
                print(f"- {candidate.name} ({candidate.party})")
        else:
            print("No candidates found for this election")
