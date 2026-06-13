from flask import Flask, render_template, request, redirect, session
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os
import pytz
from chatbot import get_chatbot_response
from predictor import predict_adherence, get_insights

# India Timezone
INDIA_TZ = pytz.timezone('Asia/Kolkata')

app = Flask(__name__)
app.secret_key = "mediguard"

USERS_FILE = "users.json"
MEDICINES_FILE = "medicines.json"
DOCTORS_FILE = "doctors.json"


def load_data(file):
    if os.path.exists(file):
        with open(file, "r") as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}


def save_data(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)


users = load_data(USERS_FILE)
medicines = load_data(MEDICINES_FILE)
doctors = load_data(DOCTORS_FILE)


@app.route("/")
def home():
    return render_template("index.html")


# ============ PATIENT REGISTER ============
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        doctor = request.form.get("doctor", "")

        if username in users:
            return "User already exists"

        users[username] = {
            "password": generate_password_hash(password),
            "doctor": doctor
        }
        save_data(USERS_FILE, users)
        return redirect("/login")

    return render_template("register.html", doctors=list(doctors.keys()))


# ============ PATIENT LOGIN ============
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username in users and check_password_hash(users[username]["password"], password):
            session["user"] = username
            session["role"] = "patient"
            return redirect("/dashboard")

        return "Invalid login"

    return render_template("login.html")


# ============ DOCTOR REGISTER ============
@app.route("/doctor/register", methods=["GET", "POST"])
def doctor_register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username in doctors:
            return "Doctor already exists"

        doctors[username] = {
            "password": generate_password_hash(password)
        }
        save_data(DOCTORS_FILE, doctors)
        return redirect("/doctor/login")

    return render_template("doctor_register.html")


# ============ DOCTOR LOGIN ============
@app.route("/doctor/login", methods=["GET", "POST"])
def doctor_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username in doctors and check_password_hash(doctors[username]["password"], password):
            session["user"] = username
            session["role"] = "doctor"
            return redirect("/doctor/dashboard")

        return "Invalid login"

    return render_template("doctor_login.html")


# ============ DOCTOR DASHBOARD ============
@app.route("/doctor/dashboard")
def doctor_dashboard():
    if "user" not in session or session.get("role") != "doctor":
        return redirect("/doctor/login")

    doctor = session["user"]

    my_patients = []
    for username, info in users.items():
        if isinstance(info, dict) and info.get("doctor") == doctor:
            patient_meds = medicines.get(username, [])

            total = len(patient_meds)
            taken = sum(1 for m in patient_meds if m.get("status") == "taken")
            missed = sum(1 for m in patient_meds if m.get("status") == "missed")
            pending = sum(1 for m in patient_meds if m.get("status") == "pending")

            my_patients.append({
                "name": username,
                "total": total,
                "taken": taken,
                "missed": missed,
                "pending": pending,
                "meds": patient_meds
            })

    return render_template("doctor_dashboard.html", doctor=doctor, patients=my_patients)


# ============ PATIENT DASHBOARD ============
@app.route("/dashboard")
def dashboard():
    if "user" not in session or session.get("role") != "patient":
        return redirect("/login")

    user = session["user"]
    user_meds = medicines.get(user, [])

    now = datetime.now(INDIA_TZ).strftime("%I:%M %p")
    today = datetime.now(INDIA_TZ).strftime("%Y-%m-%d")

    # Auto-add recurring medicines for today
    for m in list(user_meds):
        if m.get("recurring") == "daily" and m.get("date") != today:
            exists = any(
                x["name"] == m["name"] and x["time"] == m["time"] and x["date"] == today
                for x in user_meds
            )
            if not exists:
                user_meds.append({
                    "name": m["name"],
                    "time": m["time"],
                    "date": today,
                    "status": "pending",
                    "recurring": "daily"
                })

    medicines[user] = user_meds
    save_data(MEDICINES_FILE, medicines)

    for m in user_meds:
        if m["time"] == now:
            m["alert"] = "NOW"
        else:
            m["alert"] = ""

    return render_template("dashboard.html", user=user, meds=user_meds, current_time=now)


# ============ STATISTICS PAGE ============
@app.route("/stats")
def stats():
    if "user" not in session or session.get("role") != "patient":
        return redirect("/login")

    user = session["user"]
    user_meds = medicines.get(user, [])

    total = len(user_meds)
    taken = sum(1 for m in user_meds if m.get("status") == "taken")
    missed = sum(1 for m in user_meds if m.get("status") == "missed")
    pending = sum(1 for m in user_meds if m.get("status") == "pending")

    if total > 0:
        taken_percent = round((taken / total) * 100, 1)
        missed_percent = round((missed / total) * 100, 1)
        pending_percent = round((pending / total) * 100, 1)
    else:
        taken_percent = missed_percent = pending_percent = 0

    return render_template("stats.html",
                           user=user,
                           total=total,
                           taken=taken,
                           missed=missed,
                           pending=pending,
                           taken_percent=taken_percent,
                           missed_percent=missed_percent,
                           pending_percent=pending_percent)


# ============ ADD MEDICINE ============
@app.route("/add", methods=["POST"])
def add():
    if "user" not in session or session.get("role") != "patient":
        return redirect("/login")

    user = session["user"]

    name = request.form["name"]
    time_24 = request.form["time"]
    time_obj = datetime.strptime(time_24, "%H:%M")
    time = time_obj.strftime("%I:%M %p")
    date = request.form.get("date") or datetime.now(INDIA_TZ).strftime("%Y-%m-%d")
    recurring = request.form.get("recurring", "no")

    if user not in medicines:
        medicines[user] = []

    medicines[user].append({
        "name": name,
        "time": time,
        "date": date,
        "status": "pending",
        "recurring": recurring
    })

    save_data(MEDICINES_FILE, medicines)
    return redirect("/dashboard")


@app.route("/take/<int:index>")
def take(index):
    if "user" not in session:
        return redirect("/login")
    user = session["user"]
    medicines[user][index]["status"] = "taken"
    save_data(MEDICINES_FILE, medicines)
    return redirect("/dashboard")


@app.route("/miss/<int:index>")
def miss(index):
    if "user" not in session:
        return redirect("/login")
    user = session["user"]
    medicines[user][index]["status"] = "missed"
    save_data(MEDICINES_FILE, medicines)
    return redirect("/dashboard")


@app.route("/delete/<int:index>")
def delete(index):
    if "user" not in session:
        return redirect("/login")
    user = session["user"]
    medicines[user].pop(index)
    save_data(MEDICINES_FILE, medicines)
    return redirect("/dashboard")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ============ AI CHATBOT ============
@app.route("/chatbot", methods=["GET", "POST"])
def chatbot():
    if "user" not in session or session.get("role") != "patient":
        return redirect("/login")
    
    response = None
    user_message = ""
    
    if request.method == "POST":
        user_message = request.form["message"]
        response = get_chatbot_response(user_message)
    
    return render_template("chatbot.html", 
                          response=response, 
                          user_message=user_message)


# ============ AI INSIGHTS ============
@app.route("/insights")
def insights():
    if "user" not in session or session.get("role") != "patient":
        return redirect("/login")
    
    user = session["user"]
    user_meds = medicines.get(user, [])
    
    prediction = predict_adherence(user_meds)
    smart_insights = get_insights(user_meds)
    
    return render_template("insights.html",
                          user=user,
                          prediction=prediction,
                          insights=smart_insights)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)