from flask import Blueprint, render_template, abort
from app.models import Registration  # maybe for stats
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
    # If POST, handle contact form submission (send email)
    return render_template("contact.html")

@main_bp.route("/become-exhibitor")
def become_exhibitor():
    # Explanation, benefits, link to exhibitor registration form
    return render_template("become_exhibitor.html")
