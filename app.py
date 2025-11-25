import os
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "5ff4c1d72c885b500a5292ddeee269858d0f3a53f6192815da4290a591b23be9")

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://manthan2006sharma_db_user:manthan123@cluster0.giptp1d.mongodb.net/healthcare?appName=Cluster0")
client = MongoClient(MONGO_URI)
db = client["ai_emergency_db"]

users_col = db["users"]
hospitals_col = db["hospitals"]
symptom_history_col = db["symptom_history"]
emergency_actions_col = db["emergency_actions"]


def login_required(view_func):
    from functools import wraps
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapper


def seed_hospitals():
    if hospitals_col.count_documents({}) == 0:
        sample = [
            {
                "name": "City Care Hospital",
                "address": "Main Road, Sector 10",
                "status": "24/7",
                "ambulance_available": True,
                "contact_number": "+91-9876543210"
            },
            {
                "name": "Green Life Clinic",
                "address": "Near Central Park",
                "status": "Open",
                "ambulance_available": False,
                "contact_number": "+91-9123456780"
            }
        ]
        hospitals_col.insert_many(sample)


def calculate_risk(symptoms_text, duration, severity):
    text = (symptoms_text or "").lower()
    score = 0

    high_keywords = ["chest pain", "shortness of breath", "breathing difficulty", "severe bleeding"]
    medium_keywords = ["high fever", "vomiting", "dizziness", "continuous pain"]
    low_keywords = ["headache", "cough", "mild fever", "cold"]

    for kw in high_keywords:
        if kw in text:
            score += 5
    for kw in medium_keywords:
        if kw in text:
            score += 3
    for kw in low_keywords:
        if kw in text:
            score += 1

    if severity == "severe":
        score += 4
    elif severity == "moderate":
        score += 2

    if duration == ">3":
        score += 2
    elif duration == "1-3":
        score += 1

    if score >= 9:
        level = "High"
        msg = "Immediate medical attention recommended. Contact emergency services."
    elif score >= 4:
        level = "Medium"
        msg = "Consult a doctor soon and monitor your symptoms closely."
    else:
        level = "Low"
        msg = "Symptoms appear mild. Rest, hydrate, and keep monitoring."

    return level, msg


@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("All fields are required.")
            return redirect(url_for("signup"))

        if users_col.find_one({"email": email}):
            flash("Email already registered.")
            return redirect(url_for("signup"))

        password_hash = generate_password_hash(password)
        user = {
            "full_name": name,
            "email": email,
            "password_hash": password_hash,
            "created_at": datetime.utcnow()
        }
        users_col.insert_one(user)
        flash("Signup successful. Please login.")
        return redirect(url_for("login"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = users_col.find_one({"email": email})
        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.")
            return redirect(url_for("login"))

        session["user_id"] = str(user["_id"])
        session["user_name"] = user["full_name"]
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    user_id = session["user_id"]
    last_symptom = symptom_history_col.find_one(
        {"user_id": user_id},
        sort=[("timestamp", -1)]
    )
    last_action = emergency_actions_col.find_one(
        {"user_id": user_id},
        sort=[("timestamp", -1)]
    )
    total_checks = symptom_history_col.count_documents({"user_id": user_id})
    return render_template(
        "dashboard.html",
        last_symptom=last_symptom,
        last_action=last_action,
        total_checks=total_checks
    )


@app.route("/emergency", methods=["POST"])
@login_required
def emergency():
    action_type = request.form.get("type", "unknown")
    emergency_actions_col.insert_one({
        "user_id": session["user_id"],
        "action_type": action_type,
        "timestamp": datetime.utcnow()
    })
    return jsonify({"status": "ok", "message": f"{action_type.capitalize()} request simulated."})


@app.route("/symptom-checker")
@login_required
def symptom_checker_page():
    return render_template("symptom_checker.html")


@app.route("/api/check-symptoms", methods=["POST"])
@login_required
def api_check_symptoms():
    data = request.get_json() or {}
    symptoms = data.get("symptoms", "")
    duration = data.get("duration", "<1")
    severity = data.get("severity", "mild")

    level, msg = calculate_risk(symptoms, duration, severity)

    symptom_history_col.insert_one({
        "user_id": session["user_id"],
        "symptoms_text": symptoms,
        "risk_level": level,
        "timestamp": datetime.utcnow()
    })

    return jsonify({
        "risk_level": level,
        "message": msg
    })


@app.route("/hospitals")
@login_required
def hospitals():
    seed_hospitals()
    status_filter = request.args.get("status")
    ambulance_filter = request.args.get("ambulance")

    query = {}
    if status_filter == "open":
        query["status"] = {"$in": ["Open", "24/7"]}
    if ambulance_filter == "yes":
        query["ambulance_available"] = True

    hospitals_list = list(hospitals_col.find(query))
    return render_template("hospitals.html", hospitals=hospitals_list)


@app.route("/tips")
@login_required
def tips():
    tips_data = [
        {
            "title": "Minor cuts",
            "text": "Clean the area with water, apply gentle pressure to stop bleeding, and cover with a clean bandage."
        },
        {
            "title": "Fever care",
            "text": "Rest, drink plenty of fluids, and monitor temperature. Seek medical help if very high or persistent."
        },
        {
            "title": "Fainting",
            "text": "Lay the person flat, raise their legs slightly, and ensure fresh air while checking for breathing."
        }
    ]
    return render_template("tips.html", tips=tips_data)


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user_id = session.get("user_id")
    if not user_id:
        # handle error or redirect to login
        return redirect(url_for("login"))

    # Convert user ID string to ObjectId
    user = users_col.find_one({"_id": ObjectId(user_id)})

    if request.method == "POST":
        new_name = request.form.get("name", "").strip()
        new_password = request.form.get("password", "").strip()
        updates = {}
        if new_name:
            updates["full_name"] = new_name
            session["user_name"] = new_name  # update session display name
        if new_password:
            from werkzeug.security import generate_password_hash
            updates["password_hash"] = generate_password_hash(new_password)

        if updates:
            users_col.update_one({"_id": ObjectId(user_id)}, {"$set": updates})
            flash("Profile updated successfully.")
            return redirect(url_for("profile"))

    return render_template("profile.html", user=user)

@app.route("/history")
@login_required
def history():
    user_id = session["user_id"]
    symptoms = list(symptom_history_col.find({"user_id": user_id}).sort("timestamp", -1))
    actions = list(emergency_actions_col.find({"user_id": user_id}).sort("timestamp", -1))
    return render_template("history.html", symptoms=symptoms, actions=actions)


if __name__ == "__main__":
    app.run(debug=True)

