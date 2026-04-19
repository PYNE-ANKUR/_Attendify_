from flask import Flask, render_template, request, jsonify, session
from pymongo import MongoClient
import random, time
import os

app = Flask(__name__)
app.secret_key = "secret123"

# ================= DB =================
mongo_uri = os.environ.get("MONGO_URI") 
client = MongoClient(mongo_uri)
db = client["attendify"]
# ================= HOME =================
@app.route('/')
def home():
    return render_template("index.html")

# ================= LOGIN =================
@app.route('/login')
def login():
    return render_template("login.html")

@app.route('/login-user', methods=['POST'])
def login_user():
    data = request.json

    user = db.users.find_one({
        "roll": data['roll'],
        "password": data['password']
    })

    if not user:
        return {"error": "Invalid login"}

    session['user'] = user['roll']
    session['role'] = user['role']

    return {"role": user['role']}

# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    return {"status": "logged out"}

# ================= DEVICE REGISTER =================
@app.route('/register')
def register():
    return render_template("register.html")

@app.route('/save-device', methods=['POST'])
def save_device():
    data = request.json

    user = db.users.find_one({"roll": data['roll']})

    if not user:
        return {"error": "User not found"}

    result = db.users.update_one(
        {"roll": data['roll']},
        {"$set": {"deviceKey": data['deviceKey']}}
    )

    if result.modified_count == 0:
        return {"error": "Device not saved"}

    return {"status": "Device Registered"}

# ================= ADMIN =================

# ----- DASHBOARD -----
@app.route('/admin')
def admin():
    return render_template("admin.html")

# ----- PAGES (GET) -----
@app.route('/add_student')
def add_student_page():
    return render_template("add_student.html")

@app.route('/add_teacher')
def add_teacher_page():
    return render_template("add_teacher.html")

@app.route('/add_subject')
def add_subject_page():
    return render_template("add_subject.html")

@app.route('/assign')
def assign_page():
    return render_template("assign.html")

@app.route('/admin_students')
def admin_students():
    return render_template("admin_students.html")

@app.route('/admin_teachers')
def admin_teachers():
    return render_template("admin_teachers.html")

@app.route('/admin_subjects')
def admin_subjects():
    return render_template("admin_subjects.html")

@app.route('/admin_mapping')
def admin_mapping():
    return render_template("admin_mapping.html")

# ----- API (POST) -----
@app.route('/add-student', methods=['POST'])
def add_student():
    data = request.json

    db.users.insert_one({
        "roll": data['roll'],
        "password": data['password'],
        "role": "student",
        "deviceKey": None
    })

    return {"status": "Student added"}

@app.route('/add-teacher', methods=['POST'])
def add_teacher():
    data = request.json

    db.users.insert_one({
        "roll": data['roll'],
        "password": data['password'],
        "role": "teacher"
    })

    return {"status": "Teacher added"}

@app.route('/add-subject', methods=['POST'])
def add_subject():
    data = request.json

    db.subjects.insert_one({
        "name": data['name'],
        "teacher": None,
        "students": []
    })

    return {"status": "Subject added"}

@app.route('/assign-subject', methods=['POST'])
def assign_subject():
    data = request.json

    db.subjects.update_one(
        {"name": data['subject']},
        {"$set": {"teacher": data['teacher']}}
    )

    return {"status": "Teacher assigned"}

@app.route('/assign-student', methods=['POST'])
def assign_student():
    data = request.json

    db.subjects.update_one(
        {"name": data['subject']},
        {"$addToSet": {"students": data['roll']}}
    )

    return {"status": "Student assigned"}

# ----- VIEW DATA -----
@app.route('/get-students')
def get_students():
    return jsonify(list(db.users.find({"role": "student"}, {"_id": 0})))

@app.route('/get-teachers')
def get_teachers():
    return jsonify(list(db.users.find({"role": "teacher"}, {"_id": 0})))

@app.route('/get-subjects')
def get_subjects():
    return jsonify(list(db.subjects.find({}, {"_id": 0})))

@app.route('/get-mapping')
def get_mapping():
    return jsonify(list(db.subjects.find({}, {"_id": 0})))


# ================= STUDENT =================

@app.route('/student')
def student_dashboard():
    return render_template("student_dashboard.html")

@app.route('/student_register')
def student_register():
    return render_template("student_register.html")

@app.route('/student_attendance')
def student_attendance():
    return render_template("student_attendance.html")

@app.route('/student_view')
def student_view():
    return render_template("student_view.html")

@app.route('/mark-attendance', methods=['POST'])
def mark_attendance():
    data = request.json

    user = db.users.find_one({"roll": data['roll']})

    if not user:
        return {"error": "User not found"}

    if user['password'] != data['password']:
        return {"error": "Wrong password"}

    if user.get("deviceKey") != data['deviceKey']:
        return {"error": "Unauthorized device"}

    session_db = db.sessions.find_one({
        "subject": data['subject'],
        "code": data['code'],
        "active": True
    })

    if not session_db:
        return {"error": "Invalid session"}

    if time.time() - session_db['startTime'] > session_db['duration']:
        return {"error": "Session expired"}

    db.attendance.insert_one({
        "roll": data['roll'],
        "subject": data['subject'],
        "time": time.time()
    })

    return {"status": "Attendance marked"}

@app.route('/student-percentage/<roll>')
def student_percentage(roll):
    subjects = db.subjects.find({"students": roll})

    result = []

    for sub in subjects:
        name = sub["name"]

        total = db.sessions.count_documents({"subject": name})
        attended = db.attendance.count_documents({
            "roll": roll,
            "subject": name
        })

        percent = (attended / total * 100) if total else 0

        result.append({
            "subject": name,
            "percentage": round(percent, 2)
        })

    return jsonify(result)

# ================= TEACHER =================

@app.route('/teacher')
def teacher_dashboard():
    return render_template("teacher.html")

@app.route('/teacher_mark')
def teacher_mark():
    return render_template("teacher_mark.html")

@app.route('/teacher_view')
def teacher_view():
    return render_template("teacher_view.html")

@app.route('/my-subjects')
def my_subjects():
    if 'user' not in session or session.get("role") != "teacher":
        return jsonify([])

    return jsonify(list(db.subjects.find(
        {"teacher": session['user']},
        {"_id": 0}
    )))

@app.route('/start-session', methods=['POST'])
def start_session():
    data = request.json

    code = str(random.randint(1000, 9999))

    db.sessions.insert_one({
        "subject": data['subject'],
        "teacher": session.get("user"),
        "code": code,
        "startTime": time.time(),
        "duration": int(data['duration']),
        "active": True
    })

    return {"code": code}

@app.route('/attendance-percentage/<subject>')
def attendance_percentage(subject):
    subject_data = db.subjects.find_one({"name": subject})

    if not subject_data:
        return jsonify([])

    students = subject_data.get("students", [])
    total = db.sessions.count_documents({"subject": subject})

    result = []

    for s in students:
        attended = db.attendance.count_documents({
            "roll": s,
            "subject": subject
        })

        percent = (attended / total * 100) if total else 0

        result.append({
            "roll": s,
            "percentage": round(percent, 2)
        })

    return jsonify(result)

@app.route('/get-current-user')
def get_current_user():
    return jsonify({
        "user": session.get("user"),
        "role": session.get("role")
    })

# ================= RUN =================
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)