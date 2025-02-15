import os
import logging
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Progress, ChatHistory, ContentRecommendation, Quiz, QuizQuestion, QuizAttempt, StudySession, LearningPath # Added LearningPath import
from utils import get_ai_response, generate_recommendations

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize database
db.init_app(app)

# Login manager configuration
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except Exception as e:
        logger.error(f"Error loading user: {e}")
        return None

# Create tables
with app.app_context():
    try:
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            user = User.query.filter_by(username=username).first()
            if user:
                flash('Username already exists')
                return redirect(url_for('register'))

            new_user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password)
            )
            db.session.add(new_user)
            db.session.commit()
            logger.info(f"New user registered: {username}")
            flash('Registration successful!')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error during registration: {e}")
            flash('An error occurred during registration')
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        try:
            user = User.query.filter_by(username=username).first()
            if user and check_password_hash(user.password_hash, password):
                login_user(user)
                logger.info(f"User logged in: {username}")
                return redirect(url_for('dashboard'))

            flash('Invalid username or password')
        except Exception as e:
            logger.error(f"Error during login: {e}")
            flash('An error occurred during login')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        # Get user's progress data
        progress = Progress.query.filter_by(user_id=current_user.id).all()

        # Get learning path data
        learning_path = LearningPath.query.filter_by(user_id=current_user.id).first()
        if learning_path:
            path_milestones = [{
                'title': topic['title'],
                'description': topic['description'],
                'progress': topic['progress'],
                'completed': topic['progress'] == 100
            } for topic in learning_path.topics]
        else:
            path_milestones = []

        # Calculate quiz statistics
        quiz_attempts = QuizAttempt.query.filter_by(user_id=current_user.id).all()
        quiz_stats = {
            'average_score': sum(attempt.score for attempt in quiz_attempts) / len(quiz_attempts) if quiz_attempts else 0,
            'completed_count': len(quiz_attempts)
        }

        # Calculate study time statistics
        study_sessions = StudySession.query.filter_by(
            user_id=current_user.id,
            status='completed'
        ).all()

        from datetime import datetime, timedelta
        week_ago = datetime.utcnow() - timedelta(days=7)

        weekly_hours = sum(
            (session.end_time - session.start_time).total_seconds() / 3600
            for session in study_sessions
            if session.start_time >= week_ago
        )

        total_hours = sum(
            (session.end_time - session.start_time).total_seconds() / 3600
            for session in study_sessions
        )

        study_stats = {
            'weekly_hours': round(weekly_hours, 1),
            'total_hours': round(total_hours, 1)
        }

        # Get personalized recommendations
        recommendations = ContentRecommendation.query.filter_by(user_id=current_user.id).all()

        return render_template('dashboard.html',
                             progress=progress,
                             learning_path=path_milestones,
                             quiz_stats=quiz_stats,
                             study_stats=study_stats,
                             recommendations=recommendations)
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        flash('Error loading dashboard data')
        return redirect(url_for('index'))

@app.route('/chat')
@login_required
def chat():
    return render_template('chat.html')

@app.route('/api/chat', methods=['POST'])
@login_required
def process_chat():
    try:
        message = request.json.get('message')
        response = get_ai_response(message)

        chat_history = ChatHistory(
            user_id=current_user.id,
            message=message,
            response=response
        )
        db.session.add(chat_history)
        db.session.commit()

        return jsonify({'response': response})
    except Exception as e:
        logger.error(f"Error processing chat: {e}")
        db.session.rollback()
        return jsonify({'error': 'An error occurred processing your message'}), 500

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/api/update-progress', methods=['POST'])
@login_required
def update_progress():
    try:
        topic = request.json.get('topic')
        score = request.json.get('score')

        progress = Progress(
            user_id=current_user.id,
            topic=topic,
            score=score
        )
        db.session.add(progress)
        db.session.commit()

        recommendations = generate_recommendations(current_user.id, topic, score)
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Error updating progress: {e}")
        db.session.rollback()
        return jsonify({'error': 'An error occurred updating progress'}), 500


@app.route('/quizzes')
@login_required
def quiz_list():
    try:
        # Get unique topics from quizzes
        topics = db.session.query(Quiz.topic).distinct().all()
        topics = [topic[0] for topic in topics]

        # Get all quizzes
        quizzes = Quiz.query.all()

        return render_template('quiz/list.html', quizzes=quizzes, topics=topics)
    except Exception as e:
        logger.error(f"Error loading quiz list: {e}")
        flash('Error loading quizzes')
        return redirect(url_for('dashboard'))

@app.route('/api/quizzes')
@login_required
def get_quizzes():
    try:
        topic = request.args.get('topic')
        difficulty = request.args.get('difficulty')

        query = Quiz.query

        if topic:
            query = query.filter_by(topic=topic)
        if difficulty:
            query = query.filter_by(difficulty=difficulty)

        quizzes = query.all()

        return jsonify({
            'quizzes': [{
                'id': quiz.id,
                'title': quiz.title,
                'description': quiz.description,
                'difficulty': quiz.difficulty,
                'question_count': len(quiz.questions)
            } for quiz in quizzes]
        })
    except Exception as e:
        logger.error(f"Error fetching quizzes: {e}")
        return jsonify({'error': 'Failed to fetch quizzes'}), 500

@app.route('/quiz/take/<int:quiz_id>')
@login_required
def take_quiz(quiz_id):
    try:
        quiz = Quiz.query.get_or_404(quiz_id)
        return render_template('quiz/take.html', quiz=quiz)
    except Exception as e:
        logger.error(f"Error loading quiz {quiz_id}: {e}")
        flash('Error loading quiz')
        return redirect(url_for('quiz_list'))

@app.route('/api/quiz/<int:quiz_id>/submit', methods=['POST'])
@login_required
def submit_quiz():
    try:
        quiz_id = request.json.get('quiz_id')
        answers = request.json.get('answers')

        quiz = Quiz.query.get_or_404(quiz_id)

        # Calculate score
        total_points = sum(q.points for q in quiz.questions)
        earned_points = 0

        for question_id, answer in answers.items():
            question = QuizQuestion.query.get(question_id)
            if question and answer == question.correct_answer:
                earned_points += question.points

        score = (earned_points / total_points) * 100 if total_points > 0 else 0

        # Record attempt
        attempt = QuizAttempt(
            user_id=current_user.id,
            quiz_id=quiz_id,
            score=score,
            answers=answers,
            completed_at=datetime.utcnow()
        )

        db.session.add(attempt)
        db.session.commit()

        return jsonify({
            'score': score,
            'total_questions': len(quiz.questions),
            'correct_answers': sum(1 for q in quiz.questions if answers.get(str(q.id)) == q.correct_answer)
        })
    except Exception as e:
        logger.error(f"Error submitting quiz: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to submit quiz'}), 500

# Add these routes after the existing routes
@app.route('/schedule')
@login_required
def schedule():
    return render_template('schedule/calendar.html')

@app.route('/api/study-sessions', methods=['GET', 'POST'])
@login_required
def study_sessions():
    try:
        if request.method == 'POST':
            data = request.json
            session = StudySession(
                user_id=current_user.id,
                topic=data['topic'],
                start_time=datetime.fromisoformat(data['start_time']),
                end_time=datetime.fromisoformat(data['end_time']),
                notes=data.get('notes')
            )
            db.session.add(session)
            db.session.commit()
            return jsonify({'status': 'success'})

        else:  # GET
            sessions = StudySession.query.filter_by(user_id=current_user.id).all()
            return jsonify([{
                'id': session.id,
                'title': session.topic,
                'start': session.start_time.isoformat(),
                'end': session.end_time.isoformat(),
                'notes': session.notes,
                'status': session.status
            } for session in sessions])

    except Exception as e:
        logger.error(f"Error managing study sessions: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to manage study sessions'}), 500