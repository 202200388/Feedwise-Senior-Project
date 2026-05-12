import os
import csv
import io
import re
import json
import openai
import re
import urllib.parse
import pandas as pd
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response, make_response,send_file,jsonify
from flask_sqlalchemy import SQLAlchemy
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display
from werkzeug.utils import secure_filename
from pdf_reader import extract_text_from_pdf
from sentiment import analyze_sentiment     
from summarizer import summarize_text       
from werkzeug.security import generate_password_hash
from preprocessing import clean_text
from sentiment import analyze_sentiment
from summarizer import summarize_text
from issue_detection import extract_top_keywords
from main import run_analysis
from sqlalchemy import text
from sqlalchemy.orm import joinedload
from pdf_reader import extract_text_from_pdf
from sentiment import analyze_sentiment
from summarizer import summarize_text
from preprocessing import clean_text
from issue_detection import extract_top_keywords

app = Flask(__name__)

app.secret_key = 'super_secret_key_for_session'

#iniate connection to DB on (PostgreSQL)
raw_pwd = 'Z@HsB120Ra&' 
encoded_pwd = urllib.parse.quote_plus(raw_pwd)
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://postgres:{encoded_pwd}@localhost:5432/feedwise_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_size": 10,         
    "max_overflow": 20,      
    "pool_recycle": 3600,     
}

db = SQLAlchemy(app)

#Models(tables on DB)
course_instructor = db.Table('course_instructor',
    db.Column('instructor_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('course_id', db.Integer, db.ForeignKey('course.id'), primary_key=True),
    db.Column('section_number', db.String(10), primary_key=True)
)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default='Instructor')
    theme = db.Column(db.String(10), default='light')
    
    #relaionship to put all section that instructor tech
    sections_taught = db.relationship('Section', backref='instructor_user', lazy=True)

class Instructor(db.Model):
    """use it for only students choose from the list"""
    __tablename__ = 'instructor'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    courses = db.relationship('Course', backref='instructor_ref', lazy=True)
    feedbacks = db.relationship('Feedback', backref='inst_ref', lazy=True)

class Course(db.Model):
    __tablename__ = 'course'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    #link to garanty course appear to insturctors that teaching this course
    instructor_id = db.Column(db.Integer, db.ForeignKey('users.id')) 
    # relationship to student instructor list
    instructor_list_id = db.Column(db.Integer, db.ForeignKey('instructor.id'))
    sections = db.relationship('Section', backref='course_ref', lazy=True)
    analysis = db.relationship('Analysis', backref='course_ref', uselist=False, cascade="all, delete-orphan")

class Section(db.Model):
    __tablename__ = 'section'
    id = db.Column(db.Integer, primary_key=True)
    section_number = db.Column(db.String(10), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    instructor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

class Feedback(db.Model):
    __tablename__ = 'feedback'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    instructor_id = db.Column(db.Integer, db.ForeignKey('instructor.id'), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('section.id'), nullable=False)

class Analysis(db.Model):
    __tablename__ = 'analysis_results'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    summary_text = db.Column(db.Text)
    positive_points = db.Column(db.Text)
    negative_points = db.Column(db.Text)
    pos_score = db.Column(db.Integer, default=0) 
    analysis_date = db.Column(db.DateTime, default=datetime.utcnow)


#Routes:

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('This email address is already registered, please log in.', 'danger')
            return render_template('register.html', 
                                 first_name=first_name, 
                                 last_name=last_name, 
                                 email=email, 
                                 role=role)

        new_user = User(
            first_name=first_name, 
            last_name=last_name, 
            email=email, 
            password=password, 
            role=role
        )
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('register')) 
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration, please try again.', 'danger')
            return render_template('register.html')
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email').strip()
        password = request.form.get('password').strip()
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.password == password:
            normalized_role = user.role.capitalize() 
            session['user_id'] = user.id
            session['user_role'] = normalized_role  
            session['role'] = normalized_role       
            session['user_name'] = f"{user.first_name} {user.last_name}"
            session['user_email'] = user.email
    
            if 'user_theme' not in session:
                session['user_theme'] = 'light'
        
            if normalized_role == 'Instructor' or normalized_role == 'Admin':
                flash(f"Welcome back, Professor {user.last_name}!", "success")
                return redirect(url_for('dashboard'))
            else:
                flash("Logged in successfully!", "success")
                return redirect(url_for('student_feedback'))
        
        #if there's an error on login
        flash("Invalid email or password. Please try again.", "danger")
        
    return render_template('login.html')

@app.route('/forgot_pass', methods=['GET', 'POST'])
def forgot_pass():
    if request.method == 'POST':
        email = request.form.get('email')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if new_password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for('forgot_pass'))

        user = User.query.filter_by(email=email).first()
        if user:
            from werkzeug.security import generate_password_hash
            user.password = generate_password_hash(new_password) 
            db.session.commit() 
            flash("Password updated successfully! Please login.", "success")
            return redirect(url_for('login'))
        else:
            flash("Email not found!", "danger")
            
    return render_template('forgot_pass.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash("Please login to access the dashboard.", "warning")
        return redirect(url_for('login'))
        
    current_user_id = session.get('user_id')
    user_role = session.get('user_role')

    try:
        #The admin has the privileges to see everything on the page, but the instructor from instructor_id can only see their own course
        if user_role == 'Admin':
            all_analyses_list = db.session.query(Analysis).options(joinedload(Analysis.course_ref)).all()
            my_courses = Course.query.all()
        else:
            my_courses = db.session.query(Course).filter(Course.instructor_id == current_user_id).all()
            course_ids = [c.id for c in my_courses]
            
            #The instructor gets to see only their own courses
            all_analyses_list = db.session.query(Analysis)\
                .options(joinedload(Analysis.course_ref))\
                .filter(Analysis.course_id.in_(course_ids)).all()

        #Statistics calculation
        total_analyzed = len(all_analyses_list)
        
        if total_analyzed > 0:
            #Calculate the average positivity, ensuring the values ​​are not "None"
            valid_scores = [a.pos_score for a in all_analyses_list if a.pos_score is not None]
            avg_positive = sum(valid_scores) / len(valid_scores) if valid_scores else 0
        else:
            avg_positive = 0

        return render_template('dashboard.html', 
                               all_analyses=all_analyses_list, 
                               total=total_analyzed, 
                               avg_pos=int(avg_positive),
                               active_courses=len(my_courses))
                               
    except Exception as e:
        print(f"CRITICAL: Dashboard Error -> {e}")
        flash("An error occurred while loading your data.", "danger")
        return render_template('dashboard.html', all_analyses=[], total=0, avg_pos=0, active_courses=0)

@app.route('/profile')
def profile():
    if 'user_id' not in session: 
        return redirect(url_for('login'))
    
    #Retrieve user data based on the ID stored in the session
    user_data = User.query.get(session['user_id'])
    return render_template('profile.html', user=user_data)


@app.route('/compare', methods=['GET', 'POST'])
def compare():
    if 'user_id' not in session or session.get('user_role') not in ['Instructor', 'Admin']:
        flash("Access denied.", "danger")
        return redirect(url_for('login'))

    current_user_id = session.get('user_id')
    user_role = session.get('user_role')

    #bring the courses taught by the current instructor
    if user_role == 'Admin':
        my_courses = Course.query.all()
    else:
        my_courses = db.session.query(Course).filter(Course.instructor_id == current_user_id).all()

    course_ids = [c.id for c in my_courses]
    all_analyses = db.session.query(Analysis).filter(Analysis.course_id.in_(course_ids)).all()
    course_codes = [a.course_ref.code for a in all_analyses if a.course_ref]
    sentiment_scores = [a.pos_score for a in all_analyses]
    saved_theme = session.get('user_theme', 'light')

    return render_template('compare.html', 
                           courses=my_courses, 
                           course_codes=course_codes, 
                           sentiment_scores=sentiment_scores,
                           saved_theme=saved_theme)


@app.route('/api/get_analysis/<course_code>')
def get_analysis(course_code):
    #search a courses include code
    course = Course.query.filter_by(code=course_code).first()
    if not course:
        return jsonify({'error': 'Course not found'}), 404

    try:
        #bring the most recent analysis record for this course
        analysis = Analysis.query.filter_by(course_id=course.id).order_by(Analysis.analysis_date.desc()).first()
        prof_name = "Not Assigned"
        section_number = "N/A"
        
        #retrieve the section data related to the course
        section_data = Section.query.filter_by(course_id=course.id).first()
        
        if section_data:
            section_number = section_data.section_number
            instructor = User.query.get(section_data.instructor_id)
            if instructor:
                prof_name = f"Dr. {instructor.first_name} {instructor.last_name}"

        if not analysis:
            return jsonify({
                'code': course.code,
                'professor': prof_name,
                'section_id': section_number,
                'summary': "No AI analysis performed yet. Please upload feedback.",
                'summary_text': "No AI analysis performed yet.",
                'date': "N/A",
                'pos_score': 0,
                'positive_points': [],
                'negative_points': []
            })

        return jsonify({
            'code': course.code,
            'professor': prof_name,
            'section_id': section_number,
            'summary': analysis.summary_text,
            'summary_text': analysis.summary_text,
            'date': analysis.analysis_date.strftime('%Y-%m-%d') if analysis.analysis_date else "N/A",
            'pos_score': analysis.pos_score or 0,
            'positive_points': [p.strip() for p in analysis.positive_points.split(',') if p.strip()] if analysis.positive_points else [],
            'negative_points': [n.strip() for n in analysis.negative_points.split(',') if n.strip()] if analysis.negative_points else []
        })

    except Exception as e:
        print(f"CRITICAL API ERROR: {str(e)}")
        return jsonify({'error': 'Server processed your request but encountered an internal error.'}), 500
    

@app.route('/summary')
@app.route('/summary/<int:course_id>')
def summary(course_id=None):
    #ensure user login 
    if 'user_id' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('login'))

    all_courses = Course.query.all()
    
    #if choose specific course
    if course_id:
        course = Course.query.get_or_404(course_id)
    
        analysis = Analysis.query.filter_by(course_id=course_id).first()
        
        if not analysis:
            flash(f"No AI analysis found for {course.name}. Please upload feedback first.", "info")
            return render_template('summary.html', 
                                   course=course, 
                                   analysis=None,
                                   all_courses=all_courses)

        return render_template('summary.html', 
                               course=course, 
                               analysis=analysis, 
                               all_courses=all_courses)
    
    #if dont choose any course
    return render_template('summary.html', 
                           course=None, 
                           analysis=None,
                           all_courses=all_courses)
    

@app.route('/instructor_download', methods=['GET'])
def instructor_download():
    if 'user_id' not in session or session.get('role') not in ['Instructor', 'Admin']:
        return redirect(url_for('login'))

    current_instructor_id = session.get('user_id')

    instructor_sections = Section.query.filter_by(instructor_id=current_instructor_id).all()
    course_ids = [s.course_id for s in instructor_sections]
    instructor_courses = Course.query.filter(Course.id.in_(course_ids)).all()
    feedbacks_data = db.session.query(Feedback, Course, Section).\
        join(Course, Feedback.course_id == Course.id).\
        join(Section, Feedback.section_id == Section.id).\
        filter(Section.instructor_id == current_instructor_id).\
        order_by(Feedback.created_at.desc()).all()

    return render_template('download.html', 
                           courses=instructor_courses, 
                           sections=instructor_sections, 
                           feedbacks=feedbacks_data)

@app.route('/admin/assign_course', methods=['POST'])
def assign_course():
    instructor_id = request.form.get('instructor_id')
    course_id = request.form.get('course_id')
    section = request.form.get('section')
    assignment = course_instructor.insert().values(
        instructor_id=instructor_id, 
        course_id=course_id, 
        section_number=section
    )
    db.session.execute(assignment)
    db.session.commit()
    return "Instructor assigned to section successfully!"

@app.route('/student/select_course')
def student_selection():
    all_courses = Course.query.all()
    #bring in the instructor for each course to show them in the drop-down list
    return render_template('student_select.html', courses=all_courses)

@app.route('/export_data', methods=['POST'])
def export_data():
    course_id = request.form.get('course_id')
    section_id = request.form.get('section_id')
    file_format = request.form.get('format')
    #We have added an option in the HTML called 'language' with a value of 'ar' or 'en' (we will try to add this feature and work on it in the future as soon as possible) 
    selected_lang = request.form.get('language', 'en') 
    # retrieving data from the database
    query = db.session.query(Feedback, Course).join(Course, Feedback.course_id == Course.id)
    
    if course_id and course_id != 'all':
        query = query.filter(Feedback.course_id == course_id)
    if section_id and section_id != 'all':
        query = query.filter(Feedback.section_id == section_id)
    
    results = query.all()
    
    if not results:
        flash("No data is available for export based on the selected filters.", "info")
        return redirect(url_for('instructor_download'))

    #processing function based on the selected language
    def format_content(text):
        if not text: return ""
        text = str(text)
        
        if selected_lang == 'ar':
            reshaped = arabic_reshaper.reshape(text)
            return get_display(reshaped)
        else:
            return text

    if selected_lang == 'ar':
        headers = ["التاريخ", "محتوى التعليق", "الشعبة", "المادة"]
        headers = [format_content(h) for h in headers]
        filename_prefix = "تقرير_فيد_وايز"
    else:
        headers = ["Date", "Feedback Content", "Section", "Course"]
        filename_prefix = "FeedWise_Report"

    #export CSV:
    if file_format == 'csv':
        data = []
        for fb, course in results:
            if selected_lang == 'ar':
                data.append({
                    headers[3]: course.code,
                    headers[2]: fb.section_id,
                    headers[1]: fb.content,
                    headers[0]: fb.created_at.strftime('%Y-%m-%d') if fb.created_at else 'N/A'
                })
            else:
                data.append({
                    "Course": course.code,
                    "Section": fb.section_id,
                    "Feedback": fb.content,
                    "Date": fb.created_at.strftime('%Y-%m-%d') if fb.created_at else 'N/A'
                })
        
        df = pd.DataFrame(data)
        output = io.StringIO()
        df.to_csv(output, index=False, encoding='utf-8-sig')
        
        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = f"attachment; filename={filename_prefix}.csv"
        response.headers["Content-type"] = "text/csv; charset=utf-8"
        return response

    #export PDF:
    elif file_format == 'pdf':
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []

        font_path = os.path.join(os.path.dirname(__file__), 'arial.ttf')
        if selected_lang == 'ar' and os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('ArabicFont', font_path))
            font_name = 'ArabicFont'
        else:
            font_name = 'Helvetica'

        table_data = [headers]
        for fb, course in results:
            table_data.append([
                fb.created_at.strftime('%Y-%m-%d') if fb.created_at else 'N/A',
                format_content(fb.content),
                str(fb.section_id),
                format_content(course.code)
            ])

        t = Table(table_data, colWidths=[90, 260, 60, 110])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d6cdf')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white])
        ]))
        
        elements.append(t)
        doc.build(elements)
        
        buffer.seek(0)
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'{filename_prefix}.pdf',
            mimetype='application/pdf'
        )

    return redirect(url_for('instructor_download'))

#helper function
def update_analysis_in_db(course_id, stats, summary, keywords):
    """Update the analysis results in the database"""
    #searching for material using the ID
    course = Course.query.get(course_id)
    if course:
        new_analysis = Analysis(
            course_id=course.id,
            positive_points={"score": stats.get('POSITIVE')},
            negative_points={"keywords": keywords}
        )
        course.summary = summary
        course.pos_score = stats.get('POSITIVE')
        
        db.session.add(new_analysis)
        db.session.commit()

def get_part(start, end, data):
    import re
    pattern = re.escape(start) + r"(.*?)(?=" + re.escape(end) + r"|$)"
    match = re.search(pattern, data, re.S | re.I)
    if match:
        extracted = match.group(1).strip()
        return re.sub(r'[\[\]\*\#\-]', '', extracted).strip()
    return ""

def get_clean_part(start_marker, end_marker, full_text):
    import re
    pattern = re.escape(start_marker) + r"(.*?)(?=" + re.escape(end_marker) + r"|$)"
    match = re.search(pattern, full_text, re.S | re.I)
    if match:
        content = match.group(1).strip()
        content = re.sub(r'[\[\]\*\#\-]', '', content)
        noise = ['date', 'feedback', 'content', 'section', 'course', 'cs101', 'se305']
        for w in noise:
            content = re.sub(rf'\b{w}\b', '', content, flags=re.IGNORECASE)
        return content.strip()
    return ""

def get_ai_insight(text_content):
    #prompt to AI give a summary
    prompt = f"""
    Read these student opinions: '{text_content}'
    Task: Write a human-like summary. If they say "clear material", write "The teaching quality is high".
    
    Format:
    SUMMARY_DATA: [Your paragraph here]
    STRENGTHS_DATA: [3 points]
    IMPROVEMENTS_DATA: [3 points]
    """
    return summarize_text(prompt)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user_id' not in session or session.get('user_role') not in ['Instructor', 'Admin']:
        flash("Unauthorized access.", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        #to get the ID of the selected course from the drop-down list
        course_id_raw = request.form.get('course_id')
        file = request.files.get('file')

        if not course_id_raw or not file:
            flash("Please select a course and upload a file.", "warning")
            return redirect(request.url)

        try:
            course_id = int(course_id_raw) 
            
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config.get('UPLOAD_FOLDER', 'uploads'), filename)
            file.save(filepath)
            
            #extracting text from PDF
            raw_text = extract_text_from_pdf(filepath)
            
            if raw_text.strip():
                #cleaning the text of excess words such as Date, Section,etc
                clean_content = clean_text(raw_text)
                noise_list = ['date', 'feedback', 'content', 'section', 'course', '101', '305']
                for w in noise_list:
                    clean_content = re.sub(rf'\b{w}\b', '', clean_content, flags=re.IGNORECASE)

                #requesting analysis from AI
                full_response = get_ai_insight(clean_content)

                #extracting parts using the updated get_part function
                ai_summary = get_part("SUMMARY_START:", "STRENGTHS_START:", full_response)
                pos_pts = get_part("STRENGTHS_START:", "IMPROVEMENTS_START:", full_response)
                neg_pts = get_part("IMPROVEMENTS_START:", "END_OF_DATA", full_response)

                if "long" in clean_content.lower() and "long" not in neg_pts.lower():
                    neg_pts = "Long assignments, " + neg_pts

                #database update for the selected item only
                analysis = Analysis.query.filter_by(course_id=course_id).first()
                if not analysis:
                    analysis = Analysis(course_id=course_id)
                    db.session.add(analysis)
                
                #storing extracted data
                analysis.summary_text = ai_summary if len(ai_summary) > 15 else "Student feedback provided regarding teaching methods and materials."
                analysis.positive_points = pos_pts if pos_pts else "Engagement with materials"
                analysis.negative_points = neg_pts if neg_pts else "General improvements"
                
                #analyze emotions and accurately retain the percentage
                res = analyze_sentiment(clean_content)
                if isinstance(res, dict):
                    if res['label'] == 'POSITIVE':
                        analysis.pos_score = int(res['score'] * 100)
                    else:
                        analysis.pos_score = int(100 - (res['score'] * 100))
                else:
                    analysis.pos_score = res
                
                db.session.commit()
                flash(f"Analysis for {Course.query.get(course_id).code} updated successfully!", "success")
                
            if os.path.exists(filepath): os.remove(filepath)
            return redirect(url_for('dashboard'))

        except Exception as e:
            db.session.rollback()
            print(f"Upload Error: {e}")
            flash("An error occurred during processing.", "danger")

    courses = Course.query.all() 
    return render_template('upload.html', courses=courses)

@app.route('/get_sections/<int:course_id>')
def get_sections(course_id):
    #bring the sections related to the specified course
    sections = Section.query.filter_by(course_id=course_id).all()
    
    section_list = []
    for sec in sections:
        #retrieve the name of the instructor associated with this section
        instructor = User.query.get(sec.instructor_id)
        instructor_name = f"{instructor.first_name} {instructor.last_name}" if instructor else "Unknown"
        
        section_list.append({
            'id': sec.id,
            'section_number': sec.section_number,
            'instructor_name': instructor_name
        })
    
    return jsonify({'sections': section_list})

@app.route('/student_feedback', methods=['GET', 'POST'])
def student_feedback():
    if 'user_id' not in session: 
        return redirect(url_for('login'))
    
    courses = Course.query.all()

    if request.method == 'POST':
        student_id = session['user_id']
        course_id = request.form.get('course_id')
        section_id = request.form.get('section_id')
        comment = request.form.get('comment')

        if not comment or not course_id or not section_id:
            flash("Please fill in all fields.", "warning")
            return redirect(url_for('student_feedback'))

        #ensure not repeat
        existing_feedback = Feedback.query.filter_by(
            student_id=student_id, 
            course_id=course_id
        ).first()

        if existing_feedback:
            flash("You have already submitted feedback for this course!", "danger")
            return redirect(url_for('student_feedback'))

        selected_section = db.session.get(Section, section_id)
        if not selected_section:
            flash("Invalid section selection.", "danger")
            return redirect(url_for('student_feedback'))

        instructor_id = selected_section.instructor_id

        new_f = Feedback(
            content=comment,
            student_id=student_id,
            course_id=course_id,
            instructor_id=instructor_id,
            section_id=section_id,
            created_at=datetime.utcnow()
        )
        
        try:
            db.session.add(new_f)
            db.session.commit()

            #AI Integration
            
            #sentiment analysis of the current comment
            sentiment_score = analyze_sentiment(comment)
            
            #bring all comments for this course to update the summary and dashboard
            all_course_feedbacks = Feedback.query.filter_by(course_id=course_id).all()
            combined_text = " ".join([f.content for f in all_course_feedbacks])
            new_summary = summarize_text(combined_text)
            analysis_record = Analysis.query.filter_by(course_id=course_id).first()
            
            if analysis_record:
                analysis_record.summary_text = new_summary
                analysis_record.pos_score = sentiment_score
                analysis_record.analysis_date = datetime.utcnow()
            else:
                analysis_record = Analysis(
                    course_id=course_id,
                    summary_text=new_summary,
                    pos_score=sentiment_score,
                    analysis_date=datetime.utcnow()
                )
                db.session.add(analysis_record)
            
            db.session.commit()

            flash("Feedback submitted and analyzed successfully!", "success")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error during feedback processing: {e}")
            flash("System error, please try again later.", "danger")
            
        return redirect(url_for('student_feedback'))

    return render_template('student_feedback.html', courses=courses)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    success = False

    if 'user_preferences' not in session:
        session['user_preferences'] = {
            'theme': user.theme if hasattr(user, 'theme') else 'light',
            'language': 'en',
            'notifications': True
        }

    if request.method == 'POST':
        new_theme = request.form.get('theme')
        user.theme = new_theme
        
        #update name(last and first)
        full_name = request.form.get('full_name')
        if full_name:
            parts = full_name.split(maxsplit=1)
            user.first_name = parts[0]
            if len(parts) > 1:
                user.last_name = parts[1]
        
        #update email
        user.email = request.form.get('email')
        
        #change password
        new_password = request.form.get('password')
        if new_password and len(new_password.strip()) >= 6:
            from werkzeug.security import generate_password_hash
            user.password = generate_password_hash(new_password)
        
        try:
            db.session.commit()
            success = True
            
            session['user_theme'] = user.theme
            session['user_name'] = f"{user.first_name} {user.last_name}"

            prefs = session.get('user_preferences', {}).copy()
            prefs['theme'] = user.theme
            session['user_preferences'] = prefs
            session.modified = True
            
        except Exception as e:
            db.session.rollback()
            print(f"Error: {e}")

    return render_template('settings.html', 
                           user_data=user, 
                           user_preferences=session['user_preferences'], 
                           saved_theme=user.theme, 
                           success=success)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


#data preparation:
if __name__ == '__main__':
    with app.app_context():
        #create tables
        db.create_all()
        
        if not User.query.filter_by(email="instructor@example.com").first():
            db.session.add(User(first_name="Ahmed", last_name="Mohammed", email="instructor@example.com", password="password123", role="Instructor"))
            db.session.add(User(first_name="Fatema", last_name="Majeed", email="fatema@uob.edu.bh", password="password123", role="Instructor"))
            db.session.add(User(first_name="Admin", last_name="User", email="admin@uob.edu.bh", password="admin123", role="Admin"))
            db.session.commit()

        all_ins_users = User.query.filter_by(role='Instructor').all()
        for ui in all_ins_users:
            display_name = f"Dr. {ui.first_name} {ui.last_name}"
            if not Instructor.query.filter_by(name=display_name).first():
                db.session.add(Instructor(name=display_name))
        db.session.commit()

        #adding courses
        first_instructor = User.query.filter_by(role='Instructor').first()
        
        if first_instructor and not Course.query.filter_by(code='CS101').first():
            new_course = Course(
                code='CS101', 
                name='Computer Science', 
                instructor_id=first_instructor.id
            )
            db.session.add(new_course)
            db.session.commit()

        #adding sections and linking them to the course and instructor
        current_course = Course.query.filter_by(code='CS101').first()
        if current_course and not Section.query.filter_by(section_number="101").first():
            db.session.add(Section(
                section_number="101",
                course_id=current_course.id,      
                instructor_id=first_instructor.id 
            ))
            db.session.commit()
            
        print("✅ Database initialized successfully with all relationships!")

    app.run(debug=True)

@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.remove()
    