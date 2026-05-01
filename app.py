import os
import io
import base64
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from supabase import create_client, Client
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_session'

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    print("WARNING: Supabase URL or Key is missing.")

# Decorator to ensure admin is logged in
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Admin access required.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Decorator to ensure student is logged in
def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'student':
            flash('Student access required.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif session.get('role') == 'student':
        return redirect(url_for('student_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form.get('role')
        usn = request.form.get('usn')
        password = request.form.get('password')
        
        if role == 'admin':
            if usn == 'admin' and password == 'colvents@admin123':
                session['role'] = 'admin'
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Invalid Admin Credentials.', 'error')
                return redirect(url_for('login'))
                
        elif role == 'student':
            if not usn or not password:
                flash('USN and Password are required.', 'error')
                return redirect(url_for('login'))
                
            try:
                # Check StudentAuth table
                auth_res = supabase.table('studentauth').select('*').eq('usn', usn).execute().data
                if auth_res:
                    stored_hash = auth_res[0]['password_hash']
                    if check_password_hash(stored_hash, password):
                        session['role'] = 'student'
                        session['usn'] = usn
                        return redirect(url_for('student_dashboard'))
                    else:
                        flash('Invalid USN or Password.', 'error')
                else:
                    flash('Account not found. Please sign up.', 'error')
            except Exception as e:
                print(f"Login error: {e}")
                flash('An error occurred during login.', 'error')
            return redirect(url_for('login'))
            
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        usn = request.form.get('usn')
        name = request.form.get('name')
        password = request.form.get('password')
        department = request.form.get('department')
        year = request.form.get('year')
        
        if not all([usn, name, password, department, year]):
            flash('All fields are required.', 'error')
            return redirect(url_for('signup'))
            
        try:
            # Check if participant already exists
            participant_exists = supabase.table('participants').select('usn').eq('usn', usn).execute().data
            if participant_exists:
                flash('An account with this USN already exists. Please log in.', 'error')
                return redirect(url_for('login'))
            
            # Hash password
            hashed_pw = generate_password_hash(password)
            
            # Create participant record
            supabase.table('participants').insert({
                'usn': usn,
                'name': name,
                'department': department,
                'year': year,
                'participant_type': 'Student'
            }).execute()
            
            # Create student auth record
            supabase.table('studentauth').insert({
                'usn': usn,
                'password_hash': hashed_pw
            }).execute()
            
            flash('Account created successfully! You can now log in.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            print(f"Signup error: {e}")
            flash('An error occurred during signup. It is possible the USN is already registered.', 'error')
            return redirect(url_for('signup'))
            
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- ADMIN ROUTES ---

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    try:
        events_res = supabase.table('events').select('*').execute()
        events = events_res.data
        
        participation_res = supabase.table('participation').select('participation_id', count='exact').execute()
        total_participations = participation_res.count if participation_res.count else 0
        
        participants_res = supabase.table('participants').select('participant_id', count='exact').execute()
        total_registrations = participants_res.count if participants_res.count else 0
        
        past_events = len([e for e in events if e['status'] == 'Past'])
        ongoing_events = len([e for e in events if e['status'] == 'Ongoing'])
        upcoming_events = len([e for e in events if e['status'] == 'Upcoming'])
        
        # Fetch all participations for the registrations table
        all_participations = supabase.table('participation').select('*, participants(name, usn, department, year), competitions(event_id, name, events(name))').order('registration_date', desc=True).execute().data
        
        return render_template('admin_dashboard.html', 
                               total_events=len(events),
                               total_participations=total_participations,
                               total_registrations=total_registrations,
                               past_events=past_events,
                               ongoing_events=ongoing_events,
                               upcoming_events=upcoming_events,
                               events=events,
                               all_participations=all_participations)
    except Exception as e:
        print(f"Error: {e}")
        flash('Failed to fetch dashboard data.', 'error')
        return render_template('admin_dashboard.html', total_events=0, total_participations=0, total_registrations=0, events=[], all_participations=[])

@app.route('/admin/events', methods=['GET', 'POST'])
@admin_required
def admin_events():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'create_event':
            name = request.form.get('name')
            description = request.form.get('description')
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            status = request.form.get('status')
            category = request.form.get('category')
            
            try:
                supabase.table('events').insert({
                    'name': name,
                    'description': description,
                    'start_date': start_date,
                    'end_date': end_date,
                    'status': status,
                    'category': category
                }).execute()
                flash('Event created successfully!', 'success')
            except Exception as e:
                flash(f'Error creating event: {e}', 'error')
                
        elif action == 'create_competition':
            event_id = request.form.get('event_id')
            name = request.form.get('name')
            max_participants = request.form.get('max_participants')
            
            data = {'event_id': event_id, 'name': name}
            if max_participants:
                data['max_participants'] = max_participants
                
            try:
                supabase.table('competitions').insert(data).execute()
                flash('Competition added successfully!', 'success')
            except Exception as e:
                flash(f'Error adding competition: {e}', 'error')
                
        return redirect(url_for('admin_events'))

    try:
        events = supabase.table('events').select('*').execute().data
        competitions = supabase.table('competitions').select('*, events(name)').execute().data
        return render_template('admin_events.html', events=events, competitions=competitions)
    except Exception as e:
        flash(f'Error loading events: {e}', 'error')
        return render_template('admin_events.html', events=[], competitions=[])

@app.route('/admin/analytics')
@admin_required
def admin_analytics():
    try:
        # Fetch data for analytics
        participants_data = supabase.table('participants').select('*').execute().data
        participation_data = supabase.table('participation').select('*, competitions(event_id, name), participants(department, usn, name)').execute().data
        events_data = supabase.table('events').select('*').execute().data

        df_participants = pd.DataFrame(participants_data)
        df_participation = pd.DataFrame(participation_data)
        df_events = pd.DataFrame(events_data)

        graphs = {}

        if not df_participation.empty and not df_participants.empty:
            # Graph 1: Participation count by department
            dept_counts = df_participation['participants'].apply(lambda x: x['department'] if x else 'Unknown').value_counts()
            plt.figure(figsize=(8, 5))
            dept_counts.plot(kind='bar', color='#4F46E5')
            plt.title('Participation Count by Department')
            plt.xlabel('Department')
            plt.ylabel('Count')
            plt.tight_layout()
            img = io.BytesIO()
            plt.savefig(img, format='png')
            img.seek(0)
            graphs['dept_participation'] = base64.b64encode(img.getvalue()).decode('utf-8')
            plt.close()

            # Graph 2: Category-based popularity
            if not df_events.empty:
                event_categories = df_events[['event_id', 'category']]
                part_with_event = df_participation.copy()
                part_with_event['event_id'] = part_with_event['competitions'].apply(lambda x: x['event_id'] if x else None)
                merged = part_with_event.merge(event_categories, on='event_id', how='left')
                
                cat_counts = merged['category'].value_counts()
                plt.figure(figsize=(8, 5))
                cat_counts.plot(kind='pie', autopct='%1.1f%%', startangle=90, colors=['#3B82F6', '#10B981', '#F59E0B', '#EF4444'])
                plt.title('Category-based Popularity')
                plt.ylabel('')
                plt.tight_layout()
                img = io.BytesIO()
                plt.savefig(img, format='png')
                img.seek(0)
                graphs['category_popularity'] = base64.b64encode(img.getvalue()).decode('utf-8')
                plt.close()

            # Graph 3: Radar Chart for Department Comparison
            if not dept_counts.empty:
                import numpy as np
                categories = list(dept_counts.keys())
                values = list(dept_counts.values)
                values += values[:1] # close the circular graph
                angles = [n / float(len(categories)) * 2 * np.pi for n in range(len(categories))]
                angles += angles[:1]
                
                plt.figure(figsize=(6, 6))
                ax = plt.subplot(111, polar=True)
                plt.xticks(angles[:-1], categories)
                ax.plot(angles, values, color='#6366F1', linewidth=2, linestyle='solid')
                ax.fill(angles, values, color='#6366F1', alpha=0.4)
                plt.title('Department Participation Radar', y=1.1)
                
                img = io.BytesIO()
                plt.savefig(img, format='png')
                img.seek(0)
                graphs['dept_radar'] = base64.b64encode(img.getvalue()).decode('utf-8')
                plt.close()

            # Top Performers
            part_with_participant = df_participation.copy()
            if not part_with_participant.empty:
                part_with_participant['usn'] = part_with_participant['participants'].apply(lambda x: x['usn'] if x else 'Unknown')
                part_with_participant['department'] = part_with_participant['participants'].apply(lambda x: x['department'] if x else 'Unknown')
                part_with_participant['name'] = part_with_participant['participants'].apply(lambda x: x['name'] if x else 'Unknown')
                
                top_performers_counts = part_with_participant['usn'].value_counts().head(10)
                
                top_performers = []
                for usn, count in top_performers_counts.items():
                    row = part_with_participant[part_with_participant['usn'] == usn].iloc[0]
                    top_performers.append({
                        'usn': usn, 
                        'name': row['name'],
                        'department': row['department'], 
                        'count': count
                    })

        return render_template('admin_analytics.html', graphs=graphs, top_performers=top_performers if 'top_performers' in locals() else [])
    except Exception as e:
        print(f"Error generating analytics: {e}")
        flash('Failed to generate analytics.', 'error')
        return render_template('admin_analytics.html', graphs={})

@app.route('/admin/event/<int:event_id>/analytics')
@admin_required
def event_analytics(event_id):
    try:
        # Fetch event info
        event_data = supabase.table('events').select('*').eq('event_id', event_id).execute().data
        if not event_data:
            flash('Event not found.', 'error')
            return redirect(url_for('admin_dashboard'))
        event = event_data[0]
        
        # Fetch competitions for this event
        competitions = supabase.table('competitions').select('*').eq('event_id', event_id).execute().data
        comp_ids = [c['competition_id'] for c in competitions]
        
        graphs = {}
        rankers = []
        
        if comp_ids:
            part_res = supabase.table('participation').select('*, competitions(name, event_id), participants(name, usn, department, year)').in_('competition_id', comp_ids).execute().data
            df_part = pd.DataFrame(part_res)
            
            if not df_part.empty:
                df_part['comp_name'] = df_part['competitions'].apply(lambda x: x['name'] if x else 'Unknown')
                df_part['dept'] = df_part['participants'].apply(lambda x: x['department'] if x else 'Unknown')
                df_part['year'] = df_part['participants'].apply(lambda x: x['year'] if x else 0)
                df_part['reg_date'] = pd.to_datetime(df_part['registration_date']).dt.date
                
                # 1. Department-wise Bar Graph
                dept_counts = df_part['dept'].value_counts()
                plt.figure(figsize=(8, 5))
                dept_counts.plot(kind='bar', color='#10B981')
                plt.title(f'Department Participation for {event["name"]}')
                plt.xlabel('Department')
                plt.ylabel('Count')
                plt.tight_layout()
                img = io.BytesIO()
                plt.savefig(img, format='png')
                img.seek(0)
                graphs['dept_bar'] = base64.b64encode(img.getvalue()).decode('utf-8')
                plt.close()
                
                # 2. Registration Trend Line Chart
                date_counts = df_part['reg_date'].value_counts().sort_index()
                plt.figure(figsize=(8, 5))
                date_counts.plot(kind='line', marker='o', color='#3B82F6', linewidth=2)
                plt.title('Daily Registration Trend')
                plt.xlabel('Date')
                plt.ylabel('Registrations')
                plt.tight_layout()
                img = io.BytesIO()
                plt.savefig(img, format='png')
                img.seek(0)
                graphs['reg_trend'] = base64.b64encode(img.getvalue()).decode('utf-8')
                plt.close()
                
                # 3. Year-wise Distribution Pie Chart
                year_counts = df_part['year'].value_counts()
                plt.figure(figsize=(6, 6))
                year_counts.plot(kind='pie', autopct='%1.1f%%', startangle=90, colors=['#F59E0B', '#EF4444', '#8B5CF6', '#EC4899'])
                plt.title('Year-wise Distribution')
                plt.ylabel('')
                plt.tight_layout()
                img = io.BytesIO()
                plt.savefig(img, format='png')
                img.seek(0)
                graphs['year_pie'] = base64.b64encode(img.getvalue()).decode('utf-8')
                plt.close()
                
                # Rankers logic
                for comp in competitions:
                    comp_name = comp['name']
                    comp_parts = [p for p in part_res if p['competition_id'] == comp['competition_id'] and p.get('rank') is not None]
                    comp_parts.sort(key=lambda x: x['rank'])
                    if comp_parts:
                        rankers.append({
                            'competition': comp_name,
                            'winners': comp_parts
                        })
                
        return render_template('admin_event_analytics.html', event=event, graphs=graphs, rankers=rankers)
    except Exception as e:
        print(f"Error generating event analytics: {e}")
        flash('Failed to generate event analytics.', 'error')
        return redirect(url_for('admin_dashboard'))

# --- STUDENT ROUTES ---

@app.route('/student/dashboard')
@student_required
def student_dashboard():
    usn = session.get('usn')
    try:
        # Fetch competitions and their related events
        competitions_data = supabase.table('competitions').select('*, events(*)').execute().data
        competitions = [c for c in competitions_data if c.get('events') and c['events'].get('status') in ['Ongoing', 'Upcoming']]
            
        return render_template('student_dashboard.html', competitions=competitions, usn=usn)
    except Exception as e:
        print(f"Error: {e}")
        return render_template('student_dashboard.html', competitions=[], usn=usn)

@app.route('/student/my-events')
@student_required
def student_my_events():
    usn = session.get('usn')
    try:
        participant_res = supabase.table('participants').select('participant_id').eq('usn', usn).execute().data
        my_participations = []
        if participant_res:
            pid = participant_res[0]['participant_id']
            my_participations = supabase.table('participation').select('*, competitions(name, events(name, status, category))').eq('participant_id', pid).execute().data
            
        return render_template('student_my_events.html', my_participations=my_participations)
    except Exception as e:
        print(f"Error fetching my events: {e}")
        return render_template('student_my_events.html', my_participations=[])

@app.route('/student/check-usn', methods=['GET', 'POST'])
@student_required
def student_check_usn():
    search_result = None
    searched_usn = None
    if request.method == 'POST':
        searched_usn = request.form.get('search_usn')
        if searched_usn:
            try:
                participant_res = supabase.table('participants').select('*').eq('usn', searched_usn).execute().data
                if participant_res:
                    pid = participant_res[0]['participant_id']
                    participations = supabase.table('participation').select('*, competitions(name, events(name, status))').eq('participant_id', pid).execute().data
                    search_result = {
                        'student': participant_res[0],
                        'participations': participations
                    }
                else:
                    flash(f'No student found with USN {searched_usn}', 'error')
            except Exception as e:
                flash(f'Error searching USN: {e}', 'error')
    
    return render_template('student_check_usn.html', search_result=search_result, searched_usn=searched_usn)

@app.route('/student/register_competition/<int:comp_id>', methods=['GET', 'POST'])
@student_required
def register_competition(comp_id):
    usn = session.get('usn')
    if request.method == 'POST':
        name = request.form.get('name')
        department = request.form.get('department')
        year = request.form.get('year')
        
        try:
            # Ensure participant exists
            participant_res = supabase.table('participants').select('participant_id').eq('usn', usn).execute().data
            if not participant_res:
                insert_res = supabase.table('participants').insert({
                    'name': name,
                    'usn': usn,
                    'department': department,
                    'year': year,
                    'participant_type': 'Student'
                }).execute()
                participant_id = insert_res.data[0]['participant_id']
            else:
                participant_id = participant_res[0]['participant_id']
                
            # Register for competition
            supabase.table('participation').insert({
                'participant_id': participant_id,
                'competition_id': comp_id
            }).execute()
            
            flash('Successfully registered for the competition!', 'success')
            return redirect(url_for('student_dashboard'))
        except Exception as e:
            flash(f'Registration failed or you are already registered. ({e})', 'error')
            
    try:
        competition = supabase.table('competitions').select('*, events(*)').eq('competition_id', comp_id).execute().data[0]
        return render_template('register.html', competition=competition)
    except Exception as e:
        flash('Error loading competition details.', 'error')
        return redirect(url_for('student_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
