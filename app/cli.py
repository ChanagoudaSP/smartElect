import click
from flask.cli import with_appcontext
from app.models.models import User
from app import db


@click.command('create-admin')
@click.argument('email')
@click.argument('password')
@click.argument('first_name')
@click.argument('last_name')
@click.argument('national_id')
@with_appcontext
def create_admin(email, password, first_name, last_name, national_id):
    """Create an admin user without any face-registration requirement."""
    user = User.query.filter_by(email=email).first()
    if user:
        click.echo('Email already registered')
        return

    user = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        national_id=national_id,
        is_admin=True,
        is_verified=True,
    )
    user.set_password(password)

    try:
        db.session.add(user)
        db.session.commit()
        click.echo(f'Admin user {email} created successfully')
    except Exception as exc:
        db.session.rollback()
        click.echo(f'Error creating admin user: {exc}')
