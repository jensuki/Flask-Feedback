from flask import Flask, render_template, redirect, session, flash
from flask_debugtoolbar import DebugToolbarExtension
from models import db, connect_db, User, Feedback
from forms import RegisterForm, LoginForm, FeedbackForm
from werkzeug.exceptions import Unauthorized

app = Flask(__name__)

# configs
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///feedback_db'
app.config['SQLALCHEMY_ECHO'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
app.config['SECRET_KEY'] = 's3cr3tk3y'

debug = DebugToolbarExtension(app)

connect_db(app)
db.create_all()

@app.route('/')
def homepage():
    """Home page that redirects to register form"""
    return redirect('/register')

@app.route('/register', methods=['GET', 'POST'])
def register_user():
    """Display registration form + handle form submission"""
    form = RegisterForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        email = form.email.data
        first_name = form.first_name.data
        last_name = form.last_name.data

        new_user = User.register(username, password, email, first_name, last_name)

        db.session.add(new_user)
        db.session.commit()
        # store user in the session
        session['username'] = new_user.username

        flash(f"Welcome {new_user.username}", "success")

        return redirect(f'/users/{username}')

    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login_user():
    """Display login form + authenticate user credentials"""
    form = LoginForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        user = User.authenticate(username, password)

        if user:
            session['username'] = user.username
            flash('Welcome back!', 'success')
            return redirect(f'/users/{username}')
        flash("Invalid credentials. Please try again.")

    return render_template('login.html', form=form)


# @app.route('/secret')
# def secret_page():
#     """Gated page only for authenticated in users"""
#     if 'username' not in session:
#         flash('Please login first!', 'warning')
#         return redirect('/login')
#     else:
#         return render_template('secret.html')

@app.route('/logout')
def logout():
    """Log the user out"""

    if 'username' in session:
        flash("Goodbye!", "secondary")
        session.pop('username', None)

        return redirect('/')

@app.route('/users/<username>')
def user_profile(username):
    """Page view for logged in users"""
    if 'username' not in session or session['username'] != username:
        flash('Please login to view this page', 'warning')
        return redirect('/login')
    else:
        user = User.query.get_or_404(username)
        feedbacks = Feedback.query.filter_by(username=username).all()
        return render_template('user_profile.html', user=user, feedbacks=feedbacks)

@app.route('/users/<username>/delete', methods=['POST'])
def delete_user(username):
    """Delete user + their fedbacks from db"""

    if 'username' not in session or session['username'] != username:
        return redirect('/login')

    user = User.query.filter_by(username=username).first()
    Feedback.query.filter_by(username=username).delete()
    db.session.delete(user)
    db.session.commit()

    session.pop('username')
    return redirect('/login')


@app.route('/users/<username>/feedback/add', methods=['GET', 'POST'])
def add_feedback(username):
    """Display form to add feedback + handle form submission"""
    if 'username' not in session or session['username'] != username:
        flash('Please log in to add feedback.', 'warning')
        return redirect('/login')

    form = FeedbackForm()

    if form.validate_on_submit():
        title = form.title.data
        content = form.content.data
        username = session['username']

        new_feedback = Feedback(
            title=title,
            content=content,
            username=username
        )

        db.session.add(new_feedback)
        db.session.commit()
        flash('Feedback posted!', 'success')

        return redirect(f'/users/{username}')

    return render_template('add_feedback.html',form=form)

@app.route('/feedback/<int:feedback_id>/update', methods=['GET', 'POST'])
def update_feedback(feedback_id):
    """Display prepopulated form to update feedback"""
    feedback = Feedback.query.get_or_404(feedback_id)

    if 'username' not in session or session['username'] != feedback.username:
        raise Unauthorized()

    form = FeedbackForm(obj=feedback)

    if form.validate_on_submit():
        feedback.title = form.title.data
        feedback.content = form.content.data

        db.session.commit()

        return redirect(f'/users/{session["username"]}')

    # if form submission fails, rerender edit form
    return render_template('edit_feedback.html', form=form, feedback=feedback)

@app.route('/feedback/<int:feedback_id>/delete', methods=['POST'])
def delete_feedback(feedback_id):
    """Delete a feedback posted by logged in user"""
    feedback = Feedback.query.get_or_404(feedback_id)

    if 'username' not in session or session['username'] != feedback.username:
        raise Unauthorized()

    # else
    db.session.delete(feedback)
    db.session.commit()
    flash('Feedback deleted', 'success')

    return redirect(f'/users/{session["username"]}')

