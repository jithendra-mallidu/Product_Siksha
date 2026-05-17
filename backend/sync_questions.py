#!/usr/bin/env python3
"""
Sync questions from Lewis Lin's PM Question Bank (Google Sheet) into the database.
Fetches the sheet via its public CSV endpoint, compares with existing questions,
and inserts only new ones.

Supports both SQLite (local) and PostgreSQL (Cloud Run) via DATABASE_URL env var.
"""

import csv
import io
import os
import urllib.request
from datetime import datetime

from sqlalchemy import create_engine, text

# The public Google Sheet CSV export URL
SHEET_ID = "1rz10oEeLx-eGnilahKczYPhGfCUzIEKL-xRnjoQ-SX4"
GID = "1024620532"
SHEET_CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&gid={GID}"

# Import categorization and normalization logic
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from cleanup_pm_questions import categorize_question, normalize_company


def get_database_url():
    """Get database URL - uses DATABASE_URL env var or falls back to local SQLite."""
    database_url = os.getenv('DATABASE_URL', '')
    if database_url:
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        return database_url
    db_path = os.path.join(os.path.dirname(__file__), 'product_siksha.db')
    return f"sqlite:///{db_path}"


def fetch_sheet_questions():
    """Fetch all questions from the Google Sheet CSV export."""
    req = urllib.request.Request(SHEET_CSV_URL, headers={
        'User-Agent': 'Mozilla/5.0 (PM Interview Coach Sync)'
    })
    with urllib.request.urlopen(req, timeout=30) as response:
        content = response.read().decode('utf-8')

    reader = csv.reader(io.StringIO(content))
    next(reader)  # skip header

    questions = []
    for row in reader:
        if len(row) < 3 or not row[2].strip():
            continue

        questions.append({
            'timestamp': row[0].strip() if len(row) > 0 else '',
            'company': row[1].strip() if len(row) > 1 else '',
            'question': row[2].strip() if len(row) > 2 else '',
            'question_type': row[3].strip() if len(row) > 3 else '',
            'interview_type': row[4].strip() if len(row) > 4 else '',
            'comments': row[5].strip() if len(row) > 5 else '',
            'job_title': row[6].strip() if len(row) > 6 else '',
        })

    return questions


def get_existing_questions(conn):
    """Get set of (question_text, company) tuples already in the DB for deduplication."""
    result = conn.execute(text('SELECT question, company FROM questions'))
    return {(row[0], row[1]) for row in result}


def sync():
    """Main sync: fetch sheet, diff against DB, insert new questions."""
    database_url = get_database_url()
    db_type = "PostgreSQL" if "postgresql" in database_url else "SQLite"
    print(f"[{datetime.now().isoformat()}] Starting question sync ({db_type})...")

    print("  Fetching questions from Google Sheet...")
    sheet_questions = fetch_sheet_questions()
    print(f"  Found {len(sheet_questions)} questions in sheet")

    engine = create_engine(database_url)
    with engine.connect() as conn:
        existing = get_existing_questions(conn)
        print(f"  Found {len(existing)} existing questions in DB")

        new_questions = []
        for q in sheet_questions:
            key = (q['question'], q['company'])
            if key not in existing:
                new_questions.append(q)

        if not new_questions:
            print("  No new questions found. Database is up to date.")
            return 0

        print(f"  Inserting {len(new_questions)} new questions...")
        for q in new_questions:
            company_normalized = normalize_company(q['company'])
            question_category = categorize_question(q['question_type'])

            conn.execute(text('''
                INSERT INTO questions (
                    timestamp, company, question, question_type,
                    interview_type, comments, job_title,
                    company_normalized, question_category
                ) VALUES (:timestamp, :company, :question, :question_type,
                    :interview_type, :comments, :job_title,
                    :company_normalized, :question_category)
            '''), {
                'timestamp': q['timestamp'],
                'company': q['company'],
                'question': q['question'],
                'question_type': q['question_type'],
                'interview_type': q['interview_type'],
                'comments': q['comments'],
                'job_title': q['job_title'],
                'company_normalized': company_normalized,
                'question_category': question_category,
            })

        conn.commit()

    print(f"  Successfully added {len(new_questions)} new questions!")
    return len(new_questions)


if __name__ == '__main__':
    sync()
