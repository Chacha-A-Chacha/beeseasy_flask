"""
Contact form for general inquiries, aligned with Bee East Africa Symposium.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email, Length


class ContactForm(FlaskForm):
    """Form for visitors to send general inquiries."""

    first_name = StringField("First Name", validators=[DataRequired(), Length(max=100)])
    last_name = StringField("Last Name", validators=[DataRequired(), Length(max=100)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    phone = StringField("Phone", validators=[Length(max=30)])
    message = TextAreaField("Message", validators=[DataRequired(), Length(max=2000)])

    submit = SubmitField("Send Message")
