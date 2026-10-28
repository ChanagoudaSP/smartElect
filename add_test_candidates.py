from app import create_app, db
from app.models.models import Election, Candidate
from datetime import datetime, timedelta

app = create_app()

def add_test_candidates():
    with app.app_context():
        # Get all elections
        elections = Election.query.all()
        
        for election in elections:
            # Check if election has any candidates
            existing_candidates = Candidate.query.filter_by(election_id=election.id).count()
            
            if existing_candidates == 0:
                print(f"Adding test candidates to election: {election.title}")
                
                # Add sample candidates
                candidates = [
                    Candidate(
                        election_id=election.id,
                        name="Jane Smith",
                        party="Progressive Party",
                        bio="Experienced leader with a focus on education and healthcare reform."
                    ),
                    Candidate(
                        election_id=election.id,
                        name="John Doe",
                        party="Conservative Alliance",
                        bio="Business leader advocating for economic growth and fiscal responsibility."
                    ),
                    Candidate(
                        election_id=election.id,
                        name="Mike Johnson",
                        party="Independent",
                        bio="Community organizer focused on environmental protection and social justice."
                    )
                ]
                
                # Add candidates to database
                for candidate in candidates:
                    db.session.add(candidate)
                
                try:
                    db.session.commit()
                    print(f"✓ Added {len(candidates)} candidates to election {election.title}")
                except Exception as e:
                    db.session.rollback()
                    print(f"Error adding candidates: {str(e)}")
            else:
                print(f"Election '{election.title}' already has {existing_candidates} candidates")

if __name__ == '__main__':
    add_test_candidates()
