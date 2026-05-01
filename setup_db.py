import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_CONNECTION_STRING = os.getenv("DB_CONNECTION_STRING")

# We will try both connection strings if the direct one fails.
# Supabase transaction pooler runs on port 6543
alternate_conn_str = "postgresql://postgres.oflsrrmbthtkxpnxpdgx:6zjx2Rud20B8yiYK@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"

sql_commands = """
CREATE TABLE IF NOT EXISTS Events (
    event_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    start_date DATE,
    end_date DATE,
    status VARCHAR(50) CHECK (status IN ('Past', 'Ongoing', 'Upcoming')),
    category VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS Competitions (
    competition_id SERIAL PRIMARY KEY,
    event_id INT REFERENCES Events(event_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    max_participants INT
);

CREATE TABLE IF NOT EXISTS Participants (
    participant_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    usn VARCHAR(50) UNIQUE NOT NULL,
    department VARCHAR(100),
    year INT,
    participant_type VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS StudentAuth (
    usn VARCHAR(50) PRIMARY KEY REFERENCES Participants(usn) ON DELETE CASCADE,
    password_hash VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS Participation (
    participation_id SERIAL PRIMARY KEY,
    participant_id INT REFERENCES Participants(participant_id) ON DELETE CASCADE,
    competition_id INT REFERENCES Competitions(competition_id) ON DELETE CASCADE,
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    rank INT,
    UNIQUE(participant_id, competition_id)
);
"""

def setup_db():
    conn = None
    try:
        print("Attempting to connect with standard direct string...")
        conn = psycopg2.connect(DB_CONNECTION_STRING)
    except Exception as e:
        print(f"Failed direct connection: {e}")
        try:
            print("Attempting to connect with alternate pooler string...")
            conn = psycopg2.connect(alternate_conn_str)
        except Exception as e2:
            print(f"Failed pooler connection: {e2}")
            return
    
    try:
        cur = conn.cursor()
        cur.execute(sql_commands)
        conn.commit()
        cur.close()
        print("Tables created successfully!")
    except Exception as e:
        print(f"Error executing commands: {e}")
    finally:
        if conn is not None:
            conn.close()

if __name__ == "__main__":
    setup_db()
