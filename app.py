import os
from datetime import date, timedelta
from dotenv import load_dotenv
from flask import jsonify
from flask import Flask, render_template, request, flash, redirect, url_for, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func

from forms import RegisterForm, LoginForm, ApplicationForm
from models import db, User, JobApplication

load_dotenv()

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key')
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"

# --- Flask-Mail Configuration ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

db.init_app(app)
mail = Mail(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "info"

with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        existing_user = db.session.execute(
            db.select(User).where(User.email == form.email.data)
        ).scalar()
        if existing_user:
            flash("Email already registered. Please log in instead.")
            return redirect(url_for('login'))
        hashed_password = generate_password_hash(form.password.data)
        new_user = User(
            email=form.email.data,
            password_hash=hashed_password
        )
        db.session.add(new_user)
        db.session.commit()
        flash("Account created successfully. Please log in.")
        return redirect(url_for('login'))
    return render_template("register.html", form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        existing_user = db.session.execute(
            db.select(User).where(User.email == form.email.data)
        ).scalar()

        if not existing_user:
            flash("Invalid email.")
            return redirect(url_for('login'))

        if not check_password_hash(existing_user.password_hash, form.password.data):
            flash("Invalid password.")
            return redirect(url_for('login'))

        login_user(existing_user)
        flash("Logged in successfully.")
        return redirect(url_for('dashboard'))

    return render_template("login.html", form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.")
    return redirect(url_for('home'))


@app.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    form = ApplicationForm()
    if form.validate_on_submit():
        file_name = None
        if form.file.data:
            file = form.file.data
            file_name = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, file_name))
        new_job_application = JobApplication(
            company=form.company.data,
            role=form.role.data,
            date_applied=form.date_applied.data,
            deadline=form.deadline.data,
            status=form.status.data,
            job_link=form.job_link.data,
            notes=form.notes.data,
            user_id=current_user.id,
            file_name=file_name
        )
        db.session.add(new_job_application)
        db.session.commit()
        flash("Application created successfully.")
        return redirect(url_for('dashboard'))
    return render_template("add_edit.html", form=form)


@app.route('/dashboard')
@login_required
def dashboard():
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '')
    page = request.args.get('page', 1, type=int)

    query = JobApplication.query.filter_by(user_id=current_user.id)

    if search:
        query = query.filter(JobApplication.company.ilike(f'%{search}%'))

    if status:
        query = query.filter_by(status=status)

    query = query.order_by(JobApplication.date_applied.desc())
    pagination = query.paginate(page=page, per_page=10)

    status_counts = db.session.execute(
        db.select(JobApplication.status, func.count(JobApplication.id))
        .where(JobApplication.user_id == current_user.id)
        .group_by(JobApplication.status)
    ).all()
    status_dict = {status: count for status, count in status_counts}

    return render_template(
        "dashboard.html",
        applications=pagination.items,
        pagination=pagination,
        search=search,
        status=status,
        status_dict=status_dict,
        today=date.today()
    )


@app.route('/edit/<int:app_id>', methods=['GET', 'POST'])
@login_required
def edit(app_id):
    application = JobApplication.query.get_or_404(app_id)
    if application.user_id != current_user.id:
        abort(403)
    form = ApplicationForm(obj=application)
    if form.validate_on_submit():
        application.company = form.company.data
        application.role = form.role.data
        application.date_applied = form.date_applied.data
        application.status = form.status.data
        application.job_link = form.job_link.data
        application.notes = form.notes.data
        application.deadline = form.deadline.data
        if form.file.data:
            file = form.file.data
            file_name = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, file_name))
            application.file_name = file_name
        db.session.commit()
        flash("Application updated successfully.")
        return redirect(url_for('dashboard'))
    return render_template("add_edit.html", form=form)


@app.route('/delete/<int:app_id>', methods=['POST'])
@login_required
def delete(app_id):
    application = JobApplication.query.get_or_404(app_id)
    if application.user_id != current_user.id:
        abort(403)
    db.session.delete(application)
    db.session.commit()
    flash("Application deleted.")
    return redirect(url_for('dashboard'))


@app.route('/send-stale-summary')
@login_required
def send_stale_summary():
    fourteen_days_ago = date.today() - timedelta(days=14)
    stale_apps = JobApplication.query.filter(
        JobApplication.user_id == current_user.id,
        JobApplication.date_applied <= fourteen_days_ago,
        JobApplication.status.notin_(['Offer', 'Rejected'])
    ).all()

    if not stale_apps:
        flash("You have no stale applications!")
        return redirect(url_for('dashboard'))

    body = f"Hello {current_user.email},\n\nHere is your summary of job applications untouched for 2+ weeks:\n\n"
    for app_item in stale_apps:
        body += f"• {app_item.company} — {app_item.role} (Applied: {app_item.date_applied.strftime('%b %d, %Y')})\n"

    body += "\nLog in to JobTrail to update their statuses!"

    msg = Message(
        subject="📋 JobTrail: Weekly Stale Applications Summary",
        recipients=[current_user.email],
        body=body
    )
    try:
        mail.send(msg)
        flash("Stale application summary emailed successfully!")
    except Exception as e:
        flash(f"Failed to send email: {str(e)}")

    return redirect(url_for('dashboard'))


@app.route('/api/applications')
@login_required
def api_applications():
    applications = db.session.execute(
        db.select(JobApplication).filter_by(user_id=current_user.id)
    ).scalars().all()
    return jsonify([a.to_dict() for a in applications])


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403


@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500


if __name__ == '__main__':
    app.run(debug=True, port=8000)