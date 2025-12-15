#!/usr/bin/env python3
"""
Initialize the SQLite database with user and load questions from CSV.
"""

import sqlite3
import csv
import os
from datetime import datetime
import hashlib

DB_PATH = os.path.join(os.path.dirname(__file__), 'product_siksha.db')
CSV_PATH = os.path.join(os.path.dirname(__file__), '..', 'PM_Interview_Questions_Cleaned.csv')

def hash_password(password: str) -> str:
    """Simple password hashing (use bcrypt in production)."""
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    """Initialize the database with tables and seed data."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create questions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            company TEXT,
            question TEXT,
            question_type TEXT,
            interview_type TEXT,
            comments TEXT,
            job_title TEXT,
            company_normalized TEXT,
            question_category TEXT
        )
    ''')
    
    # Insert default user
    try:
        cursor.execute('''
            INSERT INTO users (email, password_hash)
            VALUES (?, ?)
        ''', ('jmallidu@gmail.com', hash_password('password')))
        print("✅ Created user: jmallidu@gmail.com")
    except sqlite3.IntegrityError:
        print("ℹ️  User already exists")
    
    # Load questions from CSV
    cursor.execute('SELECT COUNT(*) FROM questions')
    if cursor.fetchone()[0] == 0:
        print("📥 Loading questions from CSV...")
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            for row in rows:
                cursor.execute('''
                    INSERT INTO questions (
                        timestamp, company, question, question_type,
                        interview_type, comments, job_title,
                        company_normalized, question_category
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row.get('Timestamp', ''),
                    row.get('Company', ''),
                    row.get('What was the interview question?', ''),
                    row.get('Question Type (e.g. Product, Strategy)', ''),
                    row.get('Interview Type', ''),
                    row.get('Comments (e.g. your approach)', ''),
                    row.get('What was the job title for this question?', ''),
                    row.get('Company_Normalized', ''),
                    row.get('Question_Category', '')
                ))
            
            print(f"✅ Loaded {len(rows)} questions")
    else:
        print("ℹ️  Questions already loaded")
    
    conn.commit()
    conn.close()
    print(f"✅ Database initialized: {DB_PATH}")

if __name__ == '__main__':
    init_db()
