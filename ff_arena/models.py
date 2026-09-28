from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from ff_arena import db

def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class User(UserMixin, db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    free_fire_uid = db.Column(db.String(50), unique=True, nullable=True, index=True)
    in_game_name = db.Column(db.String(100), default='')
    profile_image = db.Column(db.String(255), default='default_avatar.png')
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utc_now)

    # Relationships
    teams = db.relationship('Team', backref='captain', lazy=True, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade='all, delete-orphan', order_by='desc(Notification.created_at)')
    complaints = db.relationship('Complaint', backref='user', lazy=True, cascade='all, delete-orphan', order_by='desc(Complaint.created_at)')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def tournaments_played(self):
        # Distinct tournaments where user has an approved team
        tourn_ids = set(t.tournament_id for t in self.teams if t.status == 'APPROVED')
        return len(tourn_ids)

    @property
    def matches_played(self):
        # Count verified results for user's teams
        team_ids = [t.id for t in self.teams]
        if not team_ids:
            return 0
        return Result.query.filter(Result.team_id.in_(team_ids), Result.verification_status == 'APPROVED').count()

    @property
    def wins(self):
        # 1st place finishes in approved results
        team_ids = [t.id for t in self.teams]
        if not team_ids:
            return 0
        return Result.query.filter(Result.team_id.in_(team_ids), Result.verification_status == 'APPROVED', Result.placement == 1).count()

    @property
    def total_kills(self):
        team_ids = [t.id for t in self.teams]
        if not team_ids:
            return 0
        results = Result.query.filter(Result.team_id.in_(team_ids), Result.verification_status == 'APPROVED').all()
        return sum(r.kills for r in results)

    @property
    def total_points(self):
        team_ids = [t.id for t in self.teams]
        if not team_ids:
            return 0
        results = Result.query.filter(Result.team_id.in_(team_ids), Result.verification_status == 'APPROVED').all()
        return sum(r.total_points for r in results)


class Tournament(db.Model):
    __tablename__ = 'tournament'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    banner = db.Column(db.String(255), default='')
    description = db.Column(db.Text, default='')
    date = db.Column(db.String(50), nullable=False)
    time = db.Column(db.String(50), nullable=False)
    entry_fee = db.Column(db.Float, default=0.0)
    prize_pool = db.Column(db.Float, default=0.0)
    max_teams = db.Column(db.Integer, default=48)
    game_mode = db.Column(db.String(50), default='Squad') # Squad, Duo, Solo
    map = db.Column(db.String(50), default='Bermuda') # Bermuda, Purgatory, Kalahari, Alpine
    rules = db.Column(db.Text, default='')
    status = db.Column(db.String(50), default='REGISTRATION OPEN') # UPCOMING, REGISTRATION OPEN, FULL, LIVE, COMPLETED
    created_at = db.Column(db.DateTime, default=utc_now)

    # Relationships
    teams = db.relationship('Team', backref='tournament', lazy=True, cascade='all, delete-orphan')
    matches = db.relationship('Match', backref='tournament', lazy=True, cascade='all, delete-orphan', order_by='Match.match_number')

    @property
    def registered_teams_count(self):
        return len([t for t in self.teams if t.status in ['APPROVED', 'PENDING']])

    @property
    def approved_teams_count(self):
        return len([t for t in self.teams if t.status == 'APPROVED'])

    @property
    def is_full(self):
        return self.registered_teams_count >= self.max_teams


class Team(db.Model):
    __tablename__ = 'team'

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.String(50), unique=True, nullable=False, index=True) # e.g. MFF-2026-001
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    captain_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    team_name = db.Column(db.String(100), nullable=False)

    player2_name = db.Column(db.String(100), nullable=False)
    player2_uid = db.Column(db.String(50), nullable=False)

    player3_name = db.Column(db.String(100), nullable=False)
    player3_uid = db.Column(db.String(50), nullable=False)

    player4_name = db.Column(db.String(100), nullable=False)
    player4_uid = db.Column(db.String(50), nullable=False)

    substitute_name = db.Column(db.String(100), nullable=True, default='')
    substitute_uid = db.Column(db.String(50), nullable=True, default='')

    status = db.Column(db.String(50), default='APPROVED') # APPROVED, PENDING, REJECTED
    created_at = db.Column(db.DateTime, default=utc_now)

    # Relationships
    results = db.relationship('Result', backref='team', lazy=True, cascade='all, delete-orphan')


class Match(db.Model):
    __tablename__ = 'match'

    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    match_number = db.Column(db.Integer, nullable=False)
    date = db.Column(db.String(50), nullable=False)
    time = db.Column(db.String(50), nullable=False)
    map = db.Column(db.String(50), default='Bermuda')
    room_id = db.Column(db.String(100), default='')
    room_password = db.Column(db.String(100), default='')
    room_release_time = db.Column(db.String(50), default='') # Compatibility field
    room_release_datetime = db.Column(db.String(50), default='') # YYYY-MM-DDTHH:MM
    room_status = db.Column(db.String(50), default='NOT SET') # NOT SET, SCHEDULED, PUBLISHED, LIVE, COMPLETED
    room_published = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(50), default='Upcoming') # Upcoming, Live, Completed
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    results = db.relationship('Result', backref='match', lazy=True, cascade='all, delete-orphan')

    @property
    def effective_room_status(self):
        """
        Computes dynamic room status:
        NOT SET: When room_id or room_password are empty
        SCHEDULED: When credentials set but release time is in future and not manually published
        PUBLISHED: When release time arrived or manually published
        LIVE: When match is currently live
        COMPLETED: When match is completed
        """
        if self.status == 'Completed':
            return 'COMPLETED'
        if self.status == 'Live':
            return 'LIVE'
        if not self.room_id or not self.room_password:
            return 'NOT SET'
        if self.room_published:
            return 'PUBLISHED'

        release_val = self.room_release_datetime or self.room_release_time
        if release_val:
            try:
                clean_time = release_val.replace('T', ' ').strip()
                if '-' not in clean_time and self.date:
                    clean_time = f"{self.date} {clean_time}"
                rel_dt = datetime.strptime(clean_time[:16], '%Y-%m-%d %H:%M')
                if datetime.now() >= rel_dt:
                    return 'PUBLISHED'
            except Exception:
                pass
        return 'SCHEDULED'

    def is_room_released(self):
        """
        Check if the room details should be visible to eligible registered players.
        Returns True if:
        1. Room ID and Password are set, AND
        2. effective_room_status is in ['PUBLISHED', 'LIVE', 'COMPLETED'].
        """
        if not self.room_id or not self.room_password:
            return False
        return self.effective_room_status in ['PUBLISHED', 'LIVE', 'COMPLETED']

    @property
    def release_date_display(self):
        release_val = self.room_release_datetime or self.room_release_time
        if not release_val:
            return self.date
        try:
            clean_time = release_val.replace('T', ' ').strip()
            if '-' not in clean_time and self.date:
                clean_time = f"{self.date} {clean_time}"
            dt = datetime.strptime(clean_time[:16], '%Y-%m-%d %H:%M')
            return dt.strftime('%d %B %Y')
        except Exception:
            return self.date

    @property
    def release_time_display(self):
        release_val = self.room_release_datetime or self.room_release_time
        if not release_val:
            return self.time
        try:
            clean_time = release_val.replace('T', ' ').strip()
            if '-' not in clean_time and self.date:
                clean_time = f"{self.date} {clean_time}"
            dt = datetime.strptime(clean_time[:16], '%Y-%m-%d %H:%M')
            return dt.strftime('%I:%M %p').lstrip('0')
        except Exception:
            return self.time

    @property
    def formatted_release_datetime(self):
        """
        Returns a human-readable release date/time string, e.g. '28 September 2026 at 7:45 PM'
        """
        release_val = self.room_release_datetime or self.room_release_time
        if not release_val:
            return f"{self.date} at {self.time}"
        try:
            clean_time = release_val.replace('T', ' ').strip()
            if '-' not in clean_time and self.date:
                clean_time = f"{self.date} {clean_time}"
            dt = datetime.strptime(clean_time[:16], '%Y-%m-%d %H:%M')
            return dt.strftime('%d %B %Y at %I:%M %p')
        except Exception:
            return release_val

    @property
    def release_iso(self):
        """
        Returns ISO formatted string suitable for JavaScript countdown: YYYY-MM-DDTHH:MM:SS
        """
        release_val = self.room_release_datetime or self.room_release_time
        if not release_val:
            return ""
        clean_time = release_val.replace(' ', 'T').strip()
        if '-' not in clean_time and self.date:
            clean_time = f"{self.date}T{clean_time}"
        if len(clean_time) == 16:
            clean_time += ":00"
        return clean_time

    @property
    def release_date_input(self):
        val = self.room_release_datetime or self.room_release_time
        if val and 'T' in val:
            return val.split('T')[0]
        if val and ' ' in val:
            return val.split(' ')[0]
        if val and '-' in val:
            return val
        return self.date or ''

    @property
    def release_time_input(self):
        val = self.room_release_datetime or self.room_release_time
        if val and 'T' in val:
            return val.split('T')[1][:5]
        if val and ' ' in val:
            return val.split(' ')[1][:5]
        if val and ':' in val and '-' not in val:
            return val[:5]
        return self.time or ''


class Result(db.Model):
    __tablename__ = 'result'

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('match.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    kills = db.Column(db.Integer, default=0)
    placement = db.Column(db.Integer, default=0)
    placement_points = db.Column(db.Integer, default=0)
    kill_points = db.Column(db.Integer, default=0)
    total_points = db.Column(db.Integer, default=0)
    screenshot = db.Column(db.String(255), default='')
    verification_status = db.Column(db.String(50), default='PENDING VERIFICATION') # PENDING VERIFICATION, APPROVED, REJECTED
    created_at = db.Column(db.DateTime, default=utc_now)


class Notification(db.Model):
    __tablename__ = 'notification'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utc_now)


class Complaint(db.Model):
    __tablename__ = 'complaint'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category = db.Column(db.String(50), nullable=False) # Payment, Registration, Match, Result, Technical, Other
    subject = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='OPEN') # OPEN, IN PROGRESS, RESOLVED
    admin_reply = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=utc_now)


class Setting(db.Model):
    __tablename__ = 'setting'

    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.Text, nullable=False)

    @classmethod
    def get_setting(cls, key, default=None):
        item = db.session.get(cls, key)
        return item.value if item else default

    @classmethod
    def set_setting(cls, key, value):
        item = db.session.get(cls, key)
        if not item:
            item = cls(key=key, value=str(value))
            db.session.add(item)
        else:
            item.value = str(value)
        db.session.commit()
