import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from internal.mysql.init import get_connection, init_db

def reset():
    print("Initializing pool...")
    init_db()
    print("Clearing tables...")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SET FOREIGN_KEY_CHECKS = 0;")
            cur.execute("TRUNCATE TABLE memory_level1;")
            cur.execute("TRUNCATE TABLE memory_level2;")
            cur.execute("TRUNCATE TABLE messages;")
            cur.execute("TRUNCATE TABLE conversations;")
            cur.execute("SET FOREIGN_KEY_CHECKS = 1;")
        conn.commit()
    finally:
        conn.close()
        
    print("Database data cleared.")

if __name__ == "__main__":
    reset()
