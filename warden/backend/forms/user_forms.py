from flask_wtf import FlaskForm
from flask_login import current_user
from wtforms.validators import DataRequired, EqualTo, ValidationError, Optional, Length
from wtforms import StringField, SubmitField, SelectField, PasswordField
from wtforms.fields import DateField
from models.user_models import User
from werkzeug.security import check_password_hash


class RegistrationForm(FlaskForm):
    username = StringField("Username",
                           validators=[DataRequired(),
                                       Length(min=2, max=20)],
                           render_kw={"placeholder": "choose a username"})
    password = PasswordField("Password",
                             validators=[DataRequired()],
                             render_kw={"placeholder": "password"})
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password")],
        render_kw={"placeholder": "confirm password"})
    submit = SubmitField("create account")

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError("User already exists.")


class LoginForm(FlaskForm):
    username = StringField("Username",
                           validators=[DataRequired()],
                           render_kw={"placeholder": "username"})
    password = PasswordField("Password",
                             validators=[DataRequired()],
                             render_kw={"placeholder": "password"})
    submit = SubmitField('login')


class UpdateAccountForm(FlaskForm):
    old_password = PasswordField("current password",
                                 validators=[DataRequired()],
                                 render_kw={"placeholder": "current password"})
    password = PasswordField("New Password",
                             validators=[DataRequired()],
                             render_kw={"placeholder": "new password"})
    confirm_password = PasswordField(
        "confirm password",
        validators=[DataRequired(), EqualTo("password")],
        render_kw={"placeholder": "confirm password"})
    submit = SubmitField("change password")

    def validate_old_password(self, old_password):
        user = User.query.filter_by(username=current_user.username).first()
        if not check_password_hash(user.password, self.old_password.data):
            raise ValidationError("Incorrect Current Password. Try Again.")
