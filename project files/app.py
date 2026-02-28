from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import re
from datetime import datetime, timedelta
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import traceback
from datetime import timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

def to_ist(utc_dt):
    if utc_dt is None:
        return None
    return utc_dt.replace(tzinfo=timezone.utc).astimezone(IST)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Email Configuration - UPDATE THESE WITH YOUR EMAIL
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'floodsavior@gmail.com'  # CHANGE THIS
app.config['MAIL_PASSWORD'] = 'lzql vbhu fbsm ckjm'  # ⚠️ CHANGE THIS - generate new!

db = SQLAlchemy(app)

# Admin credentials (static - as per your requirement)
admins = {
    'ns_admin': {'password': 'admin123', 'city': 'Nagarjuna Sagar', 'dam': 'Nagarjuna Sagar'},
    'kalyani_admin': {'password': 'admin123', 'city': 'Tirupati', 'dam': 'Kalyani Dam'},
    'srisailam_admin': {'password': 'admin123', 'city': 'Srisailam', 'dam': 'Srisailam Dam'},
    'somasila_admin': {'password': 'admin123', 'city': 'Nellore', 'dam': 'Somasila Dam'},
    'prakasam_admin': {'password': 'admin123', 'city': 'Vijayawada', 'dam': 'Prakasam Barrage'}
}

# Make admins available to all templates





@app.route('/help', methods=['GET', 'POST'])
def submit_help():
    if request.method == 'POST':
        name = request.form.get('name')
        mobile = request.form.get('mobile')
        email = request.form.get('email')
        location = request.form.get('location')
        issue = request.form.get('issue')

        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Help Desk Request from {name}"
            msg['From'] = app.config['MAIL_USERNAME']
            msg['To'] = "floodsavior@gmail.com"

            html = f"""
            <html>
            <body>
              <h2>New Help Desk Request</h2>
              <p><strong>Name:</strong> {name}</p>
              <p><strong>Mobile:</strong> {mobile}</p>
              <p><strong>Email:</strong> {email}</p>
              <p><strong>Location:</strong> {location}</p>
              <p><strong>Issue:</strong><br>{issue}</p>
            </body>
            </html>
            """
            msg.attach(MIMEText(html, 'html'))

            with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
                server.starttls()
                server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
                server.send_message(msg)

            # show success message
            return render_template('help_desk.html', success=True)
        except Exception as e:
            flash(f"Failed to send request: {e}", 'danger')
            return render_template('help_desk.html', success=False)

    # GET request
    return render_template('help_desk.html', success=False)

@app.context_processor
def inject_admins():
    return dict(admins=admins)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    language = db.Column(db.String(30), nullable=False)
    password = db.Column(db.String(200), nullable=False)

    # existing fields...
    email_alerts = db.Column(db.Boolean, default=True)
    last_risk_level = db.Column(db.String(20), default=None)  # NEW

    # NEW: simple on/off for alerts
from datetime import datetime
# ...

class CommunityPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='posts')



@app.route('/help_desk')
def help_desk():
    return render_template("help_desk.html")

@app.route('/community/post', methods=['POST'])
def add_community_post():
    if 'user_id' not in session or session.get('user_type') != 'user':
        flash('Please login first!', 'warning')
        return redirect(url_for('login'))

    user = db.session.get(User, session['user_id'])
    if not user:
        flash('User not found!', 'danger')
        return redirect(url_for('login'))

    content = request.form.get('content', '').strip()
    if not content:
        flash('Message cannot be empty.', 'danger')
        return redirect(url_for('user_dashboard'))

    try:
        post = CommunityPost(user_id=user.id, city=user.city, content=content)
        db.session.add(post)
        db.session.commit()
        flash('Message posted to community.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to post message: {e}', 'danger')
    return redirect(url_for('community_updates'))

@app.route('/community')
def community_updates():
    if 'user_id' not in session or session.get('user_type') != 'user':
        flash('Please login first!', 'warning')
        return redirect(url_for('login'))

    user = db.session.get(User, session['user_id'])
    if not user:
        flash('User not found!', 'danger')
        return redirect(url_for('login'))

    posts = CommunityPost.query.filter_by(city=user.city) \
    .order_by(CommunityPost.created_at.desc()) \
    .limit(50).all()

    for post in posts:
        post.ist_time = to_ist(post.created_at)


    return render_template('community_updates.html',
                           user=user,
                           posts=posts)
@app.route('/user/profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session or session.get('user_type') != 'user':
        flash('Please login first!', 'warning')
        return redirect(url_for('login'))

    user = db.session.get(User, session['user_id'])
    if not user:
        flash('User not found!', 'danger')
        return redirect(url_for('login'))

    try:
        user.name = request.form.get('name', user.name)
        new_email = request.form.get('email', user.email)
        new_phone = request.form.get('phone', user.phone)

        user.email = new_email
        user.phone = new_phone

        # Checkbox: present => True, absent => False
        user.email_alerts = 'email_alerts' in request.form

        db.session.commit()
        session['user_name'] = user.name
        flash('Profile updated successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to update profile: {e}', 'danger')

    return redirect(url_for('user_dashboard'))

# REAL EMAIL FUNCTION
def get_alert_email_content(language, user_name, risk_category):
    templates = {
        "English": {
            "subject": f"Flood Alert ({risk_category})",
            "body": f"""
            <h2>Hello {user_name},</h2>
            <p>⚠️ Flood risk level is <b>{risk_category}</b> in your area.</p>
            <p>Please stay alert and follow official instructions.</p>
            """
        },

        "Telugu": {
            "subject": f"వరద హెచ్చరిక ({risk_category})",
            "body": f"""
            <h2>హలో {user_name},</h2>
            <p>⚠️ మీ ప్రాంతంలో వరద ప్రమాద స్థాయి <b>{risk_category}</b>.</p>
            <p>దయచేసి అప్రమత్తంగా ఉండి అధికారుల సూచనలు పాటించండి.</p>
            """
        },

        "Hindi": {
            "subject": f"बाढ़ चेतावनी ({risk_category})",
            "body": f"""
            <h2>नमस्ते {user_name},</h2>
            <p>⚠️ आपके क्षेत्र में बाढ़ का खतरा <b>{risk_category}</b> है।</p>
            <p>कृपया सतर्क रहें और अधिकारियों के निर्देशों का पालन करें।</p>
            """
        },

        "Tamil": {
            "subject": f"வெள்ள அபாய எச்சரிக்கை ({risk_category})",
            "body": f"""
            <h2>வணக்கம் {user_name},</h2>
            <p>⚠️ உங்கள் பகுதியில் வெள்ள அபாய நிலை <b>{risk_category}</b>.</p>
            <p>தயவுசெய்து எச்சரிக்கையுடன் இருந்து அதிகாரிகளின் அறிவுறுத்தல்களை பின்பற்றவும்.</p>
            """
        },

        "Kannada": {
            "subject": f"ನೆರೆ ಎಚ್ಚರಿಕೆ ({risk_category})",
            "body": f"""
            <h2>ಹಲೋ {user_name},</h2>
            <p>⚠️ ನಿಮ್ಮ ಪ್ರದೇಶದಲ್ಲಿ ನೆರೆ ಅಪಾಯದ ಮಟ್ಟ <b>{risk_category}</b> ಆಗಿದೆ.</p>
            <p>ದಯವಿಟ್ಟು ಎಚ್ಚರಿಕೆಯಿಂದಿರಿ ಮತ್ತು ಅಧಿಕಾರಿಗಳ ಸೂಚನೆಗಳನ್ನು ಪಾಲಿಸಿ.</p>
            """
        }
    }

    # fallback to English if language not found
    return templates.get(language, templates["English"])

def send_welcome_email(user_email, user_name):
    """Send actual welcome email using SMTP"""
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Welcome {user_name}! 🎉 - Flood Prediction System"
        msg['From'] = app.config['MAIL_USERNAME']
        msg['To'] = user_email
        
        # Create HTML email content
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #0d6efd 0%, #198754 100%); 
                          color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border: 1px solid #ddd; }}
                .footer {{ background: #333; color: white; padding: 15px; text-align: center; 
                          border-radius: 0 0 10px 10px; font-size: 12px; }}
                .btn {{ background: #0d6efd; color: white; padding: 12px 25px; 
                       text-decoration: none; border-radius: 5px; display: inline-block; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to Flood Prediction System! 🎉</h1>
                </div>
                <div class="content">
                    <h2>Hello {user_name},</h2>
                    <p>Thank you for registering with our Flood Prediction and Monitoring System!</p>
                    
                    <p><strong>Your account has been successfully created.</strong></p>
                    
                    <h3>📋 Account Details:</h3>
                    <ul>
                        <li><strong>Name:</strong> {user_name}</li>
                        <li><strong>Email:</strong> {user_email}</li>
                        <li><strong>Registration Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
                    </ul>
                    
                    <h3>🚀 Get Started:</h3>
                    <ol>
                        <li>Monitor flood predictions for your city</li>
                        <li>Receive real-time alerts</li>
                        <li>Access emergency resources</li>
                        <li>Contact local authorities</li>
                    </ol>
                    
                    <div style="text-align: center; margin: 25px 0;">
                        <a href="http://127.0.0.1:5000/login" class="btn">
                            Login to Dashboard
                        </a>
                    </div>
                    
                    <p>Stay safe and prepared,<br>
                    <strong>Flood Prediction System Team</strong></p>
                </div>
                <div class="footer">
                    <p>© 2024 Flood Prediction and Monitoring System. All rights reserved.</p>
                    <p>This is an automated email, please do not reply.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Attach HTML
        msg.attach(MIMEText(html, 'html'))
        # Send email
        with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
            server.starttls()
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.send_message(msg)
        
        #print(f"✅ REAL EMAIL SENT to {user_email}")
        return True
        
    except Exception as e:
        #print(f"❌ Email sending failed: {e}")
        return False

def send_alert_email(user_email, user_name, language, risk_category):
    try:
        content = get_alert_email_content(language, user_name, risk_category)

        msg = MIMEMultipart('alternative')
        msg['Subject'] = content["subject"]
        msg['From'] = app.config['MAIL_USERNAME']
        msg['To'] = user_email

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            {content["body"]}
            <p><b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Stay safe,<br><b>Flood Prediction System</b></p>
        </body>
        </html>
        """

        msg.attach(MIMEText(html, 'html', 'utf-8'))

        with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
            server.starttls()
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.send_message(msg)

        return True
    except Exception as e:
        print("Email error:", e)
        return False


# Routes
@app.route('/')
def home():
    return render_template('index.html')

# User Registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        city = request.form['city']
        language = request.form['language']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Validation
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('register'))
        
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            flash('Invalid email format!', 'danger')
            return redirect(url_for('register'))
        
        if not re.match(r'^[0-9]{10}$', phone):
            flash('Phone number must be 10 digits!', 'danger')
            return redirect(url_for('register'))
        
        # Check if user exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered!', 'danger')
            return redirect(url_for('register'))
        
        # Create new user
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(
            name=name,
            email=email,
            phone=phone,
            city=city,
            language=language,
            password=hashed_password
        )
        
        try:
            db.session.add(new_user)
            db.session.commit()
            
            #print(f"\n✅ Database commit successful for user: {name}")
            
            # Send welcome email
            #print(f"📨 Sending welcome email to {email}...")
            email_sent = send_welcome_email(email, name)
            
            # if email_sent:
            #     #print(f"✅ Welcome email sent successfully")
            #     flash('Registration successful! Welcome email sent. Please login.', 'success')
            # else:
            #     #print(f"⚠️ Welcome email failed, but registration succeeded")
            #     flash('Registration successful! (Email notification failed). Please login.', 'warning')
                
            return redirect(url_for('login'))
            
        except Exception as e:
            # print(f"\n❌ Registration error: {e}")
            # print(traceback.format_exc())
            flash(f'Error in registration: {str(e)}', 'danger')
    
    return render_template('register.html')

# User Login

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session and session.get('user_type') == 'user':
        return redirect(url_for('user_dashboard'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['user_type'] = 'user'

            # send login notification only if toggle is ON
            if getattr(user, 'email_alerts', True):
                #send_login_email(user.email, user.name)
                pass

            flash('Login successful!', 'success')
            return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid email or password!', 'danger')

    return render_template('login.html')


# User Dashboard

@app.route('/user/dashboard')
def user_dashboard():
    if 'user_id' not in session or session.get('user_type') != 'user':
        flash('Please login first!', 'warning')
        return redirect(url_for('login'))

    user_id = session.get('user_id')
    user = db.session.get(User, user_id)
    if not user:
        flash('User not found!', 'danger')
        session.clear()
        return redirect(url_for('login'))

    dam_status = get_dam_status_for_city(user.city)
    weather = get_weather_for_city(user.city)
    risk_level = get_risk_level_for_city(user.city)

    
    risk_info = get_risk_level_for_city(user.city)

    try:
        if (
        risk_info
        and risk_info.get('level') in ['High', 'Critical']
        and getattr(user, 'email_alerts', True)
    ):
            last_level = user.last_risk_level

            if last_level != risk_info['level']:
                send_alert_email(
                user.email,
                user.name,
                user.language,
                risk_info['level']
            )
                user.last_risk_level = risk_info['level']
                db.session.commit()

    except Exception as e:
        print("Risk email error:", e)


    posts = CommunityPost.query.filter_by(city=user.city) \
                           .order_by(CommunityPost.created_at.desc()) \
                           .limit(20).all()

    return render_template(
    "user_dashboard.html",
    user=user,
    admins=admins,
    dam_status=dam_status,
    weather=weather,
    risk_info=risk_info,
    posts=posts,
)



# Admin Login
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username in admins and admins[username]['password'] == password:
            session['admin_id'] = username
            session['admin_name'] = username.replace('_admin', '').replace('_', ' ').title()
            session['admin_city'] = admins[username]['city']
            session['admin_dam'] = admins[username]['dam']
            session['user_type'] = 'admin'
            flash('Admin login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin credentials!', 'danger')
    
    return render_template('admin_login.html')

# Admin Dashboard
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin_id' not in session or session.get('user_type') != 'admin':
        flash('Please login as admin first!', 'warning')
        return redirect(url_for('admin_login'))
    
    # Get all users for this admin's city
    users = User.query.filter_by(city=session['admin_city']).all()
    total_users = len(users)
    
    return render_template('admin_dashboard.html', 
                         admin_name=session['admin_name'],
                         city=session['admin_city'],
                         dam=session['admin_dam'],
                         users=users,
                         total_users=total_users)

from flask import Flask, render_template, request, redirect, url_for, flash, session
# ...

@app.route('/admin/user/<int:user_id>/delete', methods=['POST'])
def admin_delete_user(user_id):
    if 'admin_id' not in session or session.get('user_type') != 'admin':
        flash('Please login as admin first!', 'warning')
        return redirect(url_for('admin_login'))

    # limit admin to own city users
    admin_city = session.get('admin_city')
    user = User.query.filter_by(id=user_id, city=admin_city).first()
    if not user:
        flash('User not found or not in your city.', 'danger')
        return redirect(url_for('admin_dashboard'))

    try:
        db.session.delete(user)
        db.session.commit()
        flash('User deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to delete user: {e}', 'danger')

    return redirect(url_for('admin_dashboard'))
def send_admin_broadcast_email(user_email, user_name, city, message):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Important Flood Update - {city}"
        msg['From'] = app.config['MAIL_USERNAME']
        msg['To'] = user_email

        html = f"""
        <html>
        <body>
          <h2>Hello {user_name},</h2>
          <p>This is an important update from the local reservoir administrator for <strong>{city}</strong>.</p>
          <p>{message}</p>
          <p>Stay safe,<br><strong>Flood Prediction System</strong></p>
        </body>
        </html>
        """
        msg.attach(MIMEText(html, 'html'))

        with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
            server.starttls()
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.send_message(msg)
        return True
    except Exception:
        return False
@app.route('/admin/broadcast', methods=['POST'])
def admin_broadcast():
    if 'admin_id' not in session or session.get('user_type') != 'admin':
        flash('Please login as admin first!', 'warning')
        return redirect(url_for('admin_login'))

    admin_city = session.get('admin_city')
    message = request.form.get('message', '').strip()
    if not message:
        flash('Message cannot be empty.', 'danger')
        return redirect(url_for('admin_dashboard'))

    users = User.query.filter_by(city=admin_city).all()
    count = 0
    for u in users:
        if send_admin_broadcast_email(u.email, u.name, admin_city, message):
            count += 1

    flash(f'Broadcast sent to {count} users in {admin_city}.', 'success')
    return redirect(url_for('admin_dashboard'))


# Logout
@app.route('/logout')
def logout():
    user_name = session.get('user_name', 'Unknown')
    admin_name = session.get('admin_name', 'Unknown')
    
    #print(f"\n🚪 Logout requested by: {user_name or admin_name}")
    
    # Clear specific session variables
    session.pop('user_id', None)
    session.pop('user_name', None)
    session.pop('user_type', None)
    session.pop('admin_id', None)
    session.pop('admin_name', None)
    session.pop('admin_city', None)
    session.pop('admin_dam', None)
    
    #print(f"✅ Session cleared")
    flash('You have been logged out!', 'info')
    return redirect(url_for('home'))

# Create database tables
with app.app_context():
    db.create_all()
    #print("\n✅ Database tables created/verified")



import pandas as pd
import os

# ... after other routes ...

@app.route('/admin/dataset')
def admin_dataset():
    if 'admin_id' not in session or session.get('user_type') != 'admin':
        flash('Please login as admin first!', 'warning')
        return redirect(url_for('admin_login'))
    
    try:
        # Read the CSV file
        csv_path = 'final_features_dataset.csv'
        
        if not os.path.exists(csv_path):
            flash('Dataset file not found!', 'danger')
            return redirect(url_for('admin_dashboard'))
        
        # Read first 50 rows
        df = pd.read_csv(csv_path)
        total_rows = len(df)
        
        # Get top 50 rows
        top_50 = df.head(100)
        
        # Convert to list of dictionaries for template
        data = top_50.to_dict('records')
        
        # Get columns for table headers
        columns = top_50.columns.tolist()
        
        # Get unique dams and cities count
        unique_dams = df['dam_name'].nunique() if 'dam_name' in df.columns else 'N/A'
        unique_cities = df['city'].nunique() if 'city' in df.columns else 'N/A'
        
        # Get date range if available
       # Get date range if available
        if 'date' in df.columns:
            try:
        # Try multiple date formats
                df['date'] = pd.to_datetime(df['date'], errors='coerce', dayfirst=True)
                valid_dates = df['date'].dropna()
                if not valid_dates.empty:
                    date_range = f"{valid_dates.min().strftime('%Y-%m-%d')} to {valid_dates.max().strftime('%Y-%m-%d')}"
                else:
                    date_range = 'Invalid date format'
            except:
                date_range = 'Date parsing error - showing raw dates'
        else:
            date_range = 'Not available'
        
        return render_template('admin_dataset.html',
                             data=data,
                             columns=columns,
                             total_rows=total_rows,
                             unique_dams=unique_dams,
                             unique_cities=unique_cities,
                             date_range=date_range,
                             admin_name=session['admin_name'])
        
    except Exception as e:
        print(f"Error reading dataset: {e}")
        flash(f'Error loading dataset: {str(e)}', 'danger')
        return redirect(url_for('admin_dashboard'))
import json
import requests

# --- Dam & weather helpers ---

DAM_STATUS_FILE = "dam_status.json"

# Simple mapping from city to dam name (match your JSON)
CITY_TO_DAM = {
    "Nagarjuna Sagar": "Nagarjuna Sagar",
    "Tirupati": "Kalyani Dam",
    "Srisailam": "Srisailam Dam",
    "Nellore": "Somasila Dam",
    "Vijayawada": "Prakasam Barrage",
}

def load_dam_status():
    """Load latest dam status for all dams from JSON."""
    try:
        with open(DAM_STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def get_dam_status_for_city(city):
    """Return dam status dict for the dam linked to a user city."""
    dam_name = CITY_TO_DAM.get(city)
    if not dam_name:
        return None
    for rec in load_dam_status():
        if rec.get("Dam_Name") == dam_name:
            return rec
    return None

def get_weather_for_city(city):
    coords = {
        "Nagarjuna Sagar": (16.57, 79.32),
        "Tirupati": (13.63, 79.42),
        "Srisailam": (16.07, 78.87),
        "Nellore": (14.44, 79.99),
        "Vijayawada": (16.51, 80.64),
    }
    latlon = coords.get(city)
    if not latlon:
        return None

    lat, lon = latlon
    try:
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            "&current=temperature_2m,relative_humidity_2m,precipitation,"
            "wind_speed_10m,wind_direction_10m,cloud_cover,apparent_temperature"
        )
        r = requests.get(url, timeout=5)
        data = r.json().get("current", {})
        return {
            "temperature": data.get("temperature_2m"),
            "feels_like": data.get("apparent_temperature"),
            "humidity": data.get("relative_humidity_2m"),
            "precipitation": data.get("precipitation"),
            "wind_speed": data.get("wind_speed_10m"),
            "wind_dir": data.get("wind_direction_10m"),
            "cloud_cover": data.get("cloud_cover"),
        }
    except Exception:
        return None


def get_risk_level_for_city(city):
    dam_status = get_dam_status_for_city(city)
    if not dam_status:
        return {"level": "Unknown", "message": "No dam data available for this city."}

    try:
        cur = float(dam_status.get("Current Level (Metre)", 0))
        maxlvl = float(dam_status.get("Max Level (Metre)", 0))
        cs=float(dam_status.get("Current Storage (TMC)",0))
        ms=float(dam_status.get("Max Storage (TMC)",0))
        if maxlvl <= 0:
            return {"level": "Unknown", "message": "Dam levels are not yet configured for this location."}
        ratio = cs/ms
        #ratio=predict()
    except Exception:
        return {"level": "Unknown", "message": "Dam level values are invalid or missing."+cs}

    if ratio < 0.60:
        return {
            "level": "Low",
            "message": "Water levels are comfortably below the danger mark.\n Stay informed but no immediate concern."
        }
    elif ratio < 0.80:
        return {

            "level": "Medium",
            "message": "  Water levels are rising.\n Stay alert and keep an eye on updates from authorities."
        }
    elif ratio < 0.95:
        return {
            "level": "High",
            "message": " Water levels are close to the danger mark.\n Prepare evacuation plans and follow official instructions."
        }
    else:
        return {
            "level": "Critical",
            "message": " Water levels are extremely close to or above danger levels.\n Move to safer locations immediately if advised."
        }

# def predict():
#     return water_level
@app.context_processor
def inject_risk_cities():
    cities = [
        "Nagarjuna Sagar",
        "Tirupati",
        "Srisailam",
        "Nellore",
        "Vijayawada"
    ]

    risk_cities = []
    for city in cities:
        info = get_risk_level_for_city(city)
        if info["level"] in ["High", "Critical"]:
            risk_cities.append({
                "city": city,
                "level": info["level"]
            })

    return dict(risk_cities=risk_cities)

if __name__ == "__main__":
    app.run(debug=True)
