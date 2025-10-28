from flask import Flask, render_template, url_for, request, flash, redirect, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, current_user, login_required, logout_user
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, text

from flask_mail import Mail, Message
import random




counties = ['Mombasa', 'Kwale', 'Kilifi', 'Tana' 'River', 'Lamu', 'Taita/Taveta', 'Garissa', 'Wajir', 'Mandera'
    , 'Marsabit', 'Isiolo', 'Meru', 'Tharaka-Nithi', 'Embu', 'Kitui', 'Machakos', 'Makueni', 'Nyandarua', 'Nyeri',
            'Kirinyaga', "Murang'a", 'Kiambu', 'Turkana', 'West Pokot', 'Samburu', 'Trans Nzoia', 'Uasin Gishu',
            'Elgeyo/Marakwet', 'Nandi', 'Baringo', 'Laikipia', 'Nakuru', 'Narok', 'Kajiado', 'Kericho', 'Bomet',
            'Kakamega', 'Vihiga', 'Bungoma', 'Busia', 'Siaya', 'Kisumu', 'Homa Bay', 'Migori', 'Kisii', 'Nyamira',
            'Nairobi City']

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key-goes-here'

# 2FA
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Use your SMTP provider
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'munazayyas@gmail.com'  # Your email
app.config['MAIL_PASSWORD'] = 'ifwx sjak mthx swxn'  # Use app password or token
app.config['MAIL_DEFAULT_SENDER'] = app.config['MAIL_USERNAME']

mail = Mail(app)


class Base(DeclarativeBase):
    pass


# setting up database

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.db'

db = SQLAlchemy(model_class=Base)
db.init_app(app)


# CONFIGURE TABLES
class Users(UserMixin, db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    serviceNumber: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    email: Mapped[str] = mapped_column(String(250), nullable=False)
    password: Mapped[str] = mapped_column(String(250), nullable=False)


class PersonalDetails(UserMixin, db.Model):
    __tablename__ = "personal_details"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    birth_id: Mapped[str] = mapped_column(Integer, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    dob: Mapped[str] = mapped_column(String(250), nullable=False)
    phone: Mapped[str] = mapped_column(String(250), nullable=False)
    emergencyName: Mapped[str] = mapped_column(String(250), nullable=False)
    emergencyRelationship: Mapped[str] = mapped_column(String(250), nullable=False)
    emergencyContact: Mapped[str] = mapped_column(String(250), nullable=False)
    county: Mapped[str] = mapped_column(String(250), nullable=False)
    address: Mapped[str] = mapped_column(String(250), nullable=False)
    bloodGroup: Mapped[str] = mapped_column(String(250))
    gender: Mapped[str] = mapped_column(String(250), nullable=False)


class Diagnosis(UserMixin, db.Model):
    __tablename__ = "diagnosis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(Integer, nullable=False)
    appointment: Mapped[str] = mapped_column(String(250), nullable=False)
    symptoms: Mapped[str] = mapped_column(String(250), nullable=False)
    notes: Mapped[str] = mapped_column(String(250), nullable=False)
    program: Mapped[str] = mapped_column(String(250), nullable=False)


with app.app_context():
    db.create_all()

login_manager = LoginManager()
login_manager.init_app(app)


# Create a user_loader callback
@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(Users, user_id)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/home')
@login_required
def home():
    patients = db.session.execute(text("SELECT * FROM personal_details")).fetchall()
    columns = ["id", "birth_id", "name", "dob", "phone", "emergencyName", "emergencyRelationship", "emergencyContact",
               "county", "address"
        , "bloodGroup", "gender"]
    patients_dict = [dict(zip(columns, patient)) for patient in patients]

    return render_template('home.html', patients=patients_dict, current_user=current_user)


@app.route('/register', methods=['POST', 'GET'])
def register():
    serviceNumbers = db.session.execute(db.select(Users.serviceNumber)).scalars().all()
    emails = db.session.execute(db.select(Users.email)).scalars().all()
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        serviceNumber = request.form['serviceNumber']
        password = request.form['password']
        repeatPassword = request.form['repeatPassword']
       
        if serviceNumber in serviceNumbers:
            flash(" The number exists. Login instead.")
            return redirect(url_for('login'))
        if email in emails:
            flash(" The email exists. Login instead.")
            return redirect(url_for('login'))
        if password != repeatPassword:
            flash("Passwords do not match")
            return redirect(url_for('register'))
         # ✅ Generate 6-digit code
        verification_code = str(random.randint(100000, 999999))

        # ✅ Store in session temporarily
        session['pending_user'] = {
            'name': name,
            'email': email,
            'serviceNumber': serviceNumber,
            'password': generate_password_hash(password, method='pbkdf2:sha256', salt_length=8),
            'code': verification_code,
        }
         # ✅ Send email
        msg = Message("Verify Your Email", recipients=[email])
        msg.body = f"Your verification code is: {verification_code}"
        mail.send(msg)

        flash("A verification code has been sent to your email.")
        return redirect(url_for('verify'))
       
        

    return render_template('register.html')

@app.route('/verify', methods=['POST', 'GET'])
def verify():
    if request.method == 'POST':
        code_entered = request.form['code']
        pending_user = session.get('pending_user')

        if not pending_user:
            flash("Session expired. Please register again.")
            return redirect(url_for('register'))

        if code_entered == pending_user['code']:
            # ✅ Create user
            new_user = Users(
                name=pending_user['name'],
                email=pending_user['email'],
                serviceNumber=pending_user['serviceNumber'],
                password=pending_user['password']
            )
            db.session.add(new_user)
            db.session.commit()

            # ✅ Clean up session
            session.pop('pending_user', None)

            flash("Email verified. Account created successfully.")
            login_user(new_user)
            return redirect('/home')
        else:
            flash("Invalid verification code.")
            return redirect(url_for('verify_email'))


    return render_template('verify.html')


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        serviceNumber = request.form['serviceNumber']
        password = request.form['password']
        user = db.session.execute(db.select(Users).where(Users.serviceNumber == serviceNumber)).scalar()
        if user:
            if check_password_hash(user.password, password):
                login_user(user)
                return redirect('/home')
            else:

                flash("Wrong password.")
                return redirect('login')
        else:
            flash("Service number does not exist")
            return redirect('login')
    return render_template('login.html')


@app.route('/addPatient', methods=['POST', 'GET'])
@login_required
def addPatient():
    if request.method == 'POST':
        birth_id = request.form['birth_id']
        name = request.form['name']
        dob = request.form['dob']
        phone = request.form['phone']
        emergencyName = request.form['emergencyName']
        emergencyRelationship = request.form['emergencyRelationship']
        emergencyContact = request.form['emergencyContact']
        county = request.form['county']
        address = request.form['address']
        bloodGroup = request.form['bloodGroup']
        gender = request.form['gender']

        details = PersonalDetails(
            birth_id=birth_id,
            name=name,
            dob=dob,
            phone=phone,
            emergencyName=emergencyName,
            emergencyRelationship=emergencyRelationship,
            emergencyContact=emergencyContact,
            county=county,
            address=address,
            bloodGroup=bloodGroup,
            gender=gender
        )
        db.session.add(details)
        db.session.commit()
        return redirect('home')

    return render_template('addPatient.html', counties=counties)


@app.route('/search', methods=['POST', 'GET'])
@login_required
def search():
    if request.method == 'POST':
        birth_id = request.form["search"]
        result = db.session.execute(db.select(PersonalDetails).where(PersonalDetails.birth_id == birth_id)).scalar()
        if result:
            return render_template('search.html', result=result)
        else:
            flash('No records found.')


@app.route('/profile/<patient_id>')
@login_required
def profile(patient_id):
    patient = db.get_or_404(PersonalDetails, patient_id)
    patient_diagnosis = db.get_or_404(Diagnosis, patient_id)
    return render_template('profile.html', patient=patient, patient_diagnosis=patient_diagnosis)


@app.route('/diagnosis/<patient_id>', methods=['POST', 'GET'])
@login_required
def diagnosis(patient_id):
    return render_template('diagnose.html', patient_id=patient_id)


@app.route('/submit_diagnosis/<patient_id>', methods=['POST', 'GET'])
@login_required
def submit_diagnosis(patient_id):
    if request.method == 'POST':
        appointment = request.form["appointment"]
        symptoms = request.form["symptoms"]
        notes = request.form["notes"]
        program = request.form["program"]

        diagnose = Diagnosis(
            patient_id=patient_id,
            appointment=appointment,
            symptoms=symptoms,
            notes=notes,
            program=program,
        )
        db.session.add(diagnose)
        db.session.commit()
        flash("Details submitted successfully")
        return redirect(url_for('home'))


@app.route('/api/data')
@login_required
def get_data():
    personal_data = PersonalDetails.query.all()
    result_1 = []
    for data in personal_data:
        personal_details = {
            'id': data.id,
            'birth_id': data.birth_id,
            'name': data.name,
            'dob': data.dob,
            'phone': data.phone,
            'emergencyName': data.emergencyName,
            'emergencyRelationship': data.emergencyRelationship,
            'emergencyContact': data.emergencyContact,
            'county': data.county,
            'address': data.address,
            'bloodGroup': data.bloodGroup,
            'gender': data.gender
        }
        result_1.append(personal_details)

    diagnosis_data = Diagnosis.query.all()
    result_2 = []
    for result in diagnosis_data:
        diagnose = {
            'patient_id': result.patient_id,
            'appointment': result.appointment,
            'symptoms': result.symptoms,
            'notes': result.notes,
            'program': result.program,
        }
        result_2.append(diagnose)

    combined_data = {
        'personal_details': result_1,
        'diagnosis_details': result_2,
    }
    return jsonify(combined_data)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
