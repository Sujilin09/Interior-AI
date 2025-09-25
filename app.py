# app.py
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from supabase import create_client, Client
from dotenv import load_dotenv
import hashlib

# Load environment variables
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")

# Utility: simple password hashing (better to use bcrypt/argon2)
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# ------------------ ROUTES ------------------

@app.route("/")
def index():
    return render_template("index.html")

# ----------- SIGNUP -----------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        role = request.form["role"]  # 'user' or 'designer'
        name = request.form["name"]
        email = request.form["email"]
        password = hash_password(request.form["password"])

        # Determine table and check for existing email
        table_name = "user_profiles" if role == "user" else "designers"
        existing = supabase.table(table_name).select("id").eq("email", email).execute()

        if existing.data:
            flash("Email already registered!", "danger")
            return redirect(url_for("signup"))

        # Insert into correct table
        if role == "user":
            supabase.table("user_profiles").insert({
                "user_name": name,
                "email": email,
                "password": password
            }).execute()
            flash("Signup successful! Now select your preferences.", "success")
            # User goes to preferences next, login will happen there
            return redirect(url_for("preferences", email=email))
        
        else: # role == 'designer'
            specialisation = request.form["specialisation"]
            insert_response = supabase.table("designers").insert({
                "designer_name": name,
                "email": email,
                "password": password,
                "specialisation": specialisation
            }).execute()
            
            # --- MODIFICATION START ---
            # FIX: Automatically log in the designer after signup
            if insert_response.data:
                designer = insert_response.data[0]
                session["user"] = {"id": designer["id"], "role": "designer", "name": designer["designer_name"]}
                flash(f"Welcome, {designer['designer_name']}! Your profile is created.", "success")
                return redirect(url_for("dashboard"))
            else:
                flash("Could not create designer profile. Please try again.", "danger")
                return redirect(url_for("signup"))
            # --- MODIFICATION END ---
            
    return render_template("signup.html")

# ----------- USER LOGIN -----------
@app.route("/login/user", methods=["GET", "POST"])
def login_user():
    if request.method == "POST":
        email = request.form["email"]
        password = hash_password(request.form["password"])

        res = supabase.table("user_profiles").select("*").eq("email", email).eq("password", password).execute()

        if res.data:
            user = res.data[0]
            session["user"] = {"id": user["id"], "role": "user", "name": user["user_name"]}
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials.", "danger")

    return render_template("login_user.html")

# ----------- DESIGNER LOGIN -----------
@app.route("/login/designer", methods=["GET", "POST"])
def login_designer():
    if request.method == "POST":
        email = request.form["email"]
        password = hash_password(request.form["password"])

        res = supabase.table("designers").select("*").eq("email", email).eq("password", password).execute()

        if res.data:
            designer = res.data[0]
            session["user"] = {"id": designer["id"], "role": "designer", "name": designer["designer_name"]}
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials.", "danger")

    return render_template("login_designer.html")

# -----------------------PREFERENCES-------------
@app.route("/preferences", methods=["GET", "POST"])
def preferences():
    if request.method == "POST":
        email = request.form["email"]
        preferences_list = request.form.getlist("preferences")
        
        supabase.table("user_preferences").insert({
            "email": email,
            "preferences": preferences_list
        }).execute()
        
        # --- MODIFICATION START ---
        # FIX: Automatically log in the user after they set preferences
        user_res = supabase.table("user_profiles").select("*").eq("email", email).execute()
        if user_res.data:
            user = user_res.data[0]
            session["user"] = {"id": user["id"], "role": "user", "name": user["user_name"]}
            flash("Preferences saved! Welcome to your dashboard.", "success")
            return redirect(url_for("dashboard"))
        else:
            # Fallback in case user is not found, though unlikely
            flash("Preferences saved! Please log in to continue.", "info")
            return redirect(url_for("login_user"))
        # --- MODIFICATION END ---

    email = request.args.get("email")
    return render_template("preferences.html", email=email)


# ----------- DASHBOARD (Role-based) -----------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("index"))

    user = session["user"]

    if user["role"] == "user":
        return render_template("dashboard_user.html", user=user)
    elif user["role"] == "designer":
        return render_template("dashboard_designer.html", user=user)
    else:
        flash("Unknown role.", "danger")
        return redirect(url_for("index"))

# ----------- LOGOUT -----------
@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)