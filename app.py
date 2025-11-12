# ...existing code...
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
import hashlib
import httpx
from supabase import create_client, Client
from dotenv import load_dotenv
from supabase.lib.client_options import ClientOptions as SyncClientOptions 
from functools import wraps
from flask import Flask, render_template, session, redirect, url_for, flash
from datetime import datetime
import calendar
import uuid
from supabase import create_client, Client
from redesign_app import redesign_bp


load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Custom httpx client (development only)
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
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey_fallback")
app.register_blueprint(redesign_bp, url_prefix='/redesign') 

# Utility: simple password hashing
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# ------------------ AUTH DECORATOR ------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            flash("You need to be logged in to view this page.", "warning")
            # Redirect to the main index page if not logged in
            return redirect(url_for("index")) 
        return f(*args, **kwargs)
    return decorated_function
# ----------------------------------------------------

# ------------------ ROUTES ------------------

@app.route("/")
def index():
    return render_template("index.html")

# ----------- SIGNUP -----------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    # ... (This entire, long function remains UNCHANGED) ...
    if request.method == "POST":
        print("\n====== SIGNUP FORM DATA RECEIVED ======")
        print(dict(request.form))
        print("=======================================")

        # Step 1: Extract Basic Fields Safely
        role = request.form.get("role")
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        if not all([role, name, email, password]):
            flash("Missing basic registration details. Please try again.", "danger")
            print("Missing role/name/email/password in form data.")
            return redirect(url_for("signup"))

        password_hash = hash_password(password)

        # Step 2: Check for existing email
        table_name = "user_profiles" if role == "user" else "designers"
        try:
            existing = supabase.table(table_name).select("id").eq("email", email).execute()
            if existing.data:
                flash("Email already registered! Try logging in.", "danger")
                print(f"Email {email} already exists in {table_name}.")
                return redirect(url_for("signup"))
        except Exception as e:
            print(f"Database error during email check: {e}")
            flash("Database error during validation. Please try again.", "danger")
            return redirect(url_for("signup"))

        # Step 3: Insert based on role
        if role == "user":
            print("Processing Homeowner Signup...")

            # Extract homeowner data
            user_city = request.form.get("user_city")
            user_budget = request.form.get("user_budget")
            user_rooms = request.form.getlist("user_rooms")
            user_styles = request.form.getlist("user_styles")
            user_property_type = request.form.get("user_property_type")
            user_bhk = request.form.get("user_bhk")
            user_timeline = request.form.get("user_timeline")

            print(f"[DEBUG] role={role}, name={name}, email={email}")
            print(f"[DEBUG] user_city={user_city}, property_type={user_property_type}, user_rooms={user_rooms}, user_styles={user_styles}")# Validation checks
            required_fields = {
                "City": user_city,
                "Budget": user_budget,
                "Property Type": user_property_type,
                "BHK Configuration": user_bhk,
                "Timeline": user_timeline,
            }

            for field, value in required_fields.items():
                if not value or not value.strip():
                    flash(f"Missing required homeowner field: {field}.", "danger")
                    print(f"Missing homeowner field: {field}")
                    return redirect(url_for("signup"))

            if not user_rooms:
                flash("Please select at least one room to design.", "danger")
                print("Missing user_rooms.")
                return redirect(url_for("signup"))

            if not user_styles:
                flash("Please select at least one design style.", "danger")
                print("Missing user_styles.")
                return redirect(url_for("signup"))

            # Prepare payload
            user_payload = {
                "user_name": name,
                "email": email,
                "password": password_hash,
                "user_city": user_city,
                "user_budget": user_budget,
                "user_rooms": user_rooms,
                "user_styles": user_styles,
                "user_property_type": user_property_type,
                "user_bhk": user_bhk,
                "user_timeline": user_timeline,
                "is_complete": True,
            }

            try:
                insert_response = supabase.table("user_profiles").insert(user_payload).execute()
                print("SUPABASE INSERT RESPONSE:", insert_response)

                # Accept either `data` or success status 201
                if insert_response.data or getattr(insert_response, "status_code", None) == 201:
                    flash("Registration complete! Redirecting to login...", "success")
                    print("Homeowner inserted successfully.")
                    return redirect(url_for("login_user"))
                else:
                    flash("Registration succeeded but response was empty. Please verify in database.", "warning")
                    print("Insert returned empty data but likely succeeded.")
                    return redirect(url_for("login_user"))
            except Exception as e:
                print(f"SUPABASE INSERT ERROR (Homeowner): {e}")
                flash("Database error during homeowner registration. Please try again.", "danger")
                return redirect(url_for("signup"))

        elif role == 'designer':
            # --- DESIGNER LOGIC: COLLECT ALL DATA, VALIDATE, & INSERT ---
            # ... (All your designer signup logic remains unchanged) ...
            
            # Step 1 Fields
            specialisation = request.form.get("specialisation")
            phone = request.form.get("phone")
            location = request.form.get("location")
            years_experience_str = request.form.get("years_experience")
            cities_served_str = request.form.get("cities_served", "")
            years_experience = int(years_experience_str) if years_experience_str else None

            # Step 2 Fields (Arrays)
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
                "Phone Number": phone, "Location": location, "Years of Experience": years_experience, 
                "Primary Specialisation": specialisation, "Average Project Duration": project_duration,
                "Max Simultaneous Projects": max_simultaneous_projects,
            }

            required_arrays = {
                "Design Styles (Step 2)": design_styles, "Room Specializations (Step 2)": room_specializations,
                "Preferred Communication (Step 4)": preferred_communication,
            }
            
            for name, value in required_fields.items():
                if value is None or (isinstance(value, str) and not value.strip()):
                    flash(f"Missing required designer field: {name}. Please go back and fill it.", "danger")
                    return redirect(url_for("signup"))

            for name, value in required_arrays.items():
                if not value:
                    flash(f"Missing required designer selection: {name}. Please go back and make a choice.", "danger")
                    return redirect(url_for("signup"))
            
            # --- CONSTRUCT PAYLOAD ---
            designer_payload = {
                "designer_name": name, "email": email, "password": password_hash,
                "specialisation": specialisation, "phone": phone, "location": location,
                "cities_served": [city.strip() for city in cities_served_str.split(',') if city.strip()], 
                "years_experience": years_experience, "studio_name": request.form.get("studio_name"),
                "certifications": request.form.get("certifications"), "awards": request.form.get("awards"),
                "design_styles": design_styles, "room_specializations": room_specializations,
                "material_preferences": request.form.getlist("materials") or None,
                "color_palette_preferences": request.form.getlist("color_palettes") or None,
                "budget_range_min": budget_range_min, "budget_range_max": budget_range_max,
                "average_project_duration": project_duration,
                "typical_project_size_sqft": typical_project_size_sqft,
                "typical_project_rooms": typical_project_rooms,
                "extra_services": request.form.getlist("extra_services") or None,
                "preferred_communication": preferred_communication,
                "max_simultaneous_projects": max_simultaneous_projects,
                "availability_schedule": request.form.get("availability"),
                "portfolio_url": request.form.get("portfolio_url"), "bio": request.form.get("bio"),
            }
            
            # --- EXECUTE FINAL INSERT & AUTOMATIC LOGIN ---
            try:
                insert_response = supabase.table("designers").insert(designer_payload).execute()
                
                if insert_response.data:
                    designer_name= insert_response.data[0]["designer_name"]
                    flash(f"Registration complete! Welcome, {designer_name}", "success")
                    return redirect(url_for("login_designer")) 
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

    return render_template("signup.html")

# ----------- LOGIN -----------

# --- THIS IS THE USER (HOMEOWNER) LOGIN ---
@app.route("/login/user", methods=["GET", "POST"])
def login_user():
    if request.method == "POST":
        email = request.form["email"]
        password = hash_password(request.form["password"])

        res = supabase.table("user_profiles").select("*").eq("email", email).eq("password", password).execute()

        if res.data:
            user = res.data[0]
            session["user"] = {"id": user["id"], "role": "user", "name": user["user_name"], "email": user["email"]}
            
            # --- MODIFICATION ---
            # Redirect to the NEW /user_dashboard route
            return redirect(url_for("user_dashboard"))
            # --- END MODIFICATION ---

        else:
            flash("Invalid credentials.", "danger")

    return render_template("login_user.html")

# --- THIS IS THE DESIGNER LOGIN ---
@app.route("/login/designer", methods=["GET", "POST"])
def login_designer():
    if request.method == "POST":
        email = request.form["email"]
        password = hash_password(request.form["password"])

        res = supabase.table("designers").select("*").eq("email", email).eq("password", password).execute()

        if res.data:
            designer = res.data[0]
            session["user"] = {"id": designer["id"], "role": "designer", "name": designer["designer_name"], "email": designer["email"]}
            
            # This is correct. /dashboard is for designers.
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials.", "danger")

    return render_template("login_designer.html")

# ... (preferences route remains UNCHANGED) ...
@app.route("/preferences", methods=["GET", "POST"])
def preferences():
    # ... (preferences logic) ...
    pass

@app.template_filter('datetimeformat')
def datetimeformat(value):
    """Convert ISO or timestamp into human-readable date"""
    try:
        return datetime.fromisoformat(value).strftime("%b %d, %Y")
    except Exception:
        return value or "N/A"


# --- MODIFIED: THIS IS NOW THE DESIGNER-ONLY DASHBOARD ---
@app.route("/dashboard")
@login_required
def dashboard():
    
    user = session["user"]
    
    # Security Check: If a 'user' lands here, send them to their correct dashboard.
    if user["role"] != "designer":
        flash("Access denied. Redirecting to your dashboard.", "warning")
        return redirect(url_for("user_dashboard"))

    # --- From here, it's ONLY designer logic ---
    email = user["email"].strip().lower()
    role = user["role"]

    try:
        print("\n===== DASHBOARD DEBUG INFO (DESIGNER) =====")
        print(f"Logged-in designer email: {email}")
        print("====================================")

        # Fetch designer record
        designer_res = (
            supabase.table("designers")
            .select("*")
            .filter("email", "eq", email)
            .limit(1)
            .execute()
        )
        designer = designer_res.data[0] if designer_res.data else None
        if not designer:
            flash("Designer not found.", "danger")
            print(f"No designer found for: {email}")
            return redirect(url_for("index"))

        print(f"Designer found: {designer.get('designer_name', 'Unknown')}")

        # ---------- PORTFOLIO ----------
        portfolio_res = (
            supabase.table("designer_portfolio")
            .select("*")
            .filter("designer_email", "eq", email)
            .execute()
        )
        portfolio = portfolio_res.data or []
        print(f"Portfolio fetched: {len(portfolio)} items")

        # ---------- REVIEWS ----------
        review_res = (
            supabase.table("designer_reviews")
            .select("*")
            .filter("designer_email", "eq", email)
            .execute()
        )
        reviews = review_res.data or []
        avg_rating = round(sum([r["rating"] for r in reviews]) / len(reviews), 1) if reviews else 0
        total_reviews = len(reviews)
        print(f"Reviews fetched: {total_reviews} (Avg Rating: {avg_rating})")

        # ---------- BOOKINGS ----------
        booking_res = (
            supabase.table("designer_bookings")
            .select("*")
            .filter("designer_email", "eq", email)
            .execute()
        )
        bookings = booking_res.data or []
        print(f"Bookings fetched: {len(bookings)}")

        # ---------- CALCULATIONS ----------
        total_projects = len(portfolio)
        now = datetime.now()
        current_month = calendar.month_abbr[now.month]

        monthly_bookings = len([
            b for b in bookings
            if b.get("created_at") and b["created_at"][:7] == now.strftime("%Y-%m")
        ])

        # ---------- EARNINGS ----------
        total_earnings = 0
        pending_earnings = 0
        for b in bookings:
            notes = b.get("notes", "")
            digits = "".join([c for c in notes if c.isdigit()])
            amount = int(digits) if digits else 0

            status = b.get("booking_status", "").lower()
            if status in ["confirmed", "completed"]:
                total_earnings += amount
            elif status == "pending":
                pending_earnings += amount

        print(f"Total Earnings: ₹{total_earnings:,} | Pending: ₹{pending_earnings:,}")

        # ---------- UPCOMING SCHEDULE ----------
        upcoming_schedule = sorted(
            [b for b in bookings if b.get("booking_date")],
            key=lambda x: x["booking_date"]
        )[:3]
        print(f"Upcoming Meetings: {len(upcoming_schedule)}")

        # ---------- POPULAR STYLES ----------
        style_count = {}
        for p in portfolio:
            style = p.get("design_style")
            if style:
                style_count[style] = style_count.get(style, 0) + 1

        total_styles = sum(style_count.values())
        popular_styles = [
            {"style": s, "percent": round((c / total_styles) * 100, 1)}
            for s, c in sorted(style_count.items(), key=lambda x: x[1], reverse=True)
        ] if total_styles else []
        print(f"Popular Styles Found: {len(popular_styles)}")

        # ---------- RENDER DESIGNER DASHBOARD ----------
        return render_template(
            "dashboard_designer.html",
            user=user,
            designer=designer,
            portfolio=portfolio,
            avg_rating=avg_rating,
            total_reviews=total_reviews,
            total_projects=total_projects,
            monthly_bookings=monthly_bookings,
            upcoming_schedule=upcoming_schedule,
            total_earnings=total_earnings,
            pending_earnings=pending_earnings,
            popular_styles=popular_styles,
            current_month=current_month,
        )

    except Exception as e:
        print("DASHBOARD ERROR TRACEBACK:", e)
        flash("Error loading dashboard data.", "danger")
        return redirect(url_for("index"))


# --- *** NEW ROUTE *** ---
# --- THIS IS THE USER (HOMEOWNER) DASHBOARD ---
@app.route("/user_dashboard")
@login_required
def user_dashboard():
    
    user = session["user"]

    # Security Check: If a 'designer' lands here, send them to their correct dashboard.
    if user["role"] != "user":
        flash("Access denied. Redirecting to your dashboard.", "warning")
        return redirect(url_for("dashboard"))
    
    # --- From here, it's ONLY homeowner logic ---
    email = user["email"].strip().lower()

    try:
        print("\n===== DASHBOARD DEBUG INFO (HOMEOWNER) =====")
        print(f"Logged-in user email: {email}")
        print("======================================")

        # Fetch homeowner record
        user_res = (
            supabase.table("user_profiles")
            .select("*")
            .filter("email", "eq", email)
            .limit(1)
            .execute()
        )
        homeowner = user_res.data[0] if user_res.data else None
        if not homeowner:
            flash("Homeowner profile not found.", "danger")
            print(f"No user_profile found for: {email}")
            return redirect(url_for("index"))

        print(f"Homeowner found: {homeowner.get('user_name', 'Unknown')}")

        # --- Placeholder Data (based on your images) ---
        # In a real app, you'd fetch this from Supabase, e.g.:
        # recent_uploads_res = supabase.table("user_projects").select("*").eq("user_id", homeowner['id']).limit(3).execute()
        # recent_uploads = recent_uploads_res.data or []
        recent_uploads = [
            {"name": "Living Room", "img_url": "https://placehold.co/150x150/eeeeee/cccccc?text=Living+Room"},
            {"name": "Bedroom", "img_url": "https://placehold.co/150x150/eeeeee/cccccc?text=Bedroom"},
            {"name": "Kitchen", "img_url": "https://placehold.co/150x150/eeeeee/cccccc?text=Kitchen"},
        ]

        # Example: Fetch AI results
        ai_results = [
            {"style": "Modern Minimalist", "match": "92%", "before_img": "https://placehold.co/300x200/ccc/fff?text=Before", "after_img": "https://placehold.co/300x200/888/fff?text=After"},
            {"style": "Cozy Scandinavian", "match": "88%", "before_img": "https://placehold.co/300x200/ccc/fff?text=Before", "after_img": "https://placehold.co/300x200/888/fff?text=After"},
            {"style": "Industrial Chic", "match": "85%", "before_img": "https://placehold.co/300x200/ccc/fff?text=Before", "after_img": "https://placehold.co/300x200/888/fff?text=After"},
        ]

        # Example: Fetch smart predictions
        smart_predictions = {
            "budget": "₹25K - ₹45K",
            "timeline": "3-5 weeks",
            "style_match": "92%",
            "trending": "Modern Minimalist"
        }

        # Example: Fetch recommended designers
        # designers_res = supabase.table("designers").select("*").limit(3).execute()
        # recommended_designers = designers_res.data or []
        recommended_designers = [
            {"initials": "PS", "name": "Priya Sharma", "style": "Modern & Contemporary", "rating": 4.9, "reviews": 127, "location": "Mumbai", "budget": "₹15K - ₹50K"},
            {"initials": "AP", "name": "Arjun Patel", "style": "Scandinavian & Minimalist", "rating": 4.8, "reviews": 89, "location": "Bangalore", "budget": "₹20K - ₹60K"},
            {"initials": "KR", "name": "Kavya Reddy", "style": "Traditional & Fusion", "rating": 4.9, "reviews": 156, "location": "Hyderabad", "budget": "₹18K - ₹45K", "available": True},
        ]

        # ---------- RENDER HOMEOWNER DASHBOARD ----------
        return render_template(
            "dashboard_homeowner.html",
            user=user,
            homeowner=homeowner,
            recent_uploads=recent_uploads,
            ai_results=ai_results,
            smart_predictions=smart_predictions,
            recommended_designers=recommended_designers
        )

    except Exception as e:
        print("HOMEOWNER DASHBOARD ERROR TRACEBACK:", e)
        flash(f"Error loading homeowner dashboard data: {e}", "danger")
        return redirect(url_for("index"))
# --- END NEW ROUTE ---


@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


# ------------------ DESIGNER PROFILE/PORTFOLIO ROUTES ------------------

@app.route("/designer/profile")
@login_required 
def designer_profile():
    # ... (This function remains UNCHANGED) ...
    user_id = session.get("user", {}).get("id")
    
    # Check if the session user is a designer
    if session.get("user", {}).get("role") != "designer":
        flash("Access denied. Only designers can edit their profile.", "error")
        # Send them to their correct dashboard
        return redirect(url_for("user_dashboard"))

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
    # ... (This function remains UNCHANGED) ...
    user_id = session.get("user", {}).get("id")
    
    if not user_id or session.get("user", {}).get("role") != "designer":
        flash("Access denied.", "error")
        return redirect(url_for("login_designer"))

    # 1. Collect updated data from the form
    update_payload = {
        "specialisation": request.form.get("specialisation"),
        "studio_name": request.form.get("studio_name"),
        "years_experience": int(request.form.get("years_experience")) if request.form.get("years_experience") else None, 
        "portfolio_url": request.form.get("portfolio_url"),
        "bio": request.form.get("bio"),
        "design_styles": request.form.getlist("design_styles"), 
        "phone": request.form.get("phone"),
        "location": request.form.get("location"),
        "cities_served": [city.strip() for city in request.form.get("cities_served", "").split(',') if city.strip()],
        "certifications": request.form.get("certifications"),
        "awards": request.form.get("awards"),
        "room_specializations": request.form.getlist("room_types"),
        "material_preferences": request.form.getlist("materials") or None,
        "color_palette_ preferences": request.form.getlist("color_palettes") or None,
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
            flash("Profile successfully updated!", "success")
        else:
            flash("Profile not updated. Data was the same or an issue occurred.", "warning")

    except Exception as e:
        print(f"Database error during profile update: {e}")
        flash("Database error during profile update. Check your input types (e.numeric fields).", "error")

    # 3. Redirect back to the profile page to show the updated data and flash message
    return redirect(url_for("designer_profile"))


if __name__ == "__main__":
    app.run(debug=True)
