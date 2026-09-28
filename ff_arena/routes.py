import os
import uuid
from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from ff_arena import db
from ff_arena.models import User, Tournament, Team, Match, Result, Notification, Complaint, Setting

main_bp = Blueprint('main', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@main_bp.route('/')
def index():
    upcoming_tournaments = Tournament.query.filter(Tournament.status.in_(['UPCOMING', 'REGISTRATION OPEN'])).order_by(Tournament.date.asc()).limit(6).all()
    live_tournaments = Tournament.query.filter_by(status='LIVE').all()
    completed_tournaments = Tournament.query.filter_by(status='COMPLETED').order_by(Tournament.date.desc()).limit(4).all()
    
    # Leaderboard summary stats
    total_tournaments = Tournament.query.count()
    total_teams = Team.query.filter_by(status='APPROVED').count()
    total_matches = Match.query.count()

    return render_template('index.html',
                           upcoming_tournaments=upcoming_tournaments,
                           live_tournaments=live_tournaments,
                           completed_tournaments=completed_tournaments,
                           total_tournaments=total_tournaments,
                           total_teams=total_teams,
                           total_matches=total_matches)


@main_bp.route('/dashboard')
@login_required
def dashboard():
    my_teams = Team.query.filter_by(captain_id=current_user.id).all()
    team_ids = [t.id for t in my_teams]
    
    # Find upcoming & live matches for tournaments current user is in
    tournament_ids = [t.tournament_id for t in my_teams]
    upcoming_matches = Match.query.filter(Match.tournament_id.in_(tournament_ids), Match.status.in_(['Upcoming', 'Live'])).order_by(Match.date.asc(), Match.time.asc()).limit(5).all() if tournament_ids else []
    
    # Recent results submitted
    recent_results = Result.query.filter(Result.team_id.in_(team_ids)).order_by(Result.created_at.desc()).limit(5).all() if team_ids else []
    
    recent_notifs = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(4).all()

    return render_template('dashboard.html',
                           user=current_user,
                           my_teams=my_teams,
                           upcoming_matches=upcoming_matches,
                           recent_results=recent_results,
                           recent_notifs=recent_notifs)


@main_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        in_game_name = request.form.get('in_game_name', '').strip()
        free_fire_uid = request.form.get('free_fire_uid', '').strip()

        if not name:
            flash('Name cannot be empty.', 'danger')
            return redirect(url_for('main.profile'))

        # Check UID duplicate if changed
        if free_fire_uid and free_fire_uid != current_user.free_fire_uid:
            existing = User.query.filter(User.free_fire_uid == free_fire_uid, User.id != current_user.id).first()
            if existing:
                flash('This Free Fire UID is already in use by another player.', 'danger')
                return redirect(url_for('main.profile'))
            current_user.free_fire_uid = free_fire_uid

        current_user.name = name
        current_user.in_game_name = in_game_name

        # Profile Picture Upload
        file = request.files.get('profile_image')
        if file and file.filename and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"avatar_{current_user.id}_{int(datetime.now(timezone.utc).timestamp())}.{ext}"
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            current_user.profile_image = filename

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('main.profile'))

    return render_template('profile.html', user=current_user)


@main_bp.route('/tournaments')
def tournaments():
    status_filter = request.args.get('status', 'ALL').upper()
    query = Tournament.query

    if status_filter == 'UPCOMING':
        query = query.filter(Tournament.status.in_(['UPCOMING', 'REGISTRATION OPEN']))
    elif status_filter == 'LIVE':
        query = query.filter_by(status='LIVE')
    elif status_filter == 'COMPLETED':
        query = query.filter_by(status='COMPLETED')

    all_tournaments = query.order_by(Tournament.created_at.desc()).all()
    return render_template('tournaments.html', tournaments=all_tournaments, active_tab=status_filter)


@main_bp.route('/tournament/<int:tournament_id>')
def tournament_details(tournament_id):
    tournament = db.get_or_404(Tournament, tournament_id)
    matches = Match.query.filter_by(tournament_id=tournament.id).order_by(Match.match_number.asc()).all()
    teams = Team.query.filter_by(tournament_id=tournament.id, status='APPROVED').all()

    # Check if current user is already registered for this tournament
    user_team = None
    if current_user.is_authenticated:
        user_team = Team.query.filter_by(tournament_id=tournament.id, captain_id=current_user.id).first()

    return render_template('tournament_details.html',
                           tournament=tournament,
                           matches=matches,
                           teams=teams,
                           user_team=user_team)


@main_bp.route('/team/register/<int:tournament_id>', methods=['GET', 'POST'])
@login_required
def team_register(tournament_id):
    tournament = db.get_or_404(Tournament, tournament_id)

    # Check if tournament accepts registrations
    if tournament.status not in ['REGISTRATION OPEN', 'UPCOMING']:
        flash('Registrations for this tournament are currently closed.', 'warning')
        return redirect(url_for('main.tournament_details', tournament_id=tournament.id))

    if tournament.is_full:
        flash('This tournament is already full. No more slots available.', 'danger')
        return redirect(url_for('main.tournament_details', tournament_id=tournament.id))

    # Check if captain has already registered
    existing_team = Team.query.filter_by(tournament_id=tournament.id, captain_id=current_user.id).first()
    if existing_team:
        flash('You have already registered a team for this tournament!', 'info')
        return render_template('registration_success.html', team=existing_team, tournament=tournament)

    if request.method == 'POST':
        team_name = request.form.get('team_name', '').strip()
        player2_name = request.form.get('player2_name', '').strip()
        player2_uid = request.form.get('player2_uid', '').strip()
        player3_name = request.form.get('player3_name', '').strip()
        player3_uid = request.form.get('player3_uid', '').strip()
        player4_name = request.form.get('player4_name', '').strip()
        player4_uid = request.form.get('player4_uid', '').strip()
        substitute_name = request.form.get('substitute_name', '').strip()
        substitute_uid = request.form.get('substitute_uid', '').strip()

        # Check required fields
        if not team_name or not player2_name or not player2_uid or not player3_name or not player3_uid or not player4_name or not player4_uid:
            flash('Please complete all 4 squad roster member fields.', 'danger')
            return render_template('team_register.html', tournament=tournament)

        # Generate unique team ID (e.g. MFF-2026-001)
        year = datetime.now().year
        count = Team.query.count() + 1
        team_code = f"MFF-{year}-{count:03d}"
        while Team.query.filter_by(team_id=team_code).first():
            count += 1
            team_code = f"MFF-{year}-{count:03d}"

        new_team = Team(
            team_id=team_code,
            tournament_id=tournament.id,
            captain_id=current_user.id,
            team_name=team_name,
            player2_name=player2_name,
            player2_uid=player2_uid,
            player3_name=player3_name,
            player3_uid=player3_uid,
            player4_name=player4_name,
            player4_uid=player4_uid,
            substitute_name=substitute_name,
            substitute_uid=substitute_uid,
            status='APPROVED' # Instant approval for smooth tournament onboarding
        )

        db.session.add(new_team)

        # Check if tournament is now full
        db.session.flush()
        if tournament.is_full:
            tournament.status = 'FULL'

        # Create confirmation notification
        notif = Notification(
            user_id=current_user.id,
            title='Registration Successful!',
            message=f'Your squad "{team_name}" was successfully registered for "{tournament.name}". Your Team ID is {team_code}.'
        )
        db.session.add(notif)
        db.session.commit()

        flash(f'Squad registered successfully! Your Team ID is {team_code}.', 'success')
        return render_template('registration_success.html', team=new_team, tournament=tournament)

    return render_template('team_register.html', tournament=tournament)


@main_bp.route('/my-tournaments')
@login_required
def my_tournaments():
    teams = Team.query.filter_by(captain_id=current_user.id).all()
    upcoming_data = []
    live_data = []
    completed_data = []

    for team in teams:
        tourn = team.tournament
        # Find next/latest match
        match = Match.query.filter_by(tournament_id=tourn.id).order_by(Match.match_number.asc()).first()
        data = {
            'team': team,
            'tournament': tourn,
            'match': match,
            'status': team.status
        }
        if tourn.status in ['UPCOMING', 'REGISTRATION OPEN', 'FULL']:
            upcoming_data.append(data)
        elif tourn.status == 'LIVE':
            live_data.append(data)
        else:
            completed_data.append(data)

    return render_template('my_tournaments.html',
                           upcoming=upcoming_data,
                           live=live_data,
                           completed=completed_data)


@main_bp.route('/match/<int:match_id>')
@login_required
def match_details(match_id):
    match = db.get_or_404(Match, match_id)
    tournament = match.tournament

    # Check if current user is participating in this tournament with an approved team
    user_team = Team.query.filter_by(tournament_id=tournament.id, captain_id=current_user.id).first()
    is_admin = getattr(current_user, 'is_admin', False)
    is_eligible = is_admin or (user_team is not None and user_team.status == 'APPROVED')

    # Automatic Release Check:
    # If release datetime has arrived and credentials exist, ensure room_published is True
    if match.room_id and match.room_password and not match.room_published:
        if match.effective_room_status == 'PUBLISHED':
            match.room_published = True
            match.room_status = 'PUBLISHED'

            # Send notification to approved teams if not already sent
            approved_teams = Team.query.filter_by(tournament_id=tournament.id, status='APPROVED').all()
            for t in approved_teams:
                existing_notif = Notification.query.filter_by(
                    user_id=t.captain_id,
                    title='🎮 Room Details Available'
                ).filter(Notification.message.like(f"%Match {match.match_number}%")).first()
                if not existing_notif:
                    notif = Notification(
                        user_id=t.captain_id,
                        title='🎮 Room Details Available',
                        message=f'Your Match {match.match_number} room is now open.\n\nRoom ID:\n{match.room_id}\n\nPassword:\n{match.room_password}\n\nOpen Match'
                    )
                    db.session.add(notif)
            db.session.commit()

    # Check existing result submission
    user_result = None
    if user_team:
        user_result = Result.query.filter_by(match_id=match.id, team_id=user_team.id).first()

    return render_template('match.html',
                           match=match,
                           tournament=tournament,
                           user_team=user_team,
                           user_result=user_result,
                           is_eligible=is_eligible)


@main_bp.route('/match/<int:match_id>/room')
@login_required
def match_room_direct(match_id):
    match = db.get_or_404(Match, match_id)
    tournament = match.tournament
    user_team = Team.query.filter_by(tournament_id=tournament.id, captain_id=current_user.id).first()
    is_admin = getattr(current_user, 'is_admin', False)
    is_eligible = is_admin or (user_team is not None and user_team.status == 'APPROVED')

    if not is_eligible:
        flash('Access denied: You must be an approved registered player to view room details.', 'danger')
        return redirect(url_for('main.tournament_details', tournament_id=tournament.id)), 403

    return redirect(url_for('main.match_details', match_id=match.id))


@main_bp.route('/result/submit/<int:match_id>', methods=['GET', 'POST'])
@login_required
def result_submit(match_id):
    match = db.get_or_404(Match, match_id)
    tournament = match.tournament

    user_team = Team.query.filter_by(tournament_id=tournament.id, captain_id=current_user.id).first()
    if not user_team:
        flash('Only registered team captains can submit match results.', 'danger')
        return redirect(url_for('main.match_details', match_id=match.id))

    existing_result = Result.query.filter_by(match_id=match.id, team_id=user_team.id).first()

    if request.method == 'POST':
        try:
            kills = int(request.form.get('kills', 0))
            placement = int(request.form.get('placement', 0))
        except ValueError:
            flash('Please enter valid numbers for kills and placement.', 'danger')
            return render_template('result_submit.html', match=match, team=user_team, result=existing_result)

        if placement < 1 or placement > 100:
            flash('Placement must be between 1 and 100.', 'danger')
            return render_template('result_submit.html', match=match, team=user_team, result=existing_result)

        screenshot_file = request.files.get('screenshot')
        screenshot_filename = existing_result.screenshot if existing_result else ''

        if screenshot_file and screenshot_file.filename and allowed_file(screenshot_file.filename):
            ext = screenshot_file.filename.rsplit('.', 1)[1].lower()
            screenshot_filename = f"result_m{match.id}_t{user_team.id}_{int(datetime.now(timezone.utc).timestamp())}.{ext}"
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], screenshot_filename)
            screenshot_file.save(file_path)
        elif not screenshot_filename:
            flash('A screenshot of the match score screen is required for verification.', 'danger')
            return render_template('result_submit.html', match=match, team=user_team, result=existing_result)

        if existing_result:
            existing_result.kills = kills
            existing_result.placement = placement
            existing_result.screenshot = screenshot_filename
            existing_result.verification_status = 'PENDING VERIFICATION'
        else:
            result = Result(
                match_id=match.id,
                team_id=user_team.id,
                kills=kills,
                placement=placement,
                screenshot=screenshot_filename,
                verification_status='PENDING VERIFICATION'
            )
            db.session.add(result)

        # Notify captain
        notif = Notification(
            user_id=current_user.id,
            title='Result Submitted',
            message=f'Your match result for Match #{match.match_number} ({kills} kills, rank #{placement}) was received and is pending admin verification.'
        )
        db.session.add(notif)
        db.session.commit()

        flash('Result submitted successfully! It is now pending admin verification.', 'success')
        return redirect(url_for('main.match_details', match_id=match.id))

    return render_template('result_submit.html', match=match, team=user_team, result=existing_result)


@main_bp.route('/leaderboard')
@main_bp.route('/leaderboard/<int:tournament_id>')
def leaderboard(tournament_id=None):
    tournaments = Tournament.query.order_by(Tournament.created_at.desc()).all()
    selected_tournament = None

    if tournament_id:
        selected_tournament = db.session.get(Tournament, tournament_id)
    if not selected_tournament and tournaments:
        selected_tournament = tournaments[0]

    leaderboard_data = []
    total_teams = 0
    total_kills = 0
    total_matches = 0

    if selected_tournament:
        teams = Team.query.filter_by(tournament_id=selected_tournament.id, status='APPROVED').all()
        total_teams = len(teams)
        total_matches = Match.query.filter_by(tournament_id=selected_tournament.id, status='Completed').count()

        for team in teams:
            # Get approved results
            approved_results = Result.query.filter_by(team_id=team.id, verification_status='APPROVED').all()
            matches_count = len(approved_results)
            team_kills = sum(r.kills for r in approved_results)
            placement_pts = sum(r.placement_points for r in approved_results)
            kill_pts = sum(r.kill_points for r in approved_results)
            total_pts = sum(r.total_points for r in approved_results)

            total_kills += team_kills

            leaderboard_data.append({
                'team': team,
                'matches': matches_count,
                'kills': team_kills,
                'placement_points': placement_pts,
                'kill_points': kill_pts,
                'total_points': total_pts
            })

        # Sort order specified by project requirements:
        # 1. Total Points DESC
        # 2. Kill Points DESC
        # 3. Placement Points DESC
        leaderboard_data.sort(key=lambda x: (x['total_points'], x['kill_points'], x['placement_points']), reverse=True)

        for index, row in enumerate(leaderboard_data):
            row['rank'] = index + 1

    return render_template('leaderboard.html',
                           tournaments=tournaments,
                           selected_tournament=selected_tournament,
                           leaderboard=leaderboard_data,
                           total_teams=total_teams,
                           total_kills=total_kills,
                           total_matches=total_matches)


@main_bp.route('/notifications')
@login_required
def notifications():
    user_notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return render_template('notifications.html', notifications=user_notifications)


@main_bp.route('/notifications/read/<int:notif_id>', methods=['POST'])
@login_required
def mark_notification_read(notif_id):
    notif = db.get_or_404(Notification, notif_id)
    if notif.user_id == current_user.id:
        notif.is_read = True
        db.session.commit()
    return redirect(url_for('main.notifications'))


@main_bp.route('/notifications/read-all', methods=['POST'])
@login_required
def mark_all_notifications_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    flash('All notifications marked as read.', 'info')
    return redirect(url_for('main.notifications'))


@main_bp.route('/support', methods=['GET', 'POST'])
@login_required
def support():
    if request.method == 'POST':
        category = request.form.get('category', 'Other')
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()

        if not subject or not message:
            flash('Subject and message are required to submit a complaint.', 'danger')
            return redirect(url_for('main.support'))

        complaint = Complaint(
            user_id=current_user.id,
            category=category,
            subject=subject,
            message=message,
            status='OPEN'
        )
        db.session.add(complaint)
        db.session.commit()

        flash('Your support ticket has been submitted. Our team will review it shortly.', 'success')
        return redirect(url_for('main.support'))

    user_complaints = Complaint.query.filter_by(user_id=current_user.id).order_by(Complaint.created_at.desc()).all()
    return render_template('support.html', complaints=user_complaints)
