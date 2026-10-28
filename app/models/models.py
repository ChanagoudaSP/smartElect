from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from app import db


class User(UserMixin, db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    national_id = db.Column(db.String(20), unique=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    votes = db.relationship('Vote', backref='voter', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Election(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    candidates = db.relationship('Candidate', backref='election', lazy=True)
    votes = db.relationship('Vote', backref='election', lazy=True)

    @property
    def current_status(self):
        """Get the current status with precise timing"""
        now = datetime.utcnow()
        
        if not self.is_active:
            return "inactive"
        
        # Compare timestamps ensuring microsecond precision
        start_diff = (self.start_date - now).total_seconds()
        end_diff = (self.end_date - now).total_seconds()
        
        if start_diff > 0:
            # Not started yet
            if start_diff < 3600:  # Less than 1 hour to start
                minutes = int(start_diff / 60)
                return f"starting_soon_{minutes}"
            return "upcoming"
        elif end_diff >= 0:
            # Currently active
            if end_diff < 3600:  # Less than 1 hour to end
                minutes = int(end_diff / 60)
                return f"ending_soon_{minutes}"
            return "active"
        else:
            return "ended"
    
    @property
    def has_started(self):
        """Check if the election has started"""
        now = datetime.utcnow()
        return (now - self.start_date).total_seconds() >= 0
    
    @property
    def has_ended(self):
        """Check if the election has ended"""
        now = datetime.utcnow()
        return (now - self.end_date).total_seconds() > 0
    
    @property
    def is_currently_active(self):
        """Check if the election is currently active"""
        now = datetime.utcnow()
        return (
            self.is_active and 
            (now - self.start_date).total_seconds() >= 0 and 
            (self.end_date - now).total_seconds() > 0
        )
    
    @property
    def time_remaining(self):
        """Get time remaining with improved precision"""
        now = datetime.utcnow()
        if now < self.start_date:
            diff = self.start_date - now
            total_minutes = int(diff.total_seconds() / 60)
            if total_minutes < 60:
                return f"{total_minutes} minutes until start"
            hours = total_minutes // 60
            minutes = total_minutes % 60
            return f"{hours} hours {minutes} minutes until start"
        elif now <= self.end_date:
            diff = self.end_date - now
            total_minutes = int(diff.total_seconds() / 60)
            if total_minutes < 60:
                return f"{total_minutes} minutes remaining"
            hours = total_minutes // 60
            minutes = total_minutes % 60
            return f"{hours} hours {minutes} minutes remaining"
        return "Ended"

    def user_has_voted(self, user):
        """Check if a user has voted in this election"""
        return any(vote.user_id == user.id for vote in self.votes)

    def can_vote(self, user):
        """Check if a user can vote in this election"""
        return (self.is_ongoing and 
                not self.user_has_voted(user) and 
                user.is_verified)

    def validate_dates(self):
        """Validate election dates"""
        now = datetime.utcnow()
        if self.start_date <= now:
            raise ValueError("Start date must be in the future")
        if self.end_date <= self.start_date:
            raise ValueError("End date must be after start date")
        return True

    @property
    def formatted_duration(self):
        """Get formatted election duration"""
        duration = self.end_date - self.start_date
        days = duration.days
        hours = duration.seconds // 3600
        return f"{days} days, {hours} hours"

    @property
    def formatted_status(self):
        """Get user-friendly status message"""
        status = self.status
        if status == "upcoming":
            return f"Starting in {self.time_remaining.days} days"
        elif status == "active":
            remaining = self.time_remaining
            if remaining.days > 0:
                return f"{remaining.days} days remaining"
            else:
                hours = remaining.seconds // 3600
                return f"{hours} hours remaining"
        elif status == "ended":
            return "Election has ended"
        else:
            return "Election is inactive"
    
    @property
    def is_currently_active(self):
        """Check if the election is currently active"""
        now = datetime.utcnow()
        return self.is_active and now >= self.start_date and now < self.end_date
    
    @property
    def is_ongoing(self):
        """Check if the election is currently ongoing"""
        now = datetime.utcnow()
        return self.is_active and now >= self.start_date and now < self.end_date


class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    party = db.Column(db.String(100), nullable=False)
    bio = db.Column(db.Text, nullable=True)
    #photo_url = db.Column(db.String(200), nullable=True)
    election_id = db.Column(db.Integer, db.ForeignKey('election.id'), nullable=False)

    photo = db.Column(db.String(255))  # stores filename or relative path
    verified = db.Column(db.Boolean, default=False)

    @property
    def photo_url(self):
        if self.photo:
            return url_for('static', filename=f'uploads/candidates/{self.photo}', _external=False)
        else:
            return url_for('static', filename='img/default_candidate.png', _external=False)
    # Relationships
    votes = db.relationship('Vote', backref='candidate', lazy=True)

    def get_vote_count(self):
        return len(self.votes)


class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    election_id = db.Column(db.Integer, db.ForeignKey('election.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidate.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    encrypted_vote = db.Column(db.Text, nullable=True)  # Making this nullable for now

    __table_args__ = (
        db.UniqueConstraint('user_id', 'election_id', name='unique_vote'),
    )