"""Application entry point and database management CLI."""

import sys
from app import create_app
from app.extensions import db
from app.models import seed_categories

app = create_app()


@app.cli.command('init-db')
def init_db_command():
    """Create database tables and idempotently seed default categories."""
    db.create_all()
    seed_categories(db.session)
    print("Database tables created and categories seeded successfully.")


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'init-db':
        with app.app_context():
            db.create_all()
            seed_categories(db.session)
            print("Database tables created and categories seeded successfully.")
    else:
        app.run(host='127.0.0.1', port=5000, debug=True)
