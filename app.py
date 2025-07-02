from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-please-change')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    tasks = db.relationship('Task', backref='user', lazy=True)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.Date)
    priority = db.Column(db.String(20), default='Medium')  # Low, Medium, High
    tags = db.Column(db.String(255))  # Comma-separated tags
    status = db.Column(db.String(20), default='pending')  # pending, completed
    pinned = db.Column(db.Boolean, nullable=False, default=False)
    starred = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
@login_required
def index():
    filter_status = request.args.get('status', 'all')
    filter_priority = request.args.get('priority', 'all')
    filter_tag = request.args.get('tag', '')
    tasks_query = Task.query.filter_by(user_id=current_user.id)
    if filter_status != 'all':
        tasks_query = tasks_query.filter_by(status=filter_status)
    if filter_priority != 'all':
        tasks_query = tasks_query.filter_by(priority=filter_priority)
    if filter_tag:
        tasks_query = tasks_query.filter(Task.tags.ilike(f'%{filter_tag}%'))
    # Pinned/starred tasks first, then by due date, then by updated_at
    tasks = tasks_query.order_by(Task.pinned.desc(), Task.starred.desc(), Task.due_date.asc().nullslast(), Task.updated_at.desc()).all()
    return render_template('index.html', tasks=tasks, filter_status=filter_status, filter_priority=filter_priority, filter_tag=filter_tag)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_task():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        due_date = request.form.get('due_date')
        priority = request.form.get('priority', 'Medium')
        tags = request.form.get('tags', '')
        pinned = bool(request.form.get('pinned'))
        starred = bool(request.form.get('starred'))
        due_date_obj = datetime.strptime(due_date, '%Y-%m-%d').date() if due_date else None
        task = Task(title=title, description=description, due_date=due_date_obj, priority=priority, tags=tags, pinned=pinned, starred=starred, user_id=current_user.id)
        db.session.add(task)
        db.session.commit()
        flash('Task added successfully!')
        return redirect(url_for('index'))
    return render_template('add_task.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_task(id):
    task = Task.query.get_or_404(id)
    if task.user_id != current_user.id:
        flash('You do not have permission to edit this task', 'danger')
        return redirect(url_for('index'))
    if request.method == 'POST':
        task.title = request.form.get('title')
        task.description = request.form.get('description')
        due_date = request.form.get('due_date')
        task.due_date = datetime.strptime(due_date, '%Y-%m-%d').date() if due_date else None
        task.priority = request.form.get('priority', 'Medium')
        task.tags = request.form.get('tags', '')
        task.pinned = bool(request.form.get('pinned'))
        task.starred = bool(request.form.get('starred'))
        db.session.commit()
        flash('Task updated successfully!')
        return redirect(url_for('index'))
    return render_template('edit_task.html', task=task)

@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_task(id):
    task = Task.query.get_or_404(id)
    if task.user_id != current_user.id:
        flash('You do not have permission to delete this task', 'danger')
        return redirect(url_for('index'))
    db.session.delete(task)
    db.session.commit()
    flash('Task deleted successfully!')
    return redirect(url_for('index'))

@app.route('/toggle_status/<int:id>', methods=['POST'])
@login_required
def toggle_status(id):
    task = Task.query.get_or_404(id)
    if task.user_id != current_user.id:
        flash('You do not have permission to update this task', 'danger')
        return redirect(url_for('index'))
    
    if task.status == 'pending':
        task.status = 'completed'
        db.session.delete(task) # Delete the task when marked as completed
        flash('Task completed and deleted successfully!', 'success')
    else:
        # This part might not be reachable if tasks are deleted on completion
        # But keep it for robustness if logic changes later
        task.status = 'pending'
        flash('Task status updated to pending!', 'info')
    
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/pin/<int:id>', methods=['POST'])
@login_required
def pin_task(id):
    task = Task.query.get_or_404(id)
    if task.user_id != current_user.id:
        flash('You do not have permission to pin this task', 'danger')
        return redirect(url_for('index'))
    task.pinned = not task.pinned
    db.session.commit()
    flash(('Task pinned!' if task.pinned else 'Task unpinned!'), 'success')
    return redirect(url_for('index'))

@app.route('/star/<int:id>', methods=['POST'])
@login_required
def star_task(id):
    task = Task.query.get_or_404(id)
    if task.user_id != current_user.id:
        flash('You do not have permission to star this task', 'danger')
        return redirect(url_for('index'))
    task.starred = not task.starred
    db.session.commit()
    flash(('Task starred!' if task.starred else 'Task unstarred!'), 'success')
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html', current_year=datetime.utcnow().year)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5003) 