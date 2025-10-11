from flask import Blueprint, render_template, abort, request, flash, redirect, url_for
from app.models import Registration  # maybe for stats
from app.forms import ContactForm
from app.services.contact_service import ContactService
from app.extensions import db

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def index():
    # You might want to pass featured speakers, news, etc. to home
    # e.g., latest news posts, top speakers
    return render_template("index.html")

@main_bp.route("/about")
def about():
    return render_template("about.html")

@main_bp.route("/speakers")
def speakers():
    # Pass a list of speakers from DB (or stub) to template
    return render_template("speakers.html")

@main_bp.route("/agenda")
def agenda():
    return render_template("agenda.html")

@main_bp.route("/news")
def news():
    # List of news posts (title, excerpt, link)
    return render_template("news.html")

@main_bp.route("/news/<slug>")
def news_detail(slug):
    # Fetch single news post by slug; if missing, 404
    # e.g. post = News.query.filter_by(slug=slug).first_or_404()
    return render_template("news_detail.html")

@main_bp.route("/contact", methods=["GET", "POST"])
def contact():
    form = ContactForm()

    if form.validate_on_submit():
        # Collect the form data
        form_data = {
            "first_name": form.first_name.data.strip(),
            "last_name": form.last_name.data.strip(),
            "email": form.email.data.strip(),
            "phone": form.phone.data.strip(),
            "message": form.message.data.strip(),
        }

        # Attempt to send the message
        success = ContactService.send_contact_message(form_data)

        if success:
            flash("Thank you! Your message has been sent successfully.", "success")
            return redirect(url_for("main.contact"))
        else:
            flash("Sorry, we couldn’t send your message. Please try again later.", "error")

    elif request.method == "POST":
        flash("Please correct the errors below and try again.", "error")

    return render_template("contact.html", form=form)

@main_bp.route("/become-exhibitor")
def become_exhibitor():
    # Explanation, benefits, link to exhibitor registration form
    return render_template("become_exhibitor.html")
