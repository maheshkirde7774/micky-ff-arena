from functools import wraps
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from ff_arena import db
from ff_arena.models import User, Tournament, Team, Match, Result, Notification, Complaint, Setting

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Administrator access required.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


def calculate_match_score(placement, kills):
    """
    Calculate placement points, kill points, and total points based on configurable settings.
    Default:
    1st = 15, 2nd = 12, 3rd = 10, 4th = 8, 5th = 6, 6th = 5, 7th = 4, 8th = 3, 9th = 2, 10th = 1
    1 Kill = 1 Point (or configurable multiplier)
    """
    kill_multiplier = float(Setting.get_setting('kill_points', '1'))
    placement_str = Setting.get_setting('placement_points', '15,12,10,8,6,5,4,3,2,1')

    try:
        pts_list = [int(p.strip()) for p in placement_str.split(',') if p.strip()]
    except Exception:
        pts_list = [15, 12, 10, 8, 6, 5, 4, 3, 2, 1]

    if 1 <= placement <= len(pts_list):
        placement_pts = pts_list[placement - 1]
    else:
        placement_pts = 0

    kill_pts = int(kills * kill_multiplier)
    total_pts = placement_pts + kill_pts
    return placement_pts, kill_pts, total_pts


# ==========================================
# ADMIN DASHBOARD
# ==========================================
@admin_bp.route('/')
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    total_users = User.query.count()
    total_teams = Team.query.count()
    active_tournaments = Tournament.query.filter(Tournament.status.in_(['REGISTRATION OPEN', 'LIVE'])).count()
    completed_tournaments = Tournament.query.filter_by(status='COMPLETED').count()
    total_matches = Match.query.count()
    pending_results = Result.query.filter_by(verification_status='PENDING VERIFICATION').count()

    recent_teams = Team.query.order_by(Team.created_at.desc()).limit(5).all()
    recent_results = Result.query.order_by(Result.created_at.desc()).limit(5).all()
    recent_complaints = Complaint.query.order_by(Complaint.created_at.desc()).limit(5).all()

    return render_template('admin/dashboard.html',
                           total_users=total_users,
                           total_teams=total_teams,
                           active_tournaments=active_tournaments,
                           completed_tournaments=completed_tournaments,
                           total_matches=total_matches,
                           pending_results=pending_results,
                           recent_teams=recent_teams,
                           recent_results=recent_results,
                           recent_complaints=recent_complaints)


# ==========================================
# TOURNAMENTS
# ==========================================
@admin_bp.route('/tournaments')
@admin_required
def tournaments():
    status_filter = request.args.get('status', 'ALL').upper()
    query = Tournament.query

    if status_filter != 'ALL':
        query = query.filter_by(status=status_filter)

    tournaments_list = query.order_by(Tournament.created_at.desc()).all()
    return render_template('admin/tournaments.html', tournaments=tournaments_list, active_tab=status_filter)


@admin_bp.route('/tournament/create', methods=['GET', 'POST'])
@admin_required
def create_tournament():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        banner = request.form.get('banner', '').strip()
        description = request.form.get('description', '').strip()
        date = request.form.get('date', '').strip()
        time = request.form.get('time', '').strip()
        entry_fee = float(request.form.get('entry_fee', 0.0) or 0.0)
        prize_pool = float(request.form.get('prize_pool', 0.0) or 0.0)
        max_teams = int(request.form.get('max_teams', 48) or 48)
        game_mode = request.form.get('game_mode', 'Squad')
        map_name = request.form.get('map', 'Bermuda')
        rules = request.form.get('rules', '').strip()
        status = request.form.get('status', 'REGISTRATION OPEN')

        if not name or not date or not time:
            flash('Tournament Name, Date, and Time are required.', 'danger')
            return render_template('admin/create_tournament.html')

        tournament = Tournament(
            name=name,
            banner=banner,
            description=description,
            date=date,
            time=time,
            entry_fee=entry_fee,
            prize_pool=prize_pool,
            max_teams=max_teams,
            game_mode=game_mode,
            map=map_name,
            rules=rules,
            status=status
        )
        db.session.add(tournament)
        db.session.commit()

        flash(f'Tournament "{name}" created successfully!', 'success')
        return redirect(url_for('admin.tournaments'))

    return render_template('admin/create_tournament.html')


@admin_bp.route('/tournament/edit/<int:tournament_id>', methods=['GET', 'POST'])
@admin_required
def edit_tournament(tournament_id):
    tournament = db.get_or_404(Tournament, tournament_id)

    if request.method == 'POST':
        tournament.name = request.form.get('name', '').strip()
        tournament.banner = request.form.get('banner', '').strip()
        tournament.description = request.form.get('description', '').strip()
        tournament.date = request.form.get('date', '').strip()
        tournament.time = request.form.get('time', '').strip()
        tournament.entry_fee = float(request.form.get('entry_fee', 0.0) or 0.0)
        tournament.prize_pool = float(request.form.get('prize_pool', 0.0) or 0.0)
        tournament.max_teams = int(request.form.get('max_teams', 48) or 48)
        tournament.game_mode = request.form.get('game_mode', 'Squad')
        tournament.map = request.form.get('map', 'Bermuda')
        tournament.rules = request.form.get('rules', '').strip()
        tournament.status = request.form.get('status', tournament.status)

        db.session.commit()
        flash('Tournament updated successfully!', 'success')
        return redirect(url_for('admin.tournaments'))

    return render_template('admin/edit_tournament.html', tournament=tournament)


@admin_bp.route('/tournament/delete/<int:tournament_id>', methods=['POST'])
@admin_required
def delete_tournament(tournament_id):
    tournament = db.get_or_404(Tournament, tournament_id)
    name = tournament.name
    db.session.delete(tournament)
    db.session.commit()
    flash(f'Tournament "{name}" deleted successfully.', 'info')
    return redirect(url_for('admin.tournaments'))


@admin_bp.route('/tournament/status/<int:tournament_id>/<string:new_status>', methods=['POST'])
@admin_required
def set_tournament_status(tournament_id, new_status):
    tournament = db.get_or_404(Tournament, tournament_id)
    tournament.status = new_status
    db.session.commit()

    # Notify registered captains if tournament becomes Live or Completed
    if new_status in ['LIVE', 'COMPLETED']:
        for team in tournament.teams:
            notif = Notification(
                user_id=team.captain_id,
                title=f'Tournament Status: {new_status}',
                message=f'Tournament "{tournament.name}" is now {new_status}. Check match schedules and results.'
            )
            db.session.add(notif)
        db.session.commit()

    flash(f'Status updated to {new_status} for "{tournament.name}".', 'success')
    return redirect(url_for('admin.tournaments'))


# ==========================================
# TEAMS MANAGEMENT
# ==========================================
@admin_bp.route('/teams')
@admin_required
def teams():
    search = request.args.get('search', '').strip()
    query = Team.query

    if search:
        search_filter = f"%{search}%"
        query = query.join(User, Team.captain_id == User.id).filter(
            (Team.team_id.ilike(search_filter)) |
            (Team.team_name.ilike(search_filter)) |
            (User.free_fire_uid.ilike(search_filter)) |
            (Team.player2_uid.ilike(search_filter)) |
            (Team.player3_uid.ilike(search_filter)) |
            (Team.player4_uid.ilike(search_filter))
        )

    all_teams = query.order_by(Team.created_at.desc()).all()
    return render_template('admin/teams.html', teams=all_teams, search=search)


@admin_bp.route('/team/approve/<int:team_id>', methods=['POST'])
@admin_required
def approve_team(team_id):
    team = db.get_or_404(Team, team_id)
    team.status = 'APPROVED'

    # Send Notification to Captain
    notif = Notification(
        user_id=team.captain_id,
        title='Team Approved!',
        message=f'Your squad "{team.team_name}" ({team.team_id}) has been approved for "{team.tournament.name}". Get ready for battle!'
    )
    db.session.add(notif)
    db.session.commit()

    flash(f'Team "{team.team_name}" has been approved.', 'success')
    return redirect(url_for('admin.teams'))


@admin_bp.route('/team/reject/<int:team_id>', methods=['POST'])
@admin_required
def reject_team(team_id):
    team = db.get_or_404(Team, team_id)
    team.status = 'REJECTED'

    notif = Notification(
        user_id=team.captain_id,
        title='Team Registration Rejected',
        message=f'Your squad "{team.team_name}" for "{team.tournament.name}" was not approved. Please contact support if you need assistance.'
    )
    db.session.add(notif)
    db.session.commit()

    flash(f'Team "{team.team_name}" has been rejected.', 'warning')
    return redirect(url_for('admin.teams'))


@admin_bp.route('/team/delete/<int:team_id>', methods=['POST'])
@admin_required
def delete_team(team_id):
    team = db.get_or_404(Team, team_id)
    name = team.team_name
    db.session.delete(team)
    db.session.commit()
    flash(f'Team "{name}" deleted.', 'info')
    return redirect(url_for('admin.teams'))


# ==========================================
# MATCH MANAGEMENT
# ==========================================
@admin_bp.route('/matches', methods=['GET', 'POST'])
@admin_required
def matches():
    tournaments = Tournament.query.order_by(Tournament.created_at.desc()).all()
    
    if request.method == 'POST':
        tournament_id = int(request.form.get('tournament_id'))
        match_number = int(request.form.get('match_number', 1))
        date = request.form.get('date', '').strip()
        time = request.form.get('time', '').strip()
        map_name = request.form.get('map', 'Bermuda').strip()
        room_id = request.form.get('room_id', '').strip()
        room_password = request.form.get('room_password', '').strip()
        room_release_time = request.form.get('room_release_time', '').strip()
        status = request.form.get('status', 'Upcoming')

        match = Match(
            tournament_id=tournament_id,
            match_number=match_number,
            date=date,
            time=time,
            map=map_name,
            room_id=room_id,
            room_password=room_password,
            room_release_time=room_release_time,
            status=status
        )
        db.session.add(match)
        db.session.commit()

        flash(f'Match #{match_number} scheduled successfully!', 'success')
        return redirect(url_for('admin.matches'))

    matches_list = Match.query.order_by(Match.date.desc(), Match.time.asc()).all()
    return render_template('admin/matches.html', matches=matches_list, tournaments=tournaments)


@admin_bp.route('/match/room/<int:match_id>', methods=['POST'])
@admin_required
def manage_match_room(match_id):
    match = db.get_or_404(Match, match_id)
    action = request.form.get('action', '').upper() # SAVE, UPDATE, PUBLISH, HIDE

    room_id = request.form.get('room_id', '').strip()
    room_password = request.form.get('room_password', '').strip()
    release_date = request.form.get('room_release_date', '').strip()
    release_time = request.form.get('room_release_time', '').strip()

    combined_datetime = ''
    if release_date and release_time:
        combined_datetime = f"{release_date}T{release_time}"
    elif release_date:
        combined_datetime = f"{release_date}T{match.time}"
    elif release_time:
        combined_datetime = f"{match.date}T{release_time}"

    old_id = match.room_id
    old_pass = match.room_password

    if action in ['SAVE', 'UPDATE', 'PUBLISH']:
        # Validations
        if action == 'PUBLISH':
            if not room_id:
                flash('Room ID is required.', 'danger')
                return redirect(url_for('admin.matches'))
            if not room_password:
                flash('Room Password is required.', 'danger')
                return redirect(url_for('admin.matches'))

        if combined_datetime:
            try:
                datetime.strptime(combined_datetime[:16], '%Y-%m-%dT%H:%M')
            except Exception:
                flash('Invalid release time.', 'danger')
                return redirect(url_for('admin.matches'))

        match.room_id = room_id
        match.room_password = room_password
        if combined_datetime:
            match.room_release_datetime = combined_datetime
            match.room_release_time = combined_datetime

        if action == 'PUBLISH':
            match.room_published = True
            match.room_status = 'PUBLISHED'

            # Notify registered approved team captains
            for team in match.tournament.teams:
                if team.status == 'APPROVED':
                    notif = Notification(
                        user_id=team.captain_id,
                        title='🎮 Room Details Available',
                        message=f'Your Match {match.match_number} room is now open.\nRoom ID: {match.room_id}\nPassword: {match.room_password}'
                    )
                    db.session.add(notif)

            db.session.commit()
            flash('Room published successfully.', 'success')
            return redirect(url_for('admin.matches'))

        # SAVE or UPDATE
        if not room_id or not room_password:
            match.room_status = 'NOT SET'
            match.room_published = False
        else:
            if match.is_room_released() and match.room_published:
                match.room_status = 'PUBLISHED'
            else:
                match.room_status = 'SCHEDULED'

        # Check if credentials changed to notify players
        credentials_changed = (old_id and room_id and old_id != room_id) or (old_pass and room_password and old_pass != room_password)
        if credentials_changed:
            for team in match.tournament.teams:
                if team.status == 'APPROVED':
                    notif = Notification(
                        user_id=team.captain_id,
                        title='Room Credentials Updated',
                        message=f'Credentials for Match #{match.match_number} ({match.tournament.name}) were updated.\nRoom ID: {match.room_id}\nPassword: {match.room_password}'
                    )
                    db.session.add(notif)

        db.session.commit()
        if action == 'SAVE':
            flash('Room details saved successfully.', 'success')
        else:
            flash('Room details updated successfully.', 'success')
        return redirect(url_for('admin.matches'))

    elif action == 'HIDE':
        match.room_published = False
        if match.room_id and match.room_password:
            match.room_status = 'SCHEDULED'
        else:
            match.room_status = 'NOT SET'
        # If release datetime was in the past, clear it so it doesn't auto-release immediately
        if match.room_release_datetime:
            try:
                clean_time = match.room_release_datetime.replace('T', ' ')
                dt = datetime.strptime(clean_time[:16], '%Y-%m-%d %H:%M')
                if datetime.now() >= dt:
                    match.room_release_datetime = None
                    match.room_release_time = None
            except Exception:
                pass
        db.session.commit()
        flash('Room hidden successfully.', 'info')
        return redirect(url_for('admin.matches'))

    return redirect(url_for('admin.matches'))


@admin_bp.route('/match/edit/<int:match_id>', methods=['POST'])
@admin_required
def edit_match(match_id):
    match = db.get_or_404(Match, match_id)

    old_date = match.date
    old_time = match.time
    old_room_id = match.room_id
    old_password = match.room_password

    match.match_number = int(request.form.get('match_number', match.match_number))
    match.date = request.form.get('date', match.date).strip()
    match.time = request.form.get('time', match.time).strip()
    match.map = request.form.get('map', match.map).strip()
    match.room_id = request.form.get('room_id', '').strip()
    match.room_password = request.form.get('room_password', '').strip()

    release_val = request.form.get('room_release_time', '').strip()
    if release_val:
        match.room_release_time = release_val
        match.room_release_datetime = release_val

    match.status = request.form.get('status', match.status)

    # Sync room status
    if match.status == 'Completed':
        match.room_status = 'COMPLETED'
    elif match.status == 'Live':
        match.room_status = 'LIVE'
    elif not match.room_id or not match.room_password:
        match.room_status = 'NOT SET'
        match.room_published = False
    elif match.room_published:
        match.room_status = 'PUBLISHED'
    else:
        match.room_status = 'SCHEDULED'

    # Notify players if match time changed
    if old_date != match.date or old_time != match.time:
        for team in match.tournament.teams:
            if team.status == 'APPROVED':
                notif = Notification(
                    user_id=team.captain_id,
                    title='Match Time Changed',
                    message=f'Match #{match.match_number} ({match.tournament.name}) has been rescheduled to {match.date} at {match.time}.'
                )
                db.session.add(notif)

    # If password changed
    if old_password and match.room_password and old_password != match.room_password:
        for team in match.tournament.teams:
            if team.status == 'APPROVED':
                notif = Notification(
                    user_id=team.captain_id,
                    title='Room Credentials Updated',
                    message=f'Credentials for Match #{match.match_number} were updated.\nRoom ID: {match.room_id}\nPassword: {match.room_password}'
                )
                db.session.add(notif)

    db.session.commit()
    flash('Room details updated successfully.', 'success')
    return redirect(url_for('admin.matches'))


@admin_bp.route('/match/delete/<int:match_id>', methods=['POST'])
@admin_required
def delete_match(match_id):
    match = db.get_or_404(Match, match_id)
    # Notify registered players
    for team in match.tournament.teams:
        if team.status == 'APPROVED':
            notif = Notification(
                user_id=team.captain_id,
                title='Match Cancelled',
                message=f'Match #{match.match_number} for "{match.tournament.name}" has been cancelled by tournament admin.'
            )
            db.session.add(notif)

    db.session.delete(match)
    db.session.commit()
    flash('Match deleted successfully.', 'info')
    return redirect(url_for('admin.matches'))


# ==========================================
# RESULTS VERIFICATION
# ==========================================
@admin_bp.route('/results')
@admin_required
def results():
    status_filter = request.args.get('status', 'ALL')
    query = Result.query

    if status_filter != 'ALL':
        query = query.filter_by(verification_status=status_filter)

    results_list = query.order_by(Result.created_at.desc()).all()
    return render_template('admin/results.html', results=results_list, active_status=status_filter)


@admin_bp.route('/result/verify/<int:result_id>', methods=['POST'])
@admin_required
def verify_result(result_id):
    result = db.get_or_404(Result, result_id)
    action = request.form.get('action') # 'APPROVE', 'REJECT', 'EDIT'

    if action == 'APPROVE':
        result.verification_status = 'APPROVED'
        placement_pts, kill_pts, total_pts = calculate_match_score(result.placement, result.kills)
        result.placement_points = placement_pts
        result.kill_points = kill_pts
        result.total_points = total_pts

        # Notify team captain
        notif = Notification(
            user_id=result.team.captain_id,
            title='Result Approved! 🏆',
            message=f'Your Match #{result.match.match_number} result was approved! Placement #{result.placement} ({placement_pts} pts) + {result.kills} kills ({kill_pts} pts) = {total_pts} Total Points!'
        )
        db.session.add(notif)
        db.session.commit()
        flash(f'Result for team "{result.team.team_name}" approved! Total points calculated: {total_pts}.', 'success')

    elif action == 'REJECT':
        result.verification_status = 'REJECTED'
        result.placement_points = 0
        result.kill_points = 0
        result.total_points = 0

        notif = Notification(
            user_id=result.team.captain_id,
            title='Result Rejected',
            message=f'Your Match #{result.match.match_number} result was rejected by admin. Please contact support or resubmit with valid screenshot proof.'
        )
        db.session.add(notif)
        db.session.commit()
        flash(f'Result for team "{result.team.team_name}" rejected.', 'warning')

    elif action == 'EDIT':
        try:
            new_kills = int(request.form.get('kills', result.kills))
            new_placement = int(request.form.get('placement', result.placement))
        except ValueError:
            flash('Invalid numbers provided.', 'danger')
            return redirect(url_for('admin.results'))

        result.kills = new_kills
        result.placement = new_placement
        result.verification_status = 'APPROVED'

        placement_pts, kill_pts, total_pts = calculate_match_score(new_placement, new_kills)
        result.placement_points = placement_pts
        result.kill_points = kill_pts
        result.total_points = total_pts

        notif = Notification(
            user_id=result.team.captain_id,
            title='Result Verified (Score Adjusted)',
            message=f'Your Match #{result.match.match_number} result was verified with updated stats: #{new_placement} place, {new_kills} kills -> {total_pts} points.'
        )
        db.session.add(notif)
        db.session.commit()
        flash(f'Score updated and approved: {total_pts} Total Points.', 'success')

    return redirect(url_for('admin.results'))


# ==========================================
# ADMIN LEADERBOARD
# ==========================================
@admin_bp.route('/leaderboard')
@admin_required
def leaderboard():
    tournaments = Tournament.query.order_by(Tournament.created_at.desc()).all()
    tournament_id = request.args.get('tournament_id', type=int)

    selected_tournament = None
    if tournament_id:
        selected_tournament = db.session.get(Tournament, tournament_id)
    if not selected_tournament and tournaments:
        selected_tournament = tournaments[0]

    leaderboard_data = []
    if selected_tournament:
        teams = Team.query.filter_by(tournament_id=selected_tournament.id, status='APPROVED').all()
        for team in teams:
            results = Result.query.filter_by(team_id=team.id, verification_status='APPROVED').all()
            matches_count = len(results)
            team_kills = sum(r.kills for r in results)
            placement_pts = sum(r.placement_points for r in results)
            kill_pts = sum(r.kill_points for r in results)
            total_pts = sum(r.total_points for r in results)

            leaderboard_data.append({
                'team': team,
                'matches': matches_count,
                'kills': team_kills,
                'placement_points': placement_pts,
                'kill_points': kill_pts,
                'total_points': total_pts
            })

        leaderboard_data.sort(key=lambda x: (x['total_points'], x['kill_points'], x['placement_points']), reverse=True)
        for index, row in enumerate(leaderboard_data):
            row['rank'] = index + 1

    return render_template('admin/leaderboard.html',
                           tournaments=tournaments,
                           selected_tournament=selected_tournament,
                           leaderboard=leaderboard_data)


# ==========================================
# USERS MANAGEMENT
# ==========================================
@admin_bp.route('/users')
@admin_required
def users():
    search = request.args.get('search', '').strip()
    query = User.query

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (User.name.ilike(search_filter)) |
            (User.email.ilike(search_filter)) |
            (User.free_fire_uid.ilike(search_filter)) |
            (User.in_game_name.ilike(search_filter))
        )

    all_users = query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=all_users, search=search)


@admin_bp.route('/user/toggle-admin/<int:user_id>', methods=['POST'])
@admin_required
def toggle_admin(user_id):
    if user_id == current_user.id:
        flash('You cannot remove your own admin privileges.', 'warning')
        return redirect(url_for('admin.users'))

    user = db.get_or_404(User, user_id)
    user.is_admin = not user.is_admin
    db.session.commit()

    role = 'Admin' if user.is_admin else 'Player'
    flash(f'Role updated for {user.name}: Now {role}.', 'success')
    return redirect(url_for('admin.users'))


# ==========================================
# COMPLAINTS / SUPPORT INBOX
# ==========================================
@admin_bp.route('/complaints')
@admin_required
def complaints():
    status_filter = request.args.get('status', 'ALL')
    query = Complaint.query

    if status_filter != 'ALL':
        query = query.filter_by(status=status_filter)

    all_complaints = query.order_by(Complaint.created_at.desc()).all()
    return render_template('admin/complaints.html', complaints=all_complaints, active_status=status_filter)


@admin_bp.route('/complaint/reply/<int:complaint_id>', methods=['POST'])
@admin_required
def reply_complaint(complaint_id):
    complaint = db.get_or_404(Complaint, complaint_id)
    reply = request.form.get('admin_reply', '').strip()
    status = request.form.get('status', 'RESOLVED')

    complaint.admin_reply = reply
    complaint.status = status

    # Notify player
    notif = Notification(
        user_id=complaint.user_id,
        title=f'Support Ticket Update: {complaint.subject}',
        message=f'Admin replied: "{reply}" (Status: {status})'
    )
    db.session.add(notif)
    db.session.commit()

    flash(f'Reply sent to {complaint.user.name}. Status set to {status}.', 'success')
    return redirect(url_for('admin.complaints'))


# ==========================================
# SCORING SETTINGS
# ==========================================
@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_required
def settings():
    if request.method == 'POST':
        kill_points = request.form.get('kill_points', '1').strip()
        placement_points = request.form.get('placement_points', '15,12,10,8,6,5,4,3,2,1').strip()

        Setting.set_setting('kill_points', kill_points)
        Setting.set_setting('placement_points', placement_points)

        flash('Scoring settings updated successfully!', 'success')
        return redirect(url_for('admin.settings'))

    kill_points = Setting.get_setting('kill_points', '1')
    placement_points = Setting.get_setting('placement_points', '15,12,10,8,6,5,4,3,2,1')

    return render_template('admin/settings.html',
                           kill_points=kill_points,
                           placement_points=placement_points)
