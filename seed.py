"""
Database Seeding Script for Micky FF Arena.
Run this script to initialize the database with admin, test player, tournaments, matches, and demo results:
python seed.py
"""
from datetime import datetime
from ff_arena import create_app, db
from ff_arena.models import User, Tournament, Team, Match, Result, Notification, Complaint, Setting

app = create_app()

def seed_database():
    with app.app_context():
        # Ensure all tables exist
        db.create_all()

        # Seed Settings
        if not Setting.get_setting('kill_points'):
            Setting.set_setting('kill_points', '1')
        if not Setting.get_setting('placement_points'):
            Setting.set_setting('placement_points', '15,12,10,8,6,5,4,3,2,1')

        # Create Admin
        admin = User.query.filter_by(email='admin@mickyarena.com').first()
        if not admin:
            admin = User(
                name='Arena Master Micky',
                email='admin@mickyarena.com',
                free_fire_uid='100000001',
                in_game_name='MICKY_CHIEF',
                is_admin=True
            )
            admin.set_password('admin12345')
            db.session.add(admin)
            print("Created Admin: admin@mickyarena.com / admin12345")

        # Create Test Player
        player = User.query.filter_by(email='player@mickyarena.com').first()
        if not player:
            player = User(
                name='Aarav Sharma',
                email='player@mickyarena.com',
                free_fire_uid='248910342',
                in_game_name='SHADOW_SNIPER',
                is_admin=False
            )
            player.set_password('player12345')
            db.session.add(player)
            print("Created Player: player@mickyarena.com / player12345")

        # Create Rival Player
        rival = User.query.filter_by(email='vikram@mickyarena.com').first()
        if not rival:
            rival = User(
                name='Vikram Rajput',
                email='vikram@mickyarena.com',
                free_fire_uid='319482019',
                in_game_name='GHOST_RIDER',
                is_admin=False
            )
            rival.set_password('player12345')
            db.session.add(rival)
            print("Created Rival: vikram@mickyarena.com / player12345")

        db.session.commit()

        # Seed Tournaments if empty
        if Tournament.query.count() == 0:
            t1 = Tournament(
                name='Bermuda Blitz Championship S4',
                banner='https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=1200&q=80',
                description='The premier competitive squad tournament of the season. 48 squads compete for a ₹50,000 prize pool and champion glory.',
                date='2026-10-15',
                time='18:00',
                entry_fee=0.0,
                prize_pool=50000.0,
                max_teams=48,
                game_mode='Squad',
                map='Bermuda',
                rules='1. Emulators strictly forbidden.\n2. All players must record POV or submit end-game score screenshot.\n3. Room ID will be unlocked 15 minutes prior to match launch.\n4. Toxic behaviour results in immediate DQ.',
                status='REGISTRATION OPEN'
            )

            t2 = Tournament(
                name='Purgatory Squad Masters Live',
                banner='https://images.unsplash.com/photo-1511512578047-dfb367046420?auto=format&fit=crop&w=1200&q=80',
                description='High-intensity tactical tournament on Purgatory. Top tier squads clashing live for glory and cash prizes.',
                date='2026-09-28',
                time='20:30',
                entry_fee=100.0,
                prize_pool=25000.0,
                max_teams=24,
                game_mode='Squad',
                map='Purgatory',
                rules='Official esports scoring. 1 kill = 1 pt. 1st = 15 pts, 2nd = 12 pts, 3rd = 10 pts. No hacking or macro scripts allowed.',
                status='LIVE'
            )

            t3 = Tournament(
                name='Kalahari Sandstorm Showdown S3',
                banner='https://images.unsplash.com/photo-1538481199705-c710c4e965fc?auto=format&fit=crop&w=1200&q=80',
                description='Completed championship featuring the fiercest survivors in the Kalahari desert.',
                date='2026-09-15',
                time='19:00',
                entry_fee=50.0,
                prize_pool=15000.0,
                max_teams=24,
                game_mode='Squad',
                map='Kalahari',
                rules='Classic Battle Royale rules. Top 3 teams rewarded.',
                status='COMPLETED'
            )

            db.session.add_all([t1, t2, t3])
            db.session.commit()
            print("Seeded 3 Tournaments.")

            # Seed Teams for Player and Rival in t1 and t2
            team1 = Team(
                team_id='MFF-2026-001',
                tournament_id=t2.id,
                captain_id=player.id,
                team_name='SOUL ASSASSINS',
                player2_name='Rohan Verma',
                player2_uid='849302184',
                player3_name='Kabir Khan',
                player3_uid='958473829',
                player4_name='Zayn Malik',
                player4_uid='473829104',
                substitute_name='Amit Singh',
                substitute_uid='384920194',
                status='APPROVED'
            )

            team2 = Team(
                team_id='MFF-2026-002',
                tournament_id=t2.id,
                captain_id=rival.id,
                team_name='GODLIKE ELITE',
                player2_name='Sameer Sen',
                player2_uid='284910294',
                player3_name='Harsh V',
                player3_uid='594839201',
                player4_name='Deepak J',
                player4_uid='748392019',
                substitute_name='Ravi K',
                substitute_uid='102938475',
                status='APPROVED'
            )

            team3 = Team(
                team_id='MFF-2026-003',
                tournament_id=t3.id,
                captain_id=player.id,
                team_name='SOUL SQUAD V1',
                player2_name='Rohan Verma',
                player2_uid='849302184',
                player3_name='Kabir Khan',
                player3_uid='958473829',
                player4_name='Zayn Malik',
                player4_uid='473829104',
                status='APPROVED'
            )

            db.session.add_all([team1, team2, team3])
            db.session.commit()
            print("Seeded Teams.")

            # Seed Matches
            # Match 1 for Live tournament (already released room)
            m1 = Match(
                tournament_id=t2.id,
                match_number=1,
                date='2026-09-28',
                time='20:30',
                map='Purgatory',
                room_id='84920194',
                room_password='mickywinner99',
                room_release_time='2026-09-01 10:00', # In the past, so revealed!
                status='Live'
            )

            # Match 2 for Live tournament (scheduled later)
            m2 = Match(
                tournament_id=t2.id,
                match_number=2,
                date='2026-09-28',
                time='21:30',
                map='Purgatory',
                room_id='84920195',
                room_password='mickyroundtwo',
                room_release_time='2026-10-30 21:15', # In the future, so hidden!
                status='Upcoming'
            )

            # Match for Completed tournament
            m3 = Match(
                tournament_id=t3.id,
                match_number=1,
                date='2026-09-15',
                time='19:00',
                map='Kalahari',
                room_id='73829104',
                room_password='sandstormgame',
                room_release_time='2026-09-15 18:45',
                status='Completed'
            )

            db.session.add_all([m1, m2, m3])
            db.session.commit()
            print("Seeded Matches.")

            # Seed Results for Completed tournament
            r1 = Result(
                match_id=m3.id,
                team_id=team3.id,
                kills=14,
                placement=1,
                placement_points=15,
                kill_points=14,
                total_points=29,
                screenshot='default_screenshot.png',
                verification_status='APPROVED'
            )

            # Result for Live match #1 (Pending verification by admin)
            r2 = Result(
                match_id=m1.id,
                team_id=team1.id,
                kills=8,
                placement=2,
                placement_points=0,
                kill_points=0,
                total_points=0,
                screenshot='sample_score.png',
                verification_status='PENDING VERIFICATION'
            )

            db.session.add_all([r1, r2])

            # Notifications
            n1 = Notification(
                user_id=player.id,
                title='Match Room Released! 🎮',
                message='Room ID and Password are now available for Purgatory Squad Masters Match #1! Copy your credentials and enter lobby now.'
            )
            n2 = Notification(
                user_id=player.id,
                title='Tournament Reminder',
                message='Your registered tournament "Bermuda Blitz Championship S4" kicks off soon. Check your squad roster.'
            )
            db.session.add_all([n1, n2])

            # Complaint
            c1 = Complaint(
                user_id=player.id,
                category='Match',
                subject='Ping spike during Round 1',
                message='We noticed higher latency on the Singapore lobby server. Can we use the Mumbai server for upcoming rounds?',
                status='OPEN'
            )
            db.session.add(c1)

            db.session.commit()
            print("Seeded Results, Notifications, and Complaints.")

        print("\nAll seed operations completed successfully!")

if __name__ == '__main__':
    seed_database()
