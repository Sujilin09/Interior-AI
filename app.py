import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
import hashlib
import httpx
from supabase import create_client, Client
from dotenv import load_dotenv
from supabase.lib.client_options import ClientOptions as SyncClientOptions 

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Custom httpx client (development only)
# IMPORTANT: In production, remove verify=False or replace with proper certificate handling.
# Note: For security, ensure proper certificate handling is used outside of local development.
http_client = httpx.Client(verify=False)

options = SyncClientOptions(
    httpx_client=http_client
)

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY,
    options=options
)

app = Flask(__name__)
# Replace with a strong, complex key stored in environment variables
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey_fallback") 

# Utility: simple password hashing (Use bcrypt/argon2 in production)
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
        # 1️⃣ Extract role
        role = request.form.get("role")
        if not role:
            flash("Role not specified.", "danger")
            return redirect(url_for("signup"))

        # 2️⃣ Basic fields extraction
        try:
            name = request.form["name"]
            email = request.form["email"]
            password_hash = hash_password(request.form["password"])
        except KeyError:
            flash("Missing basic registration fields. Please try again.", "danger")
            return redirect(url_for("signup"))

        # 3️⃣ Check if email already exists
        table_name = "user_profiles" if role == "user" else "designers"
        try:
            existing = supabase.table(table_name).select("id").eq("email", email).execute()
            if existing.data:
                flash("Email already registered!", "danger")
                return redirect(url_for("signup"))
        except Exception as e:
            print(f"Database error during email check: {e}")
            flash("A database error occurred. Please try again.", "danger")
            return redirect(url_for("signup"))

        # -------- HOMEOWNER (USER) LOGIC --------
        if role == "user":
            # Extract homeowner-specific fields
            location = request.form.get("location")
            property_type = request.form.get("property_type")
            rooms = request.form.get("rooms")
            budget = request.form.get("budget")
            timeline = request.form.get("timeline")
            project_rooms = request.form.getlist("project_rooms")     # checkbox array
            preferences = request.form.getlist("preferences")       # checkbox array

            # Validate required fields
            if not all([location, property_type, rooms, budget, timeline]):
                flash("Please fill in all required fields.", "danger")
                return redirect(url_for("signup"))

            # Insert into Supabase
            try:
                supabase.table("user_profiles").insert({
                    "user_name": name,
                    "email": email,
                    "password": password_hash,
                    "location": location,
                    "property_type": property_type,
                    "rooms": rooms,
                    "budget": budget,
                    "timeline": timeline,
                    "project_rooms": project_rooms,
                    "preferences": preferences
                }).execute()

                flash("Signup successful! Now you can select your preferences.", "success")
                # Optionally redirect to a preferences page with email in query params
                return redirect(url_for("preferences", email=email))

            except Exception as e:
                print(f"Supabase insert error: {e}")
                flash("Database insertion failed. Please try again.", "danger")
                return redirect(url_for("signup"))

        # -------- DESIGNER LOGIC --------
        elif role == "designer":
            # Step 1 Fields
            specialisation = request.form.get("specialisation")
            phone = request.form.get("phone")
            location = request.form.get("location")
            years_experience_str = request.form.get("years_experience")
            cities_served_str = request.form.get("cities_served", "")

            # Safe integer conversion
            years_experience = int(years_experience_str) if years_experience_str else None

            # Step 2 Fields (arrays)
            design_styles = request.form.getlist("design_styles")
            room_specializations = request.form.getlist("room_types")

            # Step 3 Fields
            budget_min_str = request.form.get("budget_min")
            budget_max_str = request.form.get("budget_max")
            project_duration = request.form.get("project_duration")
            budget_range_min = int(budget_min_str) if budget_min_str else None
            budget_range_max = int(budget_max_str) if budget_max_str else None
            project_size_str = request.form.get("project_size")
            project_rooms_str = request.form.get("project_rooms")
            typical_project_size_sqft = int(project_size_str) if project_size_str else None
            typical_project_rooms = int(project_rooms_str) if project_rooms_str else None

            # Step 4 Fields
            preferred_communication = request.form.getlist("communication")
            max_projects_str = request.form.get("max_projects")
            max_simultaneous_projects = int(max_projects_str) if max_projects_str else None

            # Validate required fields
            required_fields = {
                "Phone Number": phone,
                "Location": location,
                "Years of Experience": years_experience,
                "Primary Specialisation": specialisation,
                "Average Project Duration": project_duration,
                "Max Simultaneous Projects": max_simultaneous_projects
            }
            required_arrays = {
                "Design Styles": design_styles,
                "Room Specializations": room_specializations,
                "Preferred Communication": preferred_communication
            }

            for name_field, value in required_fields.items():
                if value is None:
                    flash(f"Missing required designer field: {name_field}", "danger")
                    return redirect(url_for("signup"))

            for name_field, value in required_arrays.items():
                if not value:
                    flash(f"Missing required designer selection: {name_field}", "danger")
                    return redirect(url_for("signup"))

            # Construct designer payload
            designer_payload = {
                "designer_name": name,
                "email": email,
                "password": password_hash,
                "specialisation": specialisation,
                "phone": phone,
                "location": location,
                "cities_served": [city.strip() for city in cities_served_str.split(',') if city.strip()],
                "years_experience": years_experience,
                "studio_name": request.form.get("studio_name"),
                "certifications": request.form.get("certifications"),
                "awards": request.form.get("awards"),
                "design_styles": design_styles,
                "room_specializations": room_specializations,
                "material_preferences": request.form.getlist("materials") or None,
                "color_palette_preferences": request.form.getlist("color_palettes") or None,
                "budget_range_min": budget_range_min,
                "budget_range_max": budget_range_max,
                "average_project_duration": project_duration,
                "typical_project_size_sqft": typical_project_size_sqft,
                "typical_project_rooms": typical_project_rooms,
                "extra_services": request.form.getlist("extra_services") or None,
                "preferred_communication": preferred_communication,
                "max_simultaneous_projects": max_simultaneous_projects,
                "availability_schedule": request.form.get("availability"),
                "portfolio_url": request.form.get("portfolio_url"),
                "bio": request.form.get("bio")
            }

            # Insert into Supabase
            try:
                insert_response = supabase.table("designers").insert(designer_payload).execute()
                if insert_response.data:
                    designer = insert_response.data[0]
                    session["user"] = {"id": designer["id"], "role": "designer",
                                       "name": designer["designer_name"], "email": designer["email"]}
                    flash(f"Registration complete! Welcome, {designer['designer_name']}!", "success")
                    return redirect(url_for("dashboard"))
                else:
                    flash("Could not create designer profile. Please try again.", "danger")
                    return redirect(url_for("signup"))
            except Exception as e:
                print(f"Supabase insert error: {e}")
                flash(f"Database insertion failed. Error: {e}", "danger")
                return redirect(url_for("signup"))

        else:
            flash("Invalid user role submitted.", "danger")
            return redirect(url_for("signup"))

    # GET request
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
            # Added email to session for consistency
            session["user"] = {"id": user["id"], "role": "user", "name": user["user_name"], "email": user["email"]}
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
            # Added email to session for consistency
            session["user"] = {"id": designer["id"], "role": "designer", "name": designer["designer_name"], "email": designer["email"]}
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials.", "danger")

    return render_template("login_designer.html")

# -----------------------PREFERENCES-------------
@app.route("/preferences", methods=["GET", "POST"])
def preferences():
    # --- AUTO-LOGIN LOGIC START (Runs on GET request when redirected from signup) ---
    email = request.args.get("email")
    password_hash = request.args.get("password_hash")
    
    # If session is NOT set AND we have credentials, attempt login
    if "user" not in session and email and password_hash:
        user_res = supabase.table("user_profiles").select("id, user_name, email").eq("email", email).eq("password", password_hash).execute()
        if user_res.data:
            user = user_res.data[0]
            # Set session for continuous login
            session["user"] = {"id": user["id"], "role": "user", "name": user["user_name"], "email": user["email"]} 
            # Clear sensitive data from URL and refresh to continue preferences while logged in
            return redirect(url_for("preferences")) 
        else:
            flash("Error during automatic login. Please log in manually.", "danger")
            return redirect(url_for("login_user"))

    # If the user is not logged in now, they must log in manually to proceed
    if "user" not in session:
        flash("Please log in to set your preferences.", "info")
        return redirect(url_for("login_user"))

    # --- AUTO-LOGIN LOGIC END ---

    if request.method == "POST":
        # Ensure user is logged in
        if "user" not in session or session["user"]["role"] != "user":
            flash("Session expired. Please log in.", "danger")
            return redirect(url_for("login_user"))

        # Use email from session for robust tracking
        user_email = session["user"]["email"]
        preferences_list = request.form.getlist("preferences")
        
        # Insert or Update preferences (Upsert logic for robustness)
        try:
            # Check if preferences already exist for this email
            existing_prefs = supabase.table("user_preferences").select("id").eq("email", user_email).execute().data

            if existing_prefs:
                # If exists, update the existing record
                supabase.table("user_preferences").update({"preferences": preferences_list}).eq("email", user_email).execute()
            else:
                # If not exist, insert a new record
                supabase.table("user_preferences").insert({
                    "email": user_email,
                    "preferences": preferences_list
                }).execute()

            flash("Preferences saved! Welcome to your dashboard.", "success")
            return redirect(url_for("dashboard"))
        
        except Exception as e:
            print(f"Database error during preference save: {e}")
            flash("A database error occurred while saving preferences.", "danger")
            return redirect(url_for("preferences"))


    # GET request logic
    # Fetch existing preferences to pre-fill the form if they exist
    existing_preferences = []
    if "user" in session:
        try:
            user_email = session["user"]["email"]
            # Use single() for expected unique rows or select all and take the first one
            res = supabase.table("user_preferences").select("preferences").eq("email", user_email).limit(1).execute()
            # Safely extract data
            existing_preferences = res.data[0].get("preferences", []) if res.data else []
        except:
            # Handle case where the record isn't found
            existing_preferences = []
            
    # List of available preferences for rendering the form
    available_preferences = [
        "Modern", "Minimalist", "Bohemian", "Industrial", "Rustic", "Traditional", 
        "Coastal", "Mid-Century Modern", "Scandinavian", "Farmhouse"
    ]
    
    return render_template("preferences.html", 
                           email=session["user"]["email"],
                           available_preferences=available_preferences,
                           existing_preferences=existing_preferences)


# ----------- DASHBOARD (Role-based) -----------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        flash("You must be logged in to view the dashboard.", "warning")
        return redirect(url_for("index"))

    user = session["user"]

    if user["role"] == "user":
        # Fetch user-specific data, like preferences or projects
        user_preferences = []
        try:
            # Assuming 'email' is guaranteed in session after successful login/auto-login
            res = supabase.table("user_preferences").select("preferences").eq("email", user["email"]).limit(1).execute()
            user_preferences = res.data[0].get("preferences", []) if res.data else []
        except:
            user_preferences = ["No preferences set yet."]

        return render_template("dashboard_user.html", user=user, preferences=user_preferences)
        
    elif user["role"] == "designer":
        # Fetch designer-specific data, like profile or active projects
        designer_profile = {}
        try:
            res = supabase.table("designers").select("*").eq("email", user["email"]).limit(1).execute()
            designer_profile = res.data[0] if res.data else {"bio": "Profile data not fully loaded."}
        except:
            designer_profile = {"bio": "Profile data not fully loaded or database error."}
            
        return render_template("dashboard_designer.html", user=user, profile=designer_profile)
        
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
