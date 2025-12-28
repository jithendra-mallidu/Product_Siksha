#!/usr/bin/env python3
"""
Product Siksha Flask Backend
- Authentication with JWT
- Questions API with Company/Date filters
- Google Gemini AI feedback integration
- SQLAlchemy ORM for SQLite (Local) and PostgreSQL (Cloud Run)
"""

import os
import hashlib
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, request, jsonify, g
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import jwt
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, origins=[
    'http://localhost:5173', 
    'http://127.0.0.1:5173',
    'https://productsiksha.vercel.app',
    'https://www.productsiksha.vercel.app'
])

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
# Use DATABASE_URL if set (Cloud Run), otherwise sqlite:///product_siksha.db (Local)
database_url = os.getenv('DATABASE_URL', 'sqlite:///product_siksha.db')
# Handle Postgres URL scheme fix for SQLAlchemy (postgres:// -> postgresql://)
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# ============================================================================
# Models
# ============================================================================

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.String(64)) # Keep as string to match original CSV datatypes for now
    company = db.Column(db.String(120))
    question = db.Column(db.Text)
    question_type = db.Column(db.String(64))
    interview_type = db.Column(db.String(64))
    comments = db.Column(db.Text)
    job_title = db.Column(db.String(120))
    company_normalized = db.Column(db.String(120))
    question_category = db.Column(db.String(64))

class UserProgress(db.Model):
    __tablename__ = 'user_progress'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), primary_key=True)
    is_completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

# ============================================================================
# Helpers
# ============================================================================

def hash_password(password: str) -> str:
    """Hash password with SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()

def token_required(f):
    """Decorator to require valid JWT token."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'Token required'}), 401
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            g.user_id = payload['user_id']
            g.user_email = payload['email']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        return f(*args, **kwargs)
    return decorated

def parse_timestamp(ts_string):
    """Parse timestamp string like '9/7/2022 11:48:35' to datetime."""
    if not ts_string:
        return None
    try:
        # Try M/D/YYYY H:MM:SS format
        return datetime.strptime(ts_string.strip(), '%m/%d/%Y %H:%M:%S')
    except ValueError:
        try:
            # Try M/D/YYYY format (no time)
            return datetime.strptime(ts_string.strip(), '%m/%d/%Y')
        except ValueError:
            try:
                # Try YYYY-MM-DD format
                return datetime.strptime(ts_string.strip(), '%Y-%m-%d')
            except ValueError:
                return None

# ============================================================================
# Routes
# ============================================================================

# Initialize tables (Running this at module level ensures tables exist when running via Gunicorn)
# This is crucial for Cloud Run with SQLite to ensure tables exist after a cold start
with app.app_context():
    try:
        db.create_all()
        print("✅ Database tables created successfully")
    except Exception as e:
        print(f"⚠️ Error creating database tables: {e}")

@app.route('/api/auth/init', methods=['GET'])
def init_tables():
    """Helper to initialize tables if they don't exist (useful for Cloud Run first boot)."""
    try:
        db.create_all()
        return jsonify({'message': 'Database tables initialized successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """Authenticate user and return JWT token."""
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    user = User.query.filter_by(email=email, password_hash=hash_password(password)).first()
    
    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # Generate JWT token
    token = jwt.encode({
        'user_id': user.id,
        'email': user.email,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }, app.config['SECRET_KEY'], algorithm='HS256')
    
    return jsonify({
        'token': token,
        'user': {'id': user.id, 'email': user.email}
    })

@app.route('/api/signup', methods=['POST'])
def signup():
    """Register new user."""
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 400
    
    try:
        new_user = User(email=email, password_hash=hash_password(password))
        db.session.add(new_user)
        db.session.commit()
        
        # Generate JWT token for auto-login
        token = jwt.encode({
            'user_id': new_user.id,
            'email': new_user.email,
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            'token': token,
            'user': {'id': new_user.id, 'email': email},
            'message': 'Account created successfully'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500

@app.route('/api/change-password', methods=['POST'])
def change_password():
    """Change user password."""
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    
    if not email or not current_password or not new_password:
        return jsonify({'error': 'All fields are required'}), 400
        
    if len(new_password) < 6:
        return jsonify({'error': 'New password must be at least 6 characters'}), 400
        
    user = User.query.filter_by(email=email, password_hash=hash_password(current_password)).first()
    
    if not user:
        return jsonify({'error': 'Invalid email or current password'}), 401
        
    try:
        user.password_hash = hash_password(new_password)
        db.session.commit()
        return jsonify({'message': 'Password updated successfully. Please login with your new password.'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Password update failed: {str(e)}'}), 500

@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Get all question categories with counts."""
    # Using SQLAlchemy: SELECT question_category, COUNT(*) ... GROUP BY question_category
    results = db.session.query(
        Question.question_category, db.func.count(Question.id)
    ).filter(
        Question.question_category != None, 
        Question.question_category != ''
    ).group_by(Question.question_category).order_by(db.func.count(Question.id).desc()).all()
    
    categories = []
    for category_name, count in results:
        path = category_name.lower().replace(' & ', '-').replace(' ', '-')
        categories.append({
            'name': category_name,
            'path': path,
            'count': count
        })
    
    return jsonify(categories)

@app.route('/api/companies', methods=['GET'])
def get_companies():
    """Get unique normalized companies for filter dropdown."""
    category = request.args.get('category', '')
    from_date_str = request.args.get('from_date', '')
    to_date_str = request.args.get('to_date', '')
    
    # Map slug to category name
    category_map = {
        'product-design': 'Product Design',
        'execution-metrics': 'Execution & Metrics',
        'product-strategy': 'Product Strategy',
        'behavioral': 'Behavioral',
        'estimation-pricing': 'Estimation & Pricing',
        'technical': 'Technical',
        'other': 'Other'
    }
    category_name = category_map.get(category, category) if category else None
    
    # Base query
    query = Question.query.filter(Question.company_normalized != None, Question.company_normalized != '')
    
    if category_name:
        query = query.filter(Question.question_category == category_name)
    
    # Parse dates for Python-side filtering (since timestamps are strings in DB)
    from_date = None
    to_date = None
    if from_date_str:
        try:
            from_date = datetime.strptime(from_date_str, '%Y-%m-%d')
        except ValueError:
            pass
    if to_date_str:
        try:
            to_date = datetime.strptime(to_date_str, '%Y-%m-%d')
            # Set to end of day
            to_date = to_date.replace(hour=23, minute=59, second=59)
        except ValueError:
            pass
            
    # Execute query
    results = query.with_entities(Question.company_normalized, Question.timestamp).all()
    
    # Process results in Python
    company_counts = {}
    
    for company, timestamp in results:
        # Apply date filter
        if from_date or to_date:
            row_date = parse_timestamp(timestamp)
            if row_date:
                if from_date and row_date < from_date: continue
                if to_date and row_date > to_date: continue
            else:
                continue
        
        company_counts[company] = company_counts.get(company, 0) + 1
    
    # Convert to list and sort
    companies = [{'name': name, 'count': count} for name, count in company_counts.items()]
    companies.sort(key=lambda x: x['count'], reverse=True)
    
    return jsonify(companies)

@app.route('/api/questions/<category>', methods=['GET'])
@token_required
def get_questions(category):
    """Get questions by category with optional filters."""
    category_map = {
        'product-design': 'Product Design',
        'execution-metrics': 'Execution & Metrics',
        'product-strategy': 'Product Strategy',
        'behavioral': 'Behavioral',
        'estimation-pricing': 'Estimation & Pricing',
        'technical': 'Technical',
        'other': 'Other'
    }
    category_name = category_map.get(category, category)
    
    company_filter = request.args.get('company', '')
    from_date_str = request.args.get('from_date', '')
    to_date_str = request.args.get('to_date', '')
    
    # Parse dates
    from_date = None
    to_date = None
    if from_date_str:
        try:
            from_date = datetime.strptime(from_date_str, '%Y-%m-%d')
        except ValueError:
            pass
    if to_date_str:
        try:
            to_date = datetime.strptime(to_date_str, '%Y-%m-%d')
            to_date = to_date.replace(hour=23, minute=59, second=59)
        except ValueError:
            pass
            
    # Build query with join
    # SQL: SELECT q.*, up.is_completed, up.completed_at FROM questions q LEFT JOIN user_progress up ...
    query = db.session.query(Question, UserProgress).outerjoin(
        UserProgress, 
        (UserProgress.question_id == Question.id) & (UserProgress.user_id == g.user_id)
    )
    
    query = query.filter(Question.question_category == category_name)
    
    if company_filter:
        query = query.filter(Question.company_normalized == company_filter)
        
    results = query.all()
    
    final_questions = []
    
    for q, up in results:
        # Date filtering
        if from_date or to_date:
            row_date = parse_timestamp(q.timestamp)
            if row_date:
                if from_date and row_date < from_date: continue
                if to_date and row_date > to_date: continue
            else: continue
            
        q_dict = {
            'id': q.id,
            'timestamp': q.timestamp,
            'company': q.company,
            'question': q.question,
            'question_type': q.question_type,
            'interview_type': q.interview_type,
            'comments': q.comments,
            'job_title': q.job_title,
            'company_normalized': q.company_normalized,
            'question_category': q.question_category,
            'is_completed': up.is_completed if up else False,
            'completed_at': up.completed_at.isoformat() if up and up.completed_at else None
        }
        final_questions.append(q_dict)
        
    # Sorting Logic
    completed_questions = [q for q in final_questions if q['is_completed']]
    uncompleted_questions = [q for q in final_questions if not q['is_completed']]
    
    # Sort completed by completion time (Oldest -> Newest)
    completed_questions.sort(key=lambda x: x.get('completed_at') or '')
    
    # Uncompleted questions - sort by timestamp DESC (Newest first)
    uncompleted_questions.sort(key=lambda q: parse_timestamp(q['timestamp']) or datetime.min, reverse=True)
    
    final_list = completed_questions + uncompleted_questions
    
    return jsonify({
        'category': category_name,
        'count': len(final_list),
        'questions': final_list
    })

@app.route('/api/questions/<int:question_id>/toggle', methods=['POST'])
@token_required
def toggle_question_completion(question_id):
    """Toggle completion status of a question."""
    progress = UserProgress.query.filter_by(user_id=g.user_id, question_id=question_id).first()
    
    new_status = False
    
    if progress:
        # Toggle existing
        progress.is_completed = not progress.is_completed
        progress.completed_at = datetime.utcnow() if progress.is_completed else None
        new_status = progress.is_completed
    else:
        # Create new
        progress = UserProgress(
            user_id=g.user_id, 
            question_id=question_id, 
            is_completed=True, 
            completed_at=datetime.utcnow()
        )
        db.session.add(progress)
        new_status = True
        
    try:
        db.session.commit()
        return jsonify({'question_id': question_id, 'is_completed': new_status})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/feedback', methods=['POST'])
def get_ai_feedback():
    """Get AI feedback on candidate's answer using Google Gemini."""
    data = request.get_json()
    question = data.get('question', '')
    answer = data.get('answer', '')
    prompt = data.get('prompt', 'Please analyze my answer and provide feedback.')
    files = data.get('files', [])  # List of {name, type, base64} objects
    
    if not question:
        return jsonify({'error': 'Question is required'}), 400
    
    # Build context message based on whether there's an answer
    if not answer.strip():
        user_request = f"I haven't written an answer yet. {prompt} Please provide guidance on how to approach this question."
    else:
        user_request = prompt if prompt else 'Please analyze my answer and provide feedback.'
    
    if not GEMINI_API_KEY:
        # Mock feedback for demo mode
        file_mention = f"\n\n*Note: You attached {len(files)} file(s). In demo mode, file analysis is not available.*" if files else ""
        return jsonify({
            'feedback': f'''**AI Feedback** (Demo Mode - No API Key)

Thank you for your message! Here's some structured feedback:

**Your Question Context:**
This is about: {question[:100]}...

**Strengths:**
- You're actively practicing PM interview questions
- Seeking feedback shows growth mindset

**Guidance:**
- Structure your answer using frameworks like CIRCLES, STAR, or RICE
- Include specific metrics and success measures
- Consider multiple stakeholder perspectives

**Next Steps:**
- Try answering the question before asking for feedback
- Focus on quantifiable outcomes{file_mention}

*Note: Connect your Google Gemini API key for personalized AI feedback.*''',
            'model': 'demo'
        })
    
    try:
        import google.generativeai as genai
        import base64
        
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Use vision model if files are attached
        if files:
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
        else:
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        system_prompt = """You are an expert PM interview coach having a conversation with a candidate. 
Your role is to help them prepare for product management interviews through constructive, actionable feedback.

Be conversational and encouraging but honest. Adapt your response to what the candidate asks:
- If they share an answer, provide structured feedback (Strengths, Areas for Improvement, Suggested Framework)
- If they ask a clarifying question, answer it directly
- If they share a diagram or image, analyze it and provide feedback on their visual communication
- Keep responses focused and not too long

Remember the context: This is about the PM interview question provided."""

        # Build the content for Gemini
        content_parts = []
        
        # Add system context and question
        context = f"""{system_prompt}

**Interview Question:** {question}

**Candidate's Answer/Message:** {answer if answer else '(No answer provided yet)'}

**Candidate's Request:** {user_request}
"""
        content_parts.append(context)
        
        # Add any attached images for multimodal analysis
        for file_data in files:
            if file_data.get('type', '').startswith('image/') and file_data.get('base64'):
                try:
                    # Extract base64 data (remove data URL prefix if present)
                    base64_str = file_data['base64']
                    if ',' in base64_str:
                        base64_str = base64_str.split(',')[1]
                    
                    image_bytes = base64.b64decode(base64_str)
                    content_parts.append({
                        'mime_type': file_data['type'],
                        'data': image_bytes
                    })
                except Exception as img_error:
                    print(f"Error processing image: {img_error}")
        
        content_parts.append("\nPlease provide your response:")
        
        response = model.generate_content(content_parts)
        
        return jsonify({
            'feedback': response.text,
            'model': 'gemini-2.0-flash-exp',
            'files_processed': len([f for f in files if f.get('type', '').startswith('image/')])
        })
        
    except Exception as e:
        print(f"Gemini API error: {str(e)}")
        return jsonify({
            'error': f'AI service error: {str(e)}',
            'feedback': 'Unable to get AI feedback at this time. Please try again.'
        }), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'gemini_configured': bool(GEMINI_API_KEY),
        'database': 'postgresql' if 'postgres' in app.config['SQLALCHEMY_DATABASE_URI'] else 'sqlite'
    })

if __name__ == '__main__':
    print("🚀 Starting Product Siksha Backend...")
    print(f"   Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
    # Auto-create tables for local development if they don't exist
    with app.app_context():
        try:
            db.create_all()
            print("   ✅ Database tables verified")
        except Exception as e:
            print(f"   ⚠️  Database warning: {e}")

    app.run(debug=False, host='0.0.0.0', port=5001)
