import sqlalchemy as sa # type: ignore
import sqlalchemy.orm as so # type: ignore
from app import create_app, db
from app.models import User, Post, Notification

app = create_app()


@app.shell_context_processor
def make_shell_context():
    return {'sa': sa, 'so': so, 'db': db, 'User': User, 'Post': Post,
             "Notification": Notification}