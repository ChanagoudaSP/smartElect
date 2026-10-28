from app import create_app
from app.models.models import Election
from datetime import datetime

app = create_app()

with app.app_context():
    elections = Election.query.all()
    now = datetime.utcnow()
    print('Current time:', now)
    print('\nElections:')
    for e in elections:
        print(f'Title: {e.title}')
        print(f'Start: {e.start_date}')
        print(f'End: {e.end_date}')
        print(f'Is Active: {e.is_active}')
        print(f'Is Currently Active: {e.is_currently_active}')
        print(f'Current Status: {e.current_status}')
        print('-' * 50)
