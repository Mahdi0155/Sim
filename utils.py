# utils.py

import os
import sqlite3
from hashlib import sha256
from config import PERSISTENT_DB_PATH

if not os.path.exists('persistent'):
    os.makedirs('persistent')

conn = sqlite3.connect(PERSISTENT_DB_PATH, check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS files (
    code TEXT PRIMARY KEY,
    file_id TEXT
)
''')
conn.commit()

def generate_code(file_id):
    return sha256(file_id.encode()).hexdigest()[:10]

def save_file(file_id):
    code = generate_code(file_id)
    cursor.execute('INSERT OR IGNORE INTO files (code, file_id) VALUES (?, ?)', (code, file_id))
    conn.commit()
    return code

def get_file(code):
    cursor.execute('SELECT file_id FROM files WHERE code = ?', (code,))
    result = cursor.fetchone()
    return result[0] if result else None
