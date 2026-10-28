from app import db
from app.models.models import User, Election, Candidate, Vote
from datetime import datetime, timedelta
from sqlalchemy import func
from functools import lru_cache
from typing import Optional, List, Tuple

# Cache user queries for 5 minutes
@lru_cache(maxsize=128, typed=True)
def get_user_by_email(email: str) -> Optional[User]:
    """Get user by email with caching."""
    return User.query.filter_by(email=email).first()

@lru_cache(maxsize=128, typed=True)
def get_user_by_national_id(national_id: str) -> Optional[User]:
    """Get user by national ID with caching."""
    return User.query.filter_by(national_id=national_id).first()

def create_user(email: str, password: str, first_name: str, last_name: str,
                national_id: str) -> User:
    """Create a new user with validation."""
    # Clear cache for this user's queries
    get_user_by_email.cache_clear()
    get_user_by_national_id.cache_clear()

    # Validate first and last name: only allow letters (upper/lowercase)
    import re
    if not re.fullmatch(r"[A-Za-z]+", first_name.strip()):
        raise ValueError("First name must contain only letters (A-Z, a-z)")
    if not re.fullmatch(r"[A-Za-z]+", last_name.strip()):
        raise ValueError("Last name must contain only letters (A-Z, a-z)")

    user = User(
        email=email.lower().strip(),
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        national_id=national_id.strip()
    )
    user.set_password(password)

    try:
        db.session.add(user)
        db.session.commit()
        return user
    except Exception as e:
        db.session.rollback()
        raise e

def get_active_elections():
    """Get all currently active elections."""
    now_local = datetime.now()
    return Election.query.filter(
        Election.is_active == True,
        Election.start_date <= now_local,
        Election.end_date >= now_local
    ).order_by(Election.start_date.asc()).all()


def get_upcoming_elections():
    """Get all scheduled elections that have not started yet."""
    now_local = datetime.now()
    return Election.query.filter(
        Election.is_active == True,
        Election.start_date > now_local
    ).order_by(Election.start_date.asc()).all()


def get_election_by_id(election_id):
    """Get election by ID."""
    return Election.query.get(election_id)

def create_election(title, description, start_date, end_date):
    """Create a new election."""
    election = Election(
        title=title,
        description=description,
        start_date=start_date,
        end_date=end_date,
        is_active=True
    )
    db.session.add(election)
    db.session.commit()
    return election

def add_candidate(election_id, name, party, bio=None, photo_url=None):
    """Add a candidate to an election."""
    candidate = Candidate(
        name=name,
        party=party,
        bio=bio,
        photo_url=photo_url,
        election_id=election_id
    )
    db.session.add(candidate)
    db.session.commit()
    return candidate

def record_vote(user_id, election_id, candidate_id, encrypted_vote):
    """Record a vote."""
    # Check if user has already voted in this election
    existing_vote = Vote.query.filter_by(
        user_id=user_id,
        election_id=election_id
    ).first()
    
    if existing_vote:
        return False, "User has already voted in this election"
    
    vote = Vote(
        user_id=user_id,
        election_id=election_id,
        candidate_id=candidate_id,
        encrypted_vote=encrypted_vote
    )
    db.session.add(vote)
    db.session.commit()
    return True, "Vote recorded successfully"

def get_election_results(election_id):
    """Get results for an election."""
    results = db.session.query(
        Candidate.id,
        Candidate.name,
        Candidate.party,
        func.count(Vote.id).label('vote_count')
    ).outerjoin(Vote).filter(
        Candidate.election_id == election_id
    ).group_by(
        Candidate.id,
        Candidate.name,
        Candidate.party
    ).all()
    
    return results

def get_user_voting_history(user_id):
    """Get voting history for a user."""
    history = db.session.query(
        Election.title,
        Election.start_date,
        Candidate.name.label('candidate_name'),
        Vote.timestamp
    ).join(
        Vote, Vote.election_id == Election.id
    ).join(
        Candidate, Vote.candidate_id == Candidate.id
    ).filter(
        Vote.user_id == user_id
    ).order_by(
        Vote.timestamp.desc()
    ).all()
    
    return history

def verify_user(user_id):
    """Verify a user's account."""
    user = User.query.get(user_id)
    if user:
        user.is_verified = True
        db.session.commit()
        return True
    return False

def get_election_statistics():
    """Get overall election statistics."""
    stats = {
        'total_users': User.query.count(),
        'total_elections': Election.query.count(),
        'active_elections': Election.query.filter_by(is_active=True).count(),
        'total_votes': Vote.query.count(),
        'verified_users': User.query.filter_by(is_verified=True).count()
    }
    return stats 