import secrets
import smtplib
import ssl
import string
from smtpd import SMTPServer
from smtplib import SMTPServerDisconnected
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from flask import Flask, render_template, request, redirect,jsonify, url_for,session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from sqlalchemy.orm import sessionmaker, scoped_session
from datetime import datetime, timedelta
from sqlalchemy import or_,event
import random
from flask_mail import Message,Mail

app = Flask(__name__)
app.config['SECRET_KEY'] = 'VBD-Private-limited-startup-2021'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///messages.db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///employee.db'
engine = create_engine('sqlite:///employees.db', echo=True)
# Initialize Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)
db = SQLAlchemy(app)

Session = scoped_session(sessionmaker())
users = {}
# Leave model for storing leave requests
class LeaveRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('employee.id'))
    name = db.Column(db.String(100))
    eid = db.Column(db.String(100))
    start_date = db.Column(db.String(100))
    end_date = db.Column(db.String(100))
    reason = db.Column(db.String(200))
    noofdays=db.Column(db.String(200))
    approved_by_hr = db.Column(db.Boolean, default=None)
    approved_by_department_head = db.Column(db.Boolean, default=None)


@login_manager.user_loader
def load_user(user_id):
    return Employee.query.get(int(user_id))

class Employee(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    eid = db.Column(db.String(100), nullable=False,unique=True)
    name = db.Column(db.String(100))
    contactNo = db.Column(db.String(100))
    email = db.Column(db.String(100))
    address = db.Column(db.String(100))
    blood = db.Column(db.String(100))
    department = db.Column(db.String(100))
    designation = db.Column(db.String(100))
    password = db.Column(db.String(100), nullable=False)
    totaldays = db.Column(db.Integer, default=24)
    dob = db.Column(db.String(50))
    role = db.Column(db.String(50))
    resign = db.Column(db.Boolean, default=False)
    supervisor_id = db.Column(db.String, db.ForeignKey('employee.eid'), nullable=True)
    supervisor = db.relationship('Employee', remote_side=[eid], backref='subordinates', foreign_keys=[supervisor_id])

    team_leader_id = db.Column(db.String, db.ForeignKey('employee.eid'), nullable=True)
    team_leader = db.relationship('Employee', remote_side=[eid], backref='team_members', foreign_keys=[team_leader_id])

    status = db.Column(db.String(10), nullable=False, default='stay')
    resignation_date = db.Column(db.Date)

    def update_status(self):
        today = datetime.now().date()
        if today.month == 1 and today.day == 1 or (
                self.dob and today.month == int(self.dob.split("-")[1]) and today.day == int(self.dob.split("-")[2])):
            self.totaldays = 24
            db.session.commit()
    def update_status(self):
        if self.resignation_date and self.resignation_date + timedelta(days=30) <= datetime.now().date():
            self.status = 'exit'
            db.session.commit()
    def __init__(self, eid, email, password, role, **kwargs):
        self.eid = eid
        self.email = email
        self.password = password
        self.role = role

        # Initialize the rest of the attributes if provided
        self.name = kwargs.get('name')
        self.contactNo = kwargs.get('contactNo')
        self.address = kwargs.get('address')
        self.blood = kwargs.get('blood')
        self.resign = kwargs.get('resign')
        self.dob = kwargs.get('dob')
        self.department = kwargs.get('department')
        self.designation = kwargs.get('designation')
        self.supervisor_id = kwargs.get('supervisor_id')
        self.team_leader_id = kwargs.get('team_leader_id')
        self.resignation_date = kwargs.get('resignation_date')



def generate_password(length=10):
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(secrets.choice(characters) for _ in range(length))
    return password

@app.route('/add_employee/<user_id>', methods=['GET', 'POST'])
@login_required
def add_employee(user_id):
    user = Employee.query.get(user_id)
    if not user:
        return "Employee not found.", 404
    department_heads = Employee.query.filter(
        or_(Employee.role == 'Department Head', Employee.role == 'HR')
    ).all()
    if request.method == 'POST':
        name = request.form.get('name')
        eid = request.form.get('eid')
        contactNo = request.form.get('contactNo')
        address = request.form.get('address')
        blood = request.form.get('blood')
        dob = request.form.get('dob')
        email = request.form.get('email')
        department = request.form.get('department')
        designation = request.form.get('designation')
        team_leader_id = request.form.get('team_leader_id')
        supervisor_id = request.form.get('supervisor_name')

        user.name = name
        user.eid = eid
        user.contactNo = contactNo
        user.email = email
        user.address = address
        user.blood = blood
        user.dob = dob
        user.department = department
        user.designation = designation
        user.supervisor_id = supervisor_id
        user.team_leader_id = team_leader_id
        resignation_date = request.form.get('resignation_date')

        if resignation_date:
            user.resignation_date = datetime.strptime(resignation_date, '%Y-%m-%d')
        else:
            user.resignation_date = None

        try:
            db.session.commit()
            print('Employee details updated successfully!', 'success')
            return redirect(url_for('add_employee', user_id=user_id))
        except:
            db.session.rollback()
            print('Failed to update employee details. Please try again.', 'danger')

    return render_template('add_employee.html', user=user,department_heads=department_heads)


def send_email(email, eid):
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    sender_email = 'vividobots@gmail.com'
    sender_password = 'auensrlcmhgwmygc'

    subject = 'Account Created'
    body = f'Your account has been created.\nEmployee ID: {eid}\n Create your password in new password'

    message = MIMEMultipart()
    message['Subject'] = subject
    message['From'] = sender_email
    message['To'] = email
    message.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(message)
        print("Email sent successfully!")
    except smtplib.SMTPAuthenticationError:
        print("Failed to authenticate with the SMTP server.")
    except Exception as e:
        print("An error occurred while sending the email:", str(e))


@app.route('/everysearch', methods=['GET', 'POST'])
def index():
    employees = Employee.query.all()
    current_date = datetime.now().date()
    for employee in employees:
        if employee.resignation_date and employee.resignation_date + timedelta(days=30) <= current_date:
            employee.status = 'exit'
        elif employee.resignation_date:
            employee.status = 'applying_for_resignation'
        else:
            employee.status = 'stay'
    db.session.commit()
    sorted_employees = sorted(employees, key=lambda employee: int(employee.eid[3:]))
    return render_template('employee_list.html', employees=sorted_employees,user=current_user)

@app.route('/everysearchdh', methods=['GET', 'POST'])
def index1():
    employees = Employee.query.all()
    current_date = datetime.now().date()
    for employee in employees:
        if employee.resignation_date and employee.resignation_date + timedelta(days=30) <= current_date:
            employee.status = 'exit'
        elif employee.resignation_date:
            employee.status = 'applying_for_resignation'
        else:
            employee.status = 'stay'
    db.session.commit()
    sorted_employees = sorted(employees, key=lambda employee: int(employee.eid[3:]))
    return render_template('employee_list1.html', employees=sorted_employees,user=current_user)

@app.route('/update_resign/<int:user_id>', methods=['POST'])
def update_resign(user_id):
    resign_value = request.form.get('resign')
    employee = Employee.query.get(user_id)

    if resign_value == 'true':
        employee.resign = True
    elif resign_value == 'false':
        employee.resign = False

    db.session.commit()

    sorted_employees = sorted(Employee.query.all(), key=lambda e: int(e.eid[3:]))
    return render_template('employee_list.html', employees=sorted_employees, user=current_user)




@app.route('/apply_resignation/<int:user_id>', methods=["GET", "POST"])
@login_required
def apply_resignation(user_id):
    employee = Employee.query.get(user_id)

    if request.method == 'POST':
        resignation_date = request.form['resignation_date']
        resignation_date = datetime.strptime(resignation_date, '%Y-%m-%d').date()

        employee.resignation_date = resignation_date
        db.session.commit()

        print("Resignation applied successfully!", "success")
        return redirect(url_for('apply_resignation', user_id=employee.id))  # Redirect to employee profile or success page

    return render_template('apply_resignation.html', employee=employee, user=current_user)


@app.route('/search', methods=['GET', 'POST'])
@login_required
def search_by_team_leader():
    if request.method == 'POST':

        team_leader_id = request.form['team_leader_id']
        employees = Employee.query.filter_by(team_leader_id=team_leader_id).all()
        if employees:
            return render_template('search_result_team_leader.html', employees=employees, team_leader_id=team_leader_id,user=current_user)
        else:
            return render_template('search_by_team_leader.html',user=current_user)

    return render_template('search_employee.html',user=current_user)
@app.route('/')
def home():
    return render_template('login.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        eid = request.form['eid']
        password = request.form['password']

        # Check if the user clicked on the "Forgot Password" link
        if request.form.get('forgot_password'):
            return redirect(url_for('forgot_password'))

        # Query the database for the user
        user = Employee.query.filter_by(eid=eid).first()

        # Check if the user exists and the password is correct
        if user is None or user.password != password:
            return render_template('login.html', message='Invalid email or password.')

        if user.status == 'exit':
            return render_template('login.html', message='Your status is "exit". You cannot login.')

        login_user(user)

        if user.role == 'HR':
            return render_template('hr_employee_details.html', employee=user)
        elif user.role == 'Department Head':
            return render_template('DH_employee_details.html', employee=user)
        else:
            return render_template('unique_employee_details.html', employee=user)

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    if request.method == 'POST':
        email = request.form['email']
        eid = request.form['eid']
        role = request.form['role']
        password = request.form.get('generatedPassword')

        # Save the employee details to your database
        # Send the email with the generated password
        send_email(email,eid)
        existing_user = Employee.query.filter_by(eid=eid).first()

        if existing_user:
            # Email already exists, handle the situation (e.g., show an error message)
            return render_template('register.html', message='Employee already registered.',user=current_user)
        user = Employee.query.filter_by(eid=eid).first()
        if user:
            return render_template('register.html', error=True)
        new_user = Employee(eid=eid, email=email, password=password, role=role)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('register',user_id=new_user.id))
    return render_template('register.html', error=False,user=current_user)



@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/hr_again/<user_id>')
@login_required
def hr_again(user_id):
    user = Employee.query.get(user_id)
    login_user(user)
    employee = Employee.query.get(user.id)
    if user.role == 'HR':
        return render_template('hr_employee_details.html', employee=employee,user=current_user)
    elif user.role == 'Department Head':
        return render_template('DH_employee_details.html', employee=employee,user=current_user)
    else:
        return render_template('unique_employee_details.html', employee=employee,user=current_user)

@app.route('/dh_again/<user_id>')
@login_required
def dh_again(user_id):
    user = Employee.query.get(user_id)
    login_user(user)
    employee = Employee.query.get(user.id)
    if user.role == 'HR':
        return render_template('hr_employee_details.html', employee=employee, user=current_user)
    elif user.role == 'Department Head':
        return render_template('DH_employee_details.html', employee=employee, user=current_user)
    else:
        return render_template('unique_employee_details.html', employee=employee, user=current_user)

@app.route('/employee_again/<user_id>')
@login_required
def employee_again(user_id):
    user = Employee.query.get(user_id)
    login_user(user)
    employee = Employee.query.get(user.id)
    if user.role == 'HR':
        return render_template('hr_employee_details.html', employee=employee, user=current_user)
    elif user.role == 'Department Head':
        return render_template('DH_employee_details.html', employee=employee, user=current_user)
    else:
        return render_template('unique_employee_details.html', employee=employee, user=current_user)


@app.route('/hr_leave_requests', methods=['GET','POST'])
@login_required
def hr_leave_requests():
    if not current_user.role == 'HR':
        return redirect(url_for('login'))

    if request.method == 'POST':
        request_id = request.form['request_id']
        approval_status = request.form['approval_status']

        leave_request = LeaveRequest.query.get(request_id)
        if leave_request:
            if approval_status == 'approved':
                leave_request.approved_by_hr = True
            elif approval_status == 'disapproved':
                leave_request.approved_by_hr = False

            db.session.commit()

    leave_requests = LeaveRequest.query.all()
    return render_template('hr_leave_requests.html', leave_requests=leave_requests,user=current_user)

@app.route('/leave', methods=['GET', 'POST'])
@login_required
def leave_requests():
    if request.method == 'POST':
        request_id = request.form['request_id']
        approved = request.form['approved'] == 'True'
        leave_request = LeaveRequest.query.get(request_id)
        leave_request.approved_by_hr = approved
        db.session.commit()

    leave_requests = LeaveRequest.query.filter_by(user_id=current_user.id)
    return render_template('leave_requests.html', leave_requests=leave_requests,user=current_user)


@app.route('/department_leave_requests', methods=['GET', 'POST'])
@login_required
def department_leave_requests():
    if not (current_user.role == 'Department Head' or current_user.role == 'HR'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        request_id = request.form['request_id']
        approval_status = request.form['approval_status']

        leave_request = LeaveRequest.query.get(request_id)
        if leave_request:
            if approval_status == 'approved':
                leave_request.approved_by_department_head = True
            elif approval_status == 'disapproved':
                leave_request.approved_by_department_head = False

            db.session.commit()

    if current_user.role == 'HR':
        leave_requests = LeaveRequest.query.join(Employee).filter(
            Employee.team_leader_id == current_user.eid
        ).all()
    else:
        leave_requests = LeaveRequest.query.join(Employee).filter(
            Employee.team_leader_id == current_user.eid
        ).all()

    return render_template('department_leave_requests.html', leave_requests=leave_requests, user=current_user)


@app.route('/req', methods=['GET', 'POST'])
@login_required
def leave_request():
    if request.method == 'POST':
        name = request.form.get('name')
        eid = request.form.get('eid')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        reason = request.form.get('reason')
        noofdays = int(request.form.get('noofdays'))  # Convert to an integer

        # Find the employee by their 'eid'
        employee = Employee.query.filter_by(eid=eid).first()

        if not employee:
            jsonify("Employee not found.", "error")
        elif noofdays <= 0:
            jsonify("No. of days must be greater than zero.", "error")
        elif employee.totaldays < noofdays:
            jsonify("Insufficient leave days.", "error")
        else:
            leave_request = LeaveRequest(user_id=current_user.id, eid=eid, name=name, start_date=start_date,
                                         end_date=end_date, reason=reason, noofdays=noofdays)
            db.session.add(leave_request)

            # Deduct the leave days from the employee's totaldays
            employee.totaldays -= noofdays

            db.session.commit()
            jsonify("Leave request submitted successfully.", "success")

    return render_template('request_form.html', user=current_user)

@app.route('/update_approval_hr/<int:request_id>', methods=['POST'])
@login_required
def update_approval_hr(request_id):
    if not current_user.role == 'HR':
        return redirect(url_for('hr_leave_requests'))

    approval_status = request.form['approval_status']

    leave_request = LeaveRequest.query.get(request_id)
    if leave_request:
        leave_request.approved_by_hr = (approval_status == 'approved')
        db.session.commit()

    return redirect(url_for('hr_leave_requests'))

@app.route('/update_approval_department_head/<int:request_id>', methods=['POST'])
@login_required
def update_approval_department_head(request_id):
    if not (current_user.role == 'Department Head' or current_user.role == 'HR'):
        return redirect(url_for('department_leave_requests'))

    approval_status = request.form['approval_status']

    leave_request = LeaveRequest.query.get(request_id)
    if leave_request:
        leave_request.approved_by_department_head = (approval_status == 'approved')
        db.session.commit()

    return redirect(url_for('department_leave_requests'))



def generate_otp(length=6):
    digits = "0123456789"
    otp = "".join(random.choice(digits) for _ in range(length))
    return otp

# Define the send_otp_email function
def send_otp_email(recipient_email, otp):
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    sender_email = 'vividobots@gmail.com'
    sender_password = 'auensrlcmhgwmygc'

    message = MIMEMultipart()
    message['Subject'] = 'Password Reset OTP'
    message['From'] = sender_email
    message['To'] = recipient_email

    text = f'Your OTP for password reset is: {otp}'
    message.attach(MIMEText(text, 'plain'))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(message)
        print("Email sent successfully!")
    except smtplib.SMTPAuthenticationError:
        print("Failed to authenticate with the SMTP server.")
    except Exception as e:
        print("An error occurred while sending the email:", str(e))

@app.route('/verify_otp/<eid>', methods=['GET', 'POST'])
def verify_otp(eid):
    if request.method == 'POST':
        otp = request.form['otp']
        stored_otp = session.get('otp')
        stored_eid = session.get('eid')

        if otp == stored_otp and eid == stored_eid:
            return redirect(url_for('reset_password', eid=eid))
        else:
            return "Invalid OTP"

    return render_template('otp_verification.html', eid=eid)

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        eid = request.form['eid']
        # Check if the provided EID exists in the database
        user = Employee.query.filter_by(eid=eid).first()
        if user:
            # Generate and send an OTP to the user's email
            otp = generate_otp()
            send_otp_email(user.email, otp)
            # Store the OTP and EID in the session for verification
            session['otp'] = otp
            session['eid'] = eid
            return redirect(url_for('verify_otp', eid=eid))
        else:
            return "Invalid Employee ID"

    return render_template('forget_password.html')


@app.route('/reset_password/<eid>', methods=['GET', 'POST'])
def reset_password(eid):
    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password == confirm_password:
            user = Employee.query.filter_by(eid=eid).first()
            if user:
                # Update the user's password in the database
                user.password = new_password
                db.session.commit()
                return render_template('login.html')
            else:
                return "Invalid Employee ID"
        else:
            return "Passwords do not match"

    return render_template('reset_password.html', eid=eid)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run()
