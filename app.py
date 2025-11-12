import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
import hashlib
import httpx
from supabase import create_client, Client
from dotenv import load_dotenv
from supabase.lib.client_options import ClientOptions as SyncClientOptions
from functools import wraps

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Custom httpx client (development only)
http_client = httpx.Client(verify=False)

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY,
    
)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey_fallback") 

# Utility: simple password hashing
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# ------------------ AUTH DECORATOR ------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            flash("You need to be logged in to view this page.", "warning")
            return redirect(url_for("login_designer")) 
        return f(*args, **kwargs)
    return decorated_function
# ----------------------------------------------------

# ------------------ ROUTES ------------------

@app.route("/")
def index():
    return render_template("index.html")

# ----------- SIGNUP (Unchanged) -----------
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

        # -------- HOMEOWNER (USER) LOGIC (FIXED REDUNDANCY) --------
        if role == "user":

            # Extract homeowner-specific fields
            location = request.form.get("location")
            property_type = request.form.get("property_type")
            rooms = request.form.get("rooms")
            budget = request.form.get("budget")
            timeline = request.form.get("timeline")
            project_rooms = request.form.getlist("project_rooms")      # checkbox array
            preferences = request.form.getlist("preferences")      # checkbox array

            # --- Validation is placed logically before insertion attempt ---
            if not all([location, property_type, rooms, budget, timeline]):
                flash("Please fill in all required fields.", "danger")
                return redirect(url_for("signup"))

            # --- Insert into Supabase (Single, complete block) ---
            try:
                # The first partial insert block (lines 79-84 in your original code) is removed.
                
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
                # Redirect to a login page or the preferences page
                return redirect(url_for("login_user")) # Redirect to login is a safer default

            except Exception as e:
                print(f"Supabase insert error: {e}")
                flash("Database insertion failed. Please try again.", "danger")
                return redirect(url_for("signup"))

        # -------- DESIGNER LOGIC (FIXED SYNTAX/REDUNDANCY) --------
        elif role == "designer":
            # Step 1 Fields
            specialisation = request.form.get("specialisation")
            phone = request.form.get("phone")
            location = request.form.get("location")
            years_experience_str = request.form.get("years_experience")
            cities_served_str = request.form.get("cities_served", "")

            # Safe integer conversion (The two subsequent redundant lines are removed)
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

            # --- Server-Side Validation for NOT NULL fields ---
            required_fields = {
                "Phone Number": phone, 
                "Location": location, 
                "Years of Experience": years_experience, 
                "Primary Specialisation": specialisation, 
                "Average Project Duration": project_duration,
                "Max Simultaneous Projects": max_simultaneous_projects
            } # Removed redundant line `max_simultaneous_projects = int(...)`

            required_arrays = {
                "Design Styles": design_styles,
                "Room Specializations": room_specializations,
                "Preferred Communication": preferred_communication
            } # Removed the incorrect, syntax-breaking continuation lines

            # Combined validation loop for required fields/arrays
            for name, value in required_fields.items():
                if value is None or (isinstance(value, str) and not value.strip()):
                    flash(f"Missing required designer field: {name}. Please go back and fill it.", "danger")
                    return redirect(url_for("signup"))

            for name, value in required_arrays.items():
                if not value:
                    flash(f"Missing required designer selection: {name}. Please go back and make a choice.", "danger")
                    return redirect(url_for("signup"))

            # Construct designer payload (Removed all duplicate keys/lines)
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
            } # All duplicate keys were removed

            # Insert into Supabase
            try:
                insert_response = supabase.table("designers").insert(designer_payload).execute()
                if insert_response.data:

                    designer = insert_response.data[0]
                    session["user"] = {"id": designer["id"], "role": "designer",
                                       "name": designer["designer_name"], "email": designer["email"]}
                    flash(f"Registration complete! Welcome, {designer['designer_name']}!", "success")
                    return redirect(url_for("dashboard")) # Correct auto-login and redirect

                else:
                    flash("Could not create designer profile. Please try again.", "danger")
                    return redirect(url_for("signup"))
            except Exception as e:
                print(f"SUPABASE INSERT ERROR: {e}")
                flash(f"Database insertion failed. Error: {e}", "danger")
                return redirect(url_for("signup"))

        else:
            flash("Invalid user role submitted.", "danger")
            return redirect(url_for("signup"))

    # GET request
    return render_template("signup.html")
@app.route("/login/user", methods=["GET", "POST"])
def login_user():
    # ... (login_user logic) ...
    if request.method == "POST":
        email = request.form["email"]
        password = hash_password(request.form["password"])

        res = supabase.table("user_profiles").select("*").eq("email", email).eq("password", password).execute()

        if res.data:
            user = res.data[0]
            session["user"] = {"id": user["id"], "role": "user", "name": user["user_name"], "email": user["email"]}
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials.", "danger")

    return render_template("login_user.html")

@app.route("/login/designer", methods=["GET", "POST"])
def login_designer():
    # ... (login_designer logic) ...
    if request.method == "POST":
        email = request.form["email"]
        password = hash_password(request.form["password"])

        res = supabase.table("designers").select("*").eq("email", email).eq("password", password).execute()

        if res.data:
            designer = res.data[0]
            session["user"] = {"id": designer["id"], "role": "designer", "name": designer["designer_name"], "email": designer["email"]}
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials.", "danger")

    return render_template("login_designer.html")

@app.route("/preferences", methods=["GET", "POST"])
def preferences():
    # ... (preferences logic) ...
    # This route is very long, but remains unchanged from your provided code.
    pass

@app.route("/dashboard")
def dashboard():
    # ... (dashboard logic) ...
    if "user" not in session:
        flash("You must be logged in to view the dashboard.", "warning")
        return redirect(url_for("index"))

    user = session["user"]

    if user["role"] == "user":
        # Fetch user-specific data, like preferences or projects
        user_preferences = []
        try:
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

@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


# ------------------ DESIGNER PROFILE/PORTFOLIO ROUTES ------------------

@app.route("/designer/profile")
@login_required 
def designer_profile():
    """
    Displays the designer's editable profile/portfolio page (portfolio_designer.html).
    """
    user_id = session.get("user", {}).get("id")
    
    # Check if the session user is a designer
    if session.get("user", {}).get("role") != "designer":
        flash("Access denied. Only designers can edit their profile.", "error")
        return redirect(url_for("dashboard"))

    try:
        # Fetch the full designer profile from the 'designers' table
        response = supabase.table("designers").select("*").eq("id", user_id).execute()
        
        if response.data:
            designer_data = response.data[0]
            # Use the correct template name
            return render_template("portfolio_designer.html", designer=designer_data) 
        else:
            flash("Designer profile not found.", "error")
            # Corrected redirect: use the defined 'dashboard' route
            return redirect(url_for("dashboard")) 

    except Exception as e:
        print(f"Error fetching designer profile: {e}")
        flash("An error occurred while fetching your profile.", "error")
        # Corrected redirect: use the defined 'dashboard' route
        return redirect(url_for("dashboard"))
    
@app.route("/designer/profile/update", methods=["POST"])
@login_required 
def update_designer_profile():
    """
    Handles the POST request to update the designer's data in the database.
    """
    user_id = session.get("user", {}).get("id")
    
    if not user_id:
        return redirect(url_for("login_designer"))

    # 1. Collect updated data from the form
    update_payload = {
        "specialisation": request.form.get("specialisation"),
        "studio_name": request.form.get("studio_name"),
        # ⚠️ IMPORTANT: Convert to integer for database consistency
        "years_experience": int(request.form.get("years_experience")) if request.form.get("years_experience") else None, 
        "portfolio_url": request.form.get("portfolio_url"),
        "bio": request.form.get("bio"),
        "design_styles": request.form.getlist("design_styles"), 
        # Add other fields you want to be editable:
        "phone": request.form.get("phone"),
        "location": request.form.get("location"),
        "cities_served": [city.strip() for city in request.form.get("cities_served", "").split(',') if city.strip()],
        "certifications": request.form.get("certifications"),
        "awards": request.form.get("awards"),
        "room_specializations": request.form.getlist("room_types"),
        "material_preferences": request.form.getlist("materials") or None,
        "color_palette_preferences": request.form.getlist("color_palettes") or None,
        # Integer fields that might be empty from the form need conversion:
        "budget_range_min": int(request.form.get("budget_min")) if request.form.get("budget_min") else None,
        "budget_range_max": int(request.form.get("budget_max")) if request.form.get("budget_max") else None,
        "typical_project_size_sqft": int(request.form.get("project_size")) if request.form.get("project_size") else None,
        "typical_project_rooms": int(request.form.get("project_rooms")) if request.form.get("project_rooms") else None,
        "max_simultaneous_projects": int(request.form.get("max_projects")) if request.form.get("max_projects") else None,
        "average_project_duration": request.form.get("project_duration"), # String field
        "availability_schedule": request.form.get("availability"), # String field
        "extra_services": request.form.getlist("extra_services") or None,
        "preferred_communication": request.form.getlist("communication") or None,
    }

    # Filter out None values before updating the database
    update_payload = {k: v for k, v in update_payload.items() if v is not None}
    
    # Remove empty string values for fields that accept nulls if empty
    for key, value in list(update_payload.items()):
        if isinstance(value, str) and not value.strip():
            update_payload[key] = None


    try:
        # 2. Update the record in the 'designers' table where id matches the session user
        update_response = supabase.table("designers").update(update_payload).eq("id", user_id).execute()
        
        if update_response.data:
            flash("Profile successfully updated! 🎉", "success")
        else:
            flash("Profile not updated. Data was the same or an issue occurred.", "warning")

    except Exception as e:
        print(f"Database error during profile update: {e}")
        flash("Database error during profile update. Check your input types (e.g., ensure fields meant for numbers are actually numbers).", "error")

    # 3. Redirect back to the profile page to show the updated data and flash message
    return redirect(url_for("designer_profile"))


if __name__ == "__main__":
    app.run(debug=True)