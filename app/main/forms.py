from flask_wtf import FlaskForm 
from flask_babel import _, lazy_gettext as _l
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, ValidationError,Length
import sqlalchemy as sa
from app import db
from app.models import User
from flask_wtf.file import FileField, FileAllowed


class EditProfileForm(FlaskForm):
    username = StringField(_l("username"), validators=[DataRequired()])
    about_me = TextAreaField(_l("About me"), validators=[Length(min=0, max=250)])
    avatar = FileField("Profile Picture", validators=[FileAllowed(["jpg", "jpeg", "png"],
                                                                  "Image only!")])
    submit = SubmitField(_l("Submit"))

    def __init__(self, original_username, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_username = original_username
    
    def validate_username(self, username):
        if username.data != self.original_username:
            user = db.session.scalar(sa.select(User).where(
                User.username == self.username.data))
            if user is not None:
                raise ValidationError(_("Please use a different username."))


class EmptyForm(FlaskForm):
    submit = SubmitField(_l("Submit"))


class DeletePostForm(FlaskForm):
    submit = SubmitField("Delete Post")


class PostForm(FlaskForm):
    post = TextAreaField(_l("Say Something"), validators=[
        DataRequired(), Length(min=1, max=5000)
    ]) 
    submit = SubmitField(_l("Submit"))


class MessageForm(FlaskForm):
    message = TextAreaField(_l("Message"), validators=[
        DataRequired()])
    submit = SubmitField(_l("Send"))


class FeedbackForm(FlaskForm):
    content = TextAreaField('Feedback', validators=[
        DataRequired(), Length(min=1, max=1000)
        ])
    submit = SubmitField('Submit Feedback')