
from flask import current_app
from flask_wtf import FlaskForm
from wtforms.validators import DataRequired, EqualTo, ValidationError, Optional, Length
from warden_modules import fx_list
from wtforms import StringField, SubmitField, SelectField, PasswordField
from wtforms.fields.html5 import DateField
from models import User
from flask_wtf.file import FileField, FileAllowed


# Form used to register new users and save password
class RegistrationForm(FlaskForm):
    username = StringField("Username",
                           validators=[DataRequired(),
                                       Length(min=2, max=20)],
                           render_kw={"placeholder": "Choose a Username"})
    password = PasswordField("Password", validators=[DataRequired()],
                             render_kw={"placeholder": "Password"})
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(),
                                        EqualTo("password")],
        render_kw={"placeholder": "Confirm Password"})
    submit = SubmitField("Create Login")

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError("User already exists. Please Login.")


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()], render_kw={"placeholder": "Username"})
    password = PasswordField("Password", validators=[DataRequired()], render_kw={"placeholder": "Password"})
    submit = SubmitField("Login")


class TradeForm(FlaskForm):
    trade_date = DateField("Trade Date", [DataRequired()])
    trade_asset_ticker = StringField("Asset Ticker", [Optional()])
    trade_source = StringField("Source", [Optional()])
    trade_operation = SelectField(
        "Operation",
        [Optional()],
        choices=[("B", "Buy"), ("S", "Sell")],
    )
    trade_quantity = StringField("Quantity", [Optional()])
    trade_currency = SelectField("Trade Currency", [Optional()],
                                 choices=fx_list())
    trade_price = StringField("Price", [Optional()])
    trade_fees = StringField("Fees", default=0)
    trade_account = StringField("Custody Account")
    cash_value = StringField("Total Cash Amount", default=0)
    trade_notes = StringField("Trade Notes and Tags")

    submit = SubmitField("Insert New Trade")

    def validate_trade_account(self, trade_account):
        acc = trade_account.data
        if acc == "":
            raise ValidationError("Trade Account cannot be empty")

    def validate_trade_asset_ticker(self, trade_asset_ticker):
        ticker = trade_asset_ticker.data
        if ticker == "":
            raise ValidationError("Ticker cannot be empty")

    def validate_trade_price(self, trade_price):
        try:
            price = float(trade_price.data)
        except ValueError:
            raise ValidationError("Invalid Price")
        if price < 0:
            raise ValidationError("Price has to be a positive number")
        if price == "":
            raise ValidationError("Price can't be empty")

    def validate_trade_quantity(self, trade_quantity):
        try:
            quant = float(trade_quantity.data)
        except ValueError:
            raise ValidationError("Invalid Quantity")
        if quant < 0:
            raise ValidationError("Quantity has to be a positive number")
        if quant == "":
            raise ValidationError("Quantity can't be empty")


class ImportCSV(FlaskForm):
    csvfile = FileField('Import CSV File', validators=[FileAllowed(['csv'])])
    submit = SubmitField('Open File')

    def validate_csvfile(sef, csvfile):
        if csvfile.data is None:
            raise ValidationError("Please select a file")
