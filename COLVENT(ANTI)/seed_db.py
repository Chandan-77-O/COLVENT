import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Missing Supabase credentials.")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def seed_data():
    try:
        print("Clearing existing data to avoid duplicates...")
        # Since there's no easy "truncate" from supabase client, we can delete all rows by matching a condition that's always true.
        # But supabase requires a filter. We can use .neq('id', -1)
        supabase.table('participation').delete().neq('participation_id', -1).execute()
        supabase.table('competitions').delete().neq('competition_id', -1).execute()
        supabase.table('events').delete().neq('event_id', -1).execute()
        
        # Must delete studentauth before participants due to foreign key constraints if cascade isn't fully working, but we added cascade.
        supabase.table('studentauth').delete().neq('password_hash', 'dummy').execute()
        supabase.table('participants').delete().neq('participant_id', -1).execute()
        
        # 1. Add demo events
        print("Adding demo events...")
        events_data = [
            {
                'name': 'Tech Symposium 2026',
                'description': 'Annual technical symposium featuring coding challenges and hackathons.',
                'start_date': '2026-06-15',
                'end_date': '2026-06-17',
                'status': 'Upcoming',
                'category': 'Technical'
            },
            {
                'name': 'Cultural Fest: Euphoria',
                'description': 'A three-day cultural extravaganza with music, dance, and arts.',
                'start_date': '2026-05-10',
                'end_date': '2026-05-12',
                'status': 'Ongoing',
                'category': 'Cultural'
            },
            {
                'name': 'Sports Meet 2026',
                'description': 'Inter-departmental sports tournament.',
                'start_date': '2026-04-01',
                'end_date': '2026-04-05',
                'status': 'Past',
                'category': 'Sports'
            }
        ]
        
        events_res = supabase.table('events').insert(events_data).execute()
        inserted_events = events_res.data
        
        # Mapping event names to IDs
        event_ids = {e['name']: e['event_id'] for e in inserted_events}
        
        # 2. Add demo competitions
        print("Adding demo competitions...")
        competitions_data = [
            {'event_id': event_ids['Tech Symposium 2026'], 'name': 'CodeRush - Algorithmic Programming', 'max_participants': 100},
            {'event_id': event_ids['Tech Symposium 2026'], 'name': 'Webathon 24Hr Hackathon', 'max_participants': 50},
            {'event_id': event_ids['Cultural Fest: Euphoria'], 'name': 'Battle of Bands', 'max_participants': 20},
            {'event_id': event_ids['Cultural Fest: Euphoria'], 'name': 'Group Dance Competition', 'max_participants': 30},
            {'event_id': event_ids['Sports Meet 2026'], 'name': '100m Sprint', 'max_participants': 50},
            {'event_id': event_ids['Sports Meet 2026'], 'name': 'Inter-Dept Football', 'max_participants': 16}
        ]
        
        comps_res = supabase.table('competitions').insert(competitions_data).execute()
        inserted_comps = comps_res.data
        
        comp_ids = {c['name']: c['competition_id'] for c in inserted_comps}
        
        # 3. Add demo participants with 24UG00xxx format
        print("Adding demo participants...")
        participants_data = [
            {'name': 'Alice Smith', 'usn': '24UG00101', 'department': 'CSE', 'year': 2, 'participant_type': 'Student'},
            {'name': 'Bob Johnson', 'usn': '24UG00102', 'department': 'ISE', 'year': 3, 'participant_type': 'Student'},
            {'name': 'Charlie Brown', 'usn': '24UG00103', 'department': 'ECE', 'year': 4, 'participant_type': 'Student'},
            {'name': 'Diana Prince', 'usn': '24UG00104', 'department': 'ME', 'year': 1, 'participant_type': 'Student'},
            {'name': 'Ethan Hunt', 'usn': '24UG00105', 'department': 'CSE', 'year': 2, 'participant_type': 'Student'},
            {'name': 'Fiona Gallagher', 'usn': '24UG00106', 'department': 'MBA', 'year': 1, 'participant_type': 'Student'},
            {'name': 'George Costanza', 'usn': '24UG00107', 'department': 'BBA', 'year': 2, 'participant_type': 'Student'},
            {'name': 'Harvey Specter', 'usn': '24UG00108', 'department': 'BALLB', 'year': 3, 'participant_type': 'Student'},
            {'name': 'Irene Adler', 'usn': '24UG00109', 'department': 'BCOM', 'year': 2, 'participant_type': 'Student'},
            {'name': 'Jack Ryan', 'usn': '24UG00110', 'department': 'MCOM', 'year': 1, 'participant_type': 'Student'},
        ]
        
        parts_res = supabase.table('participants').insert(participants_data).execute()
        inserted_parts = parts_res.data
        
        part_ids = {p['usn']: p['participant_id'] for p in inserted_parts}
        
        # 4. Add demo participations
        print("Adding demo participations...")
        participations_data = [
            {'participant_id': part_ids['24UG00101'], 'competition_id': comp_ids['CodeRush - Algorithmic Programming'], 'rank': 1},
            {'participant_id': part_ids['24UG00101'], 'competition_id': comp_ids['Webathon 24Hr Hackathon'], 'rank': None},
            {'participant_id': part_ids['24UG00102'], 'competition_id': comp_ids['Webathon 24Hr Hackathon'], 'rank': 2},
            {'participant_id': part_ids['24UG00103'], 'competition_id': comp_ids['Battle of Bands'], 'rank': 1},
            {'participant_id': part_ids['24UG00104'], 'competition_id': comp_ids['Group Dance Competition'], 'rank': 3},
            {'participant_id': part_ids['24UG00105'], 'competition_id': comp_ids['Inter-Dept Football'], 'rank': 1},
            {'participant_id': part_ids['24UG00101'], 'competition_id': comp_ids['Group Dance Competition'], 'rank': None},
            {'participant_id': part_ids['24UG00103'], 'competition_id': comp_ids['CodeRush - Algorithmic Programming'], 'rank': 2},
            {'participant_id': part_ids['24UG00106'], 'competition_id': comp_ids['Webathon 24Hr Hackathon'], 'rank': 1},
            {'participant_id': part_ids['24UG00107'], 'competition_id': comp_ids['Battle of Bands'], 'rank': 2},
            {'participant_id': part_ids['24UG00108'], 'competition_id': comp_ids['CodeRush - Algorithmic Programming'], 'rank': 3},
            {'participant_id': part_ids['24UG00109'], 'competition_id': comp_ids['Group Dance Competition'], 'rank': 1},
            {'participant_id': part_ids['24UG00110'], 'competition_id': comp_ids['Inter-Dept Football'], 'rank': 2},
        ]
        
        supabase.table('participation').insert(participations_data).execute()
        
        print("Database seeded successfully with new USN format!")
        
    except Exception as e:
        print(f"Error during seeding: {e}")

if __name__ == '__main__':
    seed_data()
