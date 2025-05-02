import sqlite3

def init_db():
    conn = sqlite3.connect("data.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id TEXT PRIMARY KEY,
            file_id TEXT NOT NULL,
            caption TEXT,
            cover TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_video(key, file_id, caption, cover):
    conn = sqlite3.connect("data.db")
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO videos (id, file_id, caption, cover)
        VALUES (?, ?, ?, ?)
    """, (key, file_id, caption, cover))
    conn.commit()
    conn.close()

def get_video(key):
    conn = sqlite3.connect("data.db")
    cur = conn.cursor()
    cur.execute("SELECT file_id, caption, cover FROM videos WHERE id = ?", (key,))
    row = cur.fetchone()
    conn.close()
    if row:
        return {"video": row[0], "caption": row[1], "cover": row[2]}
    return None
