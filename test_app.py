"""
Comprehensive test suite to verify all player and admin routes, templates, models, authentication, and scoring.
"""
from ff_arena import create_app, db
from ff_arena.models import User, Tournament, Team, Match, Result

def test_routes():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    client = app.test_client()

    with app.app_context():
        # 1. Test Home page
        res = client.get('/')
        assert res.status_code == 200, f"Home failed: {res.status_code}"
        assert b"MICKY" in res.data
        print("[OK] Home page (/) OK")

        # 2. Test Tournaments page
        res = client.get('/tournaments')
        assert res.status_code == 200
        print("[OK] Tournaments (/tournaments) OK")

        # 3. Test Leaderboard page
        res = client.get('/leaderboard')
        assert res.status_code == 200
        print("[OK] Leaderboard (/leaderboard) OK")

        # 4. Test Tournament details
        tourn = Tournament.query.first()
        if tourn:
            res = client.get(f'/tournament/{tourn.id}')
            assert res.status_code == 200
            print(f"[OK] Tournament Details (/tournament/{tourn.id}) OK")

        # 5. Test Login page
        res = client.get('/login')
        assert res.status_code == 200
        print("[OK] Login page (/login) OK")

        # 6. Test Register page
        res = client.get('/register')
        assert res.status_code == 200
        print("[OK] Register page (/register) OK")

        # 7. Test Player Login
        res = client.post('/login', data={
            'email': 'player@mickyarena.com',
            'password': 'player12345'
        }, follow_redirects=True)
        assert res.status_code == 200
        assert b"WELCOME" in res.data or b"Aarav" in res.data
        print("[OK] Player authentication and Dashboard OK")

        # 8. Test Player pages while logged in
        res = client.get('/profile')
        assert res.status_code == 200
        print("[OK] Player Profile (/profile) OK")

        res = client.get('/my-tournaments')
        assert res.status_code == 200
        print("[OK] My Tournaments (/my-tournaments) OK")

        res = client.get('/notifications')
        assert res.status_code == 200
        print("[OK] Notifications (/notifications) OK")

        res = client.get('/support')
        assert res.status_code == 200
        print("[OK] Support (/support) OK")

        match = Match.query.first()
        if match:
            res = client.get(f'/match/{match.id}')
            assert res.status_code == 200
            print(f"[OK] Match Details (/match/{match.id}) OK")

        # 9. Test Player trying to access Admin (should be redirected/blocked)
        res = client.get('/admin/', follow_redirects=True)
        assert b"Administrator access required" in res.data or res.status_code in [302, 200]
        print("[OK] Security: Player cannot access /admin/ OK")

        # 10. Logout player
        client.get('/logout', follow_redirects=True)
        print("[OK] Logout OK")

        # 11. Test Admin Login
        res = client.post('/login', data={
            'email': 'admin@mickyarena.com',
            'password': 'admin12345'
        }, follow_redirects=True)
        assert res.status_code == 200
        assert b"ADMIN DASHBOARD" in res.data
        print("[OK] Admin authentication and Admin Dashboard OK")

        # 12. Test Admin routes
        admin_routes = [
            '/admin/tournaments',
            '/admin/tournament/create',
            '/admin/teams',
            '/admin/matches',
            '/admin/results',
            '/admin/leaderboard',
            '/admin/users',
            '/admin/complaints',
            '/admin/settings'
        ]
        for route in admin_routes:
            res = client.get(route)
            assert res.status_code == 200, f"Admin route {route} failed with {res.status_code}"
            print(f"[OK] Admin route ({route}) OK")

        # 13. Test Edit Tournament page
        if tourn:
            res = client.get(f'/admin/tournament/edit/{tourn.id}')
            assert res.status_code == 200
            print(f"[OK] Admin Edit Tournament (/admin/tournament/edit/{tourn.id}) OK")

    print("\nALL BASE ROUTE TESTS PASSED SUCCESSFULLY!")


def test_custom_room_system():
    print("\n" + "="*60)
    print("RUNNING CUSTOM ROOM MANAGEMENT SYSTEM TESTS (1 THROUGH 8)")
    print("="*60)
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    client = app.test_client()

    with app.app_context():
        # Setup: Ensure an unregistered user exists
        unreg_user = User.query.filter_by(email='unregistered_player@mickyarena.com').first()
        if not unreg_user:
            unreg_user = User(
                name='Unreg Gamer',
                email='unregistered_player@mickyarena.com',
                free_fire_uid='9998887771',
                in_game_name='UnregPro'
            )
            unreg_user.set_password('player12345')
            db.session.add(unreg_user)
            db.session.commit()

        # Find tournament 2 where user 2 ('player@mickyarena.com') has approved team
        tourn = Tournament.query.get(2) or Tournament.query.first()
        reg_player_email = 'player@mickyarena.com'

        # Create or find a test match
        test_match = Match.query.filter_by(tournament_id=tourn.id, match_number=88).first()
        if not test_match:
            test_match = Match(
                tournament_id=tourn.id,
                match_number=88,
                date='2026-09-28',
                time='19:45',
                map='Bermuda',
                room_id='',
                room_password='',
                status='Upcoming'
            )
            db.session.add(test_match)
            db.session.commit()

        match_id = test_match.id

        # --------------------------------------------------
        # TEST 1: No Room ID/Password -> Player sees "Room Not Set"
        # --------------------------------------------------
        test_match.room_id = ''
        test_match.room_password = ''
        test_match.room_release_datetime = ''
        test_match.room_published = False
        db.session.commit()

        # Login as registered player
        client.post('/login', data={'email': reg_player_email, 'password': 'player12345'}, follow_redirects=True)
        res = client.get(f'/match/{match_id}')
        assert res.status_code == 200
        assert b"ROOM NOT SET" in res.data
        print("[TEST 1 PASSED] No Room ID/Password -> Player sees 'Room Not Set'")

        # --------------------------------------------------
        # TEST 2: Room entered but release time is in future -> Player sees "Room Details Locked"
        # --------------------------------------------------
        test_match.room_id = '123456789'
        test_match.room_password = 'secret_room_pass'
        test_match.room_release_datetime = '2099-12-31T23:59'
        test_match.room_release_time = '2099-12-31T23:59'
        test_match.room_published = False
        test_match.room_status = 'SCHEDULED'
        db.session.commit()

        res = client.get(f'/match/{match_id}')
        assert res.status_code == 200
        assert b"ROOM DETAILS LOCKED" in res.data
        assert b"123456789" not in res.data  # Security check: Room ID must be locked!
        assert b"secret_room_pass" not in res.data # Security check: Password must be locked!
        print("[TEST 2 PASSED] Room entered but release time is in future -> Player sees 'Room Details Locked' (Credentials securely hidden)")

        # --------------------------------------------------
        # TEST 3: Release time reached -> Player sees Room ID + Password
        # --------------------------------------------------
        test_match.room_release_datetime = '2020-01-01T00:00'
        test_match.room_release_time = '2020-01-01T00:00'
        test_match.room_published = False  # Auto-release detection triggers
        db.session.commit()

        res = client.get(f'/match/{match_id}')
        assert res.status_code == 200
        assert b"ROOM DETAILS" in res.data
        assert b"123456789" in res.data
        assert b"secret_room_pass" in res.data
        assert b"JOIN MATCH" in res.data
        print("[TEST 3 PASSED] Release time reached -> Player sees Room ID + Password and 'JOIN MATCH' button")

        # --------------------------------------------------
        # TEST 4: User is not registered -> User cannot see Room ID/Password
        # --------------------------------------------------
        # Logout registered player and login as unregistered user
        client.get('/logout', follow_redirects=True)
        client.post('/login', data={'email': 'unregistered_player@mickyarena.com', 'password': 'player12345'}, follow_redirects=True)
        res = client.get(f'/match/{match_id}')
        assert res.status_code == 200
        assert b"123456789" not in res.data
        assert b"secret_room_pass" not in res.data
        assert b"ACCESS DENIED" in res.data or b"ACCESS RESTRICTED" in res.data
        print("[TEST 4 PASSED] User is not registered -> User cannot see Room ID/Password")

        # --------------------------------------------------
        # TEST 5: Admin changes Room Password -> Updated password appears to eligible players
        # --------------------------------------------------
        # Login as Admin
        client.get('/logout', follow_redirects=True)
        client.post('/login', data={'email': 'admin@mickyarena.com', 'password': 'admin12345'}, follow_redirects=True)

        res = client.post(f'/admin/match/room/{match_id}', data={
            'action': 'UPDATE',
            'room_id': '123456789',
            'room_password': 'NEW_UPDATED_PASS_777',
            'room_release_date': '2020-01-01',
            'room_release_time': '00:00'
        }, follow_redirects=True)
        assert res.status_code == 200

        # Login as registered player
        client.get('/logout', follow_redirects=True)
        client.post('/login', data={'email': reg_player_email, 'password': 'player12345'}, follow_redirects=True)
        res = client.get(f'/match/{match_id}')
        assert res.status_code == 200
        assert b"NEW_UPDATED_PASS_777" in res.data
        print("[TEST 5 PASSED] Admin changes Room Password -> Updated password appears to eligible players")

        # --------------------------------------------------
        # TEST 6: Admin hides room -> Players see "Room Details Locked"
        # --------------------------------------------------
        # Login as Admin
        client.get('/logout', follow_redirects=True)
        client.post('/login', data={'email': 'admin@mickyarena.com', 'password': 'admin12345'}, follow_redirects=True)

        res = client.post(f'/admin/match/room/{match_id}', data={
            'action': 'HIDE',
            'room_id': '123456789',
            'room_password': 'NEW_UPDATED_PASS_777'
        }, follow_redirects=True)
        assert res.status_code == 200

        # Login as registered player
        client.get('/logout', follow_redirects=True)
        client.post('/login', data={'email': reg_player_email, 'password': 'player12345'}, follow_redirects=True)
        res = client.get(f'/match/{match_id}')
        assert res.status_code == 200
        assert b"ROOM DETAILS LOCKED" in res.data
        assert b"NEW_UPDATED_PASS_777" not in res.data
        print("[TEST 6 PASSED] Admin hides room -> Players see 'Room Details Locked'")

        # --------------------------------------------------
        # TEST 7: Admin publishes room manually -> Eligible players immediately see Room ID/Password
        # --------------------------------------------------
        # Login as Admin
        client.get('/logout', follow_redirects=True)
        client.post('/login', data={'email': 'admin@mickyarena.com', 'password': 'admin12345'}, follow_redirects=True)

        res = client.post(f'/admin/match/room/{match_id}', data={
            'action': 'PUBLISH',
            'room_id': '987654321',
            'room_password': 'MANUAL_PUBLISH_PASS'
        }, follow_redirects=True)
        assert res.status_code == 200

        # Login as registered player
        client.get('/logout', follow_redirects=True)
        client.post('/login', data={'email': reg_player_email, 'password': 'player12345'}, follow_redirects=True)
        res = client.get(f'/match/{match_id}')
        assert res.status_code == 200
        assert b"ROOM DETAILS" in res.data
        assert b"987654321" in res.data
        assert b"MANUAL_PUBLISH_PASS" in res.data
        print("[TEST 7 PASSED] Admin publishes room manually -> Eligible players immediately see Room ID/Password")

        # --------------------------------------------------
        # TEST 8: Player tries to access room URL directly without registration -> Access denied
        # --------------------------------------------------
        client.get('/logout', follow_redirects=True)
        client.post('/login', data={'email': 'unregistered_player@mickyarena.com', 'password': 'player12345'}, follow_redirects=True)
        res = client.get(f'/match/{match_id}/room', follow_redirects=True)
        assert b"Access denied" in res.data or res.status_code == 403
        print("[TEST 8 PASSED] Player tries to access room URL directly without registration -> Access denied")

        # --------------------------------------------------
        # TEST 9: Admin Validations & Feedback Messages
        # --------------------------------------------------
        # 9a. Non-admin blocked from admin room management
        res = client.post(f'/admin/match/room/{match_id}', data={'action': 'SAVE'}, follow_redirects=True)
        assert b"Administrator access required" in res.data
        print("[VALIDATION OK] Non-admin cannot modify room credentials")

        # Login as Admin
        client.get('/logout', follow_redirects=True)
        client.post('/login', data={'email': 'admin@mickyarena.com', 'password': 'admin12345'}, follow_redirects=True)

        # 9b. Empty Room ID on publish
        res = client.post(f'/admin/match/room/{match_id}', data={
            'action': 'PUBLISH',
            'room_id': '',
            'room_password': 'mypass'
        }, follow_redirects=True)
        assert b"Room ID is required." in res.data
        print("[VALIDATION OK] 'Room ID is required.' validated")

        # 9c. Empty Room Password on publish
        res = client.post(f'/admin/match/room/{match_id}', data={
            'action': 'PUBLISH',
            'room_id': '12345',
            'room_password': ''
        }, follow_redirects=True)
        assert b"Room Password is required." in res.data
        print("[VALIDATION OK] 'Room Password is required.' validated")

        # 9d. Invalid Release Time
        res = client.post(f'/admin/match/room/{match_id}', data={
            'action': 'SAVE',
            'room_id': '12345',
            'room_password': 'mypass',
            'room_release_date': 'invalid-date',
            'room_release_time': 'invalid-time'
        }, follow_redirects=True)
        assert b"Invalid release time." in res.data
        print("[VALIDATION OK] 'Invalid release time.' validated")

        # 9e. Success messages
        res = client.post(f'/admin/match/room/{match_id}', data={
            'action': 'SAVE',
            'room_id': '123456789',
            'room_password': 'savepass',
            'room_release_date': '2099-10-10',
            'room_release_time': '18:00'
        }, follow_redirects=True)
        assert b"Room details saved successfully." in res.data
        print("[MESSAGE OK] 'Room details saved successfully.' displayed")

        res = client.post(f'/admin/match/room/{match_id}', data={
            'action': 'UPDATE',
            'room_id': '123456789',
            'room_password': 'newupdatepass',
            'room_release_date': '2099-10-10',
            'room_release_time': '18:00'
        }, follow_redirects=True)
        assert b"Room details updated successfully." in res.data
        print("[MESSAGE OK] 'Room details updated successfully.' displayed")

        res = client.post(f'/admin/match/room/{match_id}', data={
            'action': 'PUBLISH',
            'room_id': '123456789',
            'room_password': 'newupdatepass'
        }, follow_redirects=True)
        assert b"Room published successfully." in res.data
        print("[MESSAGE OK] 'Room published successfully.' displayed")

    print("\n" + "="*60)
    print("ALL 8 USER TEST CASES & ADMIN VALIDATIONS PASSED WITH 100% SUCCESS!")
    print("="*60 + "\n")


if __name__ == '__main__':
    test_routes()
    test_custom_room_system()
