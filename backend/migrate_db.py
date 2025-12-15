import sqlite3

DB_NAME = 'product_siksha.db'

def migrate():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    print("Creating user_progress table...")
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_progress (
            user_id INTEGER,
            question_id INTEGER,
            is_completed BOOLEAN DEFAULT 0,
            completed_at TIMESTAMP,
            PRIMARY KEY (user_id, question_id),
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (question_id) REFERENCES questions (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == '__main__':
    migrate()
