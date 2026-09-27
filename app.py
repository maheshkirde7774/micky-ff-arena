import os
from ff_arena import create_app, db
from ff_arena.models import Setting

app = create_app()

with app.app_context():
    db.create_all()

    # Safe auto-migration for match table columns if running on an existing DB
    try:
        from sqlalchemy import text
        with db.engine.connect() as conn:
            cols = [row[1] for row in conn.execute(text("PRAGMA table_info(match)")).fetchall()]
            columns_to_add = [
                ('room_release_datetime', "TEXT DEFAULT ''"),
                ('room_status', "TEXT DEFAULT 'NOT SET'"),
                ('room_published', "INTEGER DEFAULT 0"),
                ('created_at', "DATETIME"),
                ('updated_at', "DATETIME")
            ]
            for col_name, col_def in columns_to_add:
                if col_name not in cols:
                    conn.execute(text(f"ALTER TABLE match ADD COLUMN {col_name} {col_def}"))
            conn.execute(text("UPDATE match SET created_at = datetime('now') WHERE created_at = '' OR created_at IS NULL"))
            conn.execute(text("UPDATE match SET updated_at = datetime('now') WHERE updated_at = '' OR updated_at IS NULL"))
            conn.commit()
    except Exception:
        pass

    # Initialize default settings if not present
    if not Setting.get_setting('kill_points'):
        Setting.set_setting('kill_points', '1')
    if not Setting.get_setting('placement_points'):
        Setting.set_setting('placement_points', '15,12,10,8,6,5,4,3,2,1')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
