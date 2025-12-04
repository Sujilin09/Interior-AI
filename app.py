# ...existing code...
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
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
from collections import Counter


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
    
    if user["role"] != "designer":
        flash("Access denied. Redirecting to your dashboard.", "warning")
        return redirect(url_for("user_dashboard"))

    designer_id = user["id"]

    try:
        # 1. Fetch Designer Data
        designer_res = supabase.table("designers").select("*").eq("id", designer_id).limit(1).execute()
        if not designer_res.data:
            return redirect(url_for("index"))
        designer = designer_res.data[0]

        # 2. Fetch Supporting Data
        portfolio_res = supabase.table("designer_portfolio").select("*").eq("designer_id", designer_id).execute()
        portfolio = portfolio_res.data or []
        
        review_res = supabase.table("designer_reviews").select("*").eq("designer_id", designer_id).execute()
        reviews = review_res.data or []
        avg_rating = round(sum([r["rating"] for r in reviews]) / len(reviews), 1) if reviews else 0
        total_reviews = len(reviews)

        booking_res = supabase.table("designer_bookings").select("*").eq("designer_id", designer_id).order("booking_date", desc=True).execute()
        bookings = booking_res.data or []

        # 3. Standard Dashboard Calculations
        total_projects = len(portfolio)
        now = datetime.now()
        current_month = calendar.month_abbr[now.month]
        monthly_bookings = len([b for b in bookings if b.get("created_at") and b["created_at"][:7] == now.strftime("%Y-%m")])

        total_earnings = 0
        pending_earnings = 0
        for b in bookings:
            amount = 0 # Logic placeholder
            status = b.get("booking_status", "").lower()
            if status in ["confirmed", "completed"]:
                total_earnings += amount
            elif status == "pending":
                pending_earnings += amount

        upcoming_schedule = sorted(
            [b for b in bookings if b.get("booking_status") in ["pending", "confirmed"]],
            key=lambda x: x["booking_date"]
        )[:10]

        style_count = {}
        for p in portfolio:
            style = p.get("design_style")
            if style: style_count[style] = style_count.get(style, 0) + 1
        total_styles = sum(style_count.values())
        popular_styles = [{"style": s, "percent": round((c / total_styles) * 100, 1)} for s, c in sorted(style_count.items(), key=lambda x: x[1], reverse=True)] if total_styles else []


        # --- 4. AI RECOMMENDATION ENGINE (New Feature) ---
        
        # A. Get all users (Potential Leads)
        # In a real app, you might limit this to users created in the last 30 days
        users_res = supabase.table("user_profiles").select("*").limit(100).execute()
        all_users = users_res.data or []

        # B. Define Designer's "Cluster" (Location & Style)
        my_cities = set(designer.get('cities_served', []) or [])
        if designer.get('location'):
            my_cities.add(designer['location'])
            
        my_styles = set(designer.get('design_styles', []) or [])

        recommended_leads = []
        
        # C. Scoring Algorithm
        for u in all_users:
            score = 0
            
            # Location Match (High Priority: 50 pts)
            u_city = u.get('user_city')
            if u_city and u_city in my_cities:
                score += 50
            
            # Style Match (Medium Priority: 15 pts per match)
            u_styles = set(u.get('user_styles', []) or [])
            style_overlap = my_styles.intersection(u_styles)
            score += (len(style_overlap) * 15)
            
            # Budget Presence (Bonus: 10 pts if they have a budget set)
            if u.get('user_budget'):
                score += 10

            # Threshold: Only recommend if there is some connection
            if score > 0:
                display_score = min(score, 100) # Cap at 100%
                recommended_leads.append({
                    "id": u['id'],
                    "name": u['user_name'],
                    "location": u_city or "Unknown",
                    "styles": list(style_overlap)[:3], # Top 3 matching styles
                    "budget": u.get('user_budget', 'N/A'),
                    "property": u.get('user_property_type', 'Property'),
                    "match_score": display_score
                })

        # D. Sort by highest match and take top 4
        recommended_leads.sort(key=lambda x: x['match_score'], reverse=True)
        recommended_leads = recommended_leads[:6]


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
            recommended_leads=recommended_leads # <-- PASSING NEW DATA
        )

    except Exception as e:
        print("DASHBOARD ERROR TRACEBACK:", e)
        flash("Error loading dashboard data.", "danger")
        return redirect(url_for("index"))

@app.route("/designer/add_project", methods=["GET", "POST"])
@login_required
def add_project():
    user = session["user"]
    user_id = user["id"]
    
    if user.get("role") != "designer":
        return redirect(url_for("user_dashboard"))

    if request.method == "POST":
        try:
            # 2. Get Form Data (File Upload)
            if 'image_file' not in request.files:
                flash("No file uploaded.", "warning")
                return redirect(request.url)
            
            file = request.files['image_file']
            if file.filename == '':
                flash("No file selected.", "warning")
                return redirect(request.url)

            if file:
                # 3. Upload to Supabase
                file_ext = os.path.splitext(file.filename)[1]
                unique_filename = f"{user_id}/{uuid.uuid4()}{file_ext}"
                bucket_name = "portfolio-images"
                
                file_content = file.read()
                content_type = file.content_type
                
                supabase.storage.from_(bucket_name).upload(
                    path=unique_filename,
                    file=file_content,
                    file_options={"content-type": content_type}
                )
                
                image_url = supabase.storage.from_(bucket_name).get_public_url(unique_filename)

                # 4. Save to Database
                new_project = {
                    "designer_id": user_id,
                    "designer_email": user["email"],
                    "project_title": request.form.get("project_title"),
                    "room_type": request.form.get("room_type"),
                    "design_style": request.form.get("design_style"),
                    "project_description": request.form.get("description"),
                    "image_url": image_url,
                    "uploaded_at": datetime.now().isoformat()
                }

                supabase.table("designer_portfolio").insert(new_project).execute()
                
                flash("Project added successfully!", "success")
            return redirect(url_for("designer_profile"))

        except Exception as e:
            print(f"Error adding project: {e}")
            flash("An error occurred while saving your project.", "danger")

    # THIS IS THE FIX: Pass dummy/default values for the sidebar variables
    return render_template(
        "add_project.html", 
        user=user,
        total_earnings=0,          # Prevents the crash
        pending_earnings=0,        # Prevents the crash
        upcoming_schedule=[],      # Prevents the crash
        popular_styles=[],         # Prevents the crash
        current_month=""
    )

    
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
    user = session["user"]
    user_id = user.get("id")
    
    # 1. Security Check
    if user.get("role") != "designer":
        flash("Access denied.", "error")
        return redirect(url_for("user_dashboard"))

    try:
        # 2. Fetch Designer Profile
        response = supabase.table("designers").select("*").eq("id", user_id).execute()
        if not response.data:
            flash("Designer profile not found.", "error")
            return redirect(url_for("dashboard")) 
        designer_data = response.data[0]

        # 3. Fetch Bookings
        booking_res = supabase.table("designer_bookings") \
            .select("*") \
            .eq("designer_id", user_id) \
            .order("booking_date", desc=True) \
            .execute()
        bookings = booking_res.data or []

        # 4. Fetch Portfolio
        portfolio_res = supabase.table("designer_portfolio").select("*").eq("designer_id", user_id).execute()
        portfolio = portfolio_res.data or []

        # 5. Calculate Earnings
        total_earnings = 0
        pending_earnings = 0
        for b in bookings:
            amount = 0 
            status = b.get("booking_status", "").lower()
            if status in ["confirmed", "completed"]:
                total_earnings += amount
            elif status == "pending":
                pending_earnings += amount

        # 6. Filter "Client Requests" (Same logic as Dashboard)
        upcoming_schedule = sorted(
            [b for b in bookings if b.get("booking_status") in ["pending", "confirmed"]],
            key=lambda x: x["booking_date"]
        )[:10] # <--- CHANGED FROM 3 TO 10

        # 7. Calculate Popular Styles
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
        
        now = datetime.now()
        current_month = calendar.month_abbr[now.month]

        # 8. Render Template
        return render_template(
            "portfolio_designer.html", 
            designer=designer_data, 
            user=user,
            upcoming_schedule=upcoming_schedule,
            total_earnings=total_earnings,
            pending_earnings=pending_earnings,
            popular_styles=popular_styles,
            current_month=current_month,
            total_projects=len(portfolio)
        )

    except Exception as e:
        print(f"Error fetching designer profile: {e}")
        flash("An error occurred while fetching your profile.", "error")
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
from collections import Counter, defaultdict

@app.route("/designer/analytics")
@login_required
def designer_analytics():
    user = session["user"]
    user_id = user["id"]
    
    if user.get("role") != "designer":
        return redirect(url_for("user_dashboard"))

    try:
        # ==========================================
        # PART 1: SIDEBAR DATA (Keep this! It prevents crashes)
        # ==========================================
        
        # Fetch Bookings & Portfolio for Sidebar
        booking_res = supabase.table("designer_bookings").select("*").eq("designer_id", user_id).order("booking_date", desc=True).execute()
        bookings = booking_res.data or []
        
        portfolio_res = supabase.table("designer_portfolio").select("design_style").eq("designer_id", user_id).execute()
        portfolio_items = portfolio_res.data or []

        # Sidebar Calcs
        total_earnings = 0
        pending_earnings = 0
        for b in bookings:
            amount = 0 
            status = b.get("booking_status", "").lower()
            if status in ["confirmed", "completed"]:
                total_earnings += amount
            elif status == "pending":
                pending_earnings += amount

        upcoming_schedule = sorted([b for b in bookings if b.get("booking_status") in ["pending", "confirmed"]], key=lambda x: x["booking_date"])[:10]

        from collections import Counter
        import itertools # Needed to flatten list of lists
        
        style_list = [p.get("design_style") for p in portfolio_items if p.get("design_style")]
        sidebar_style_count = Counter(style_list)
        popular_styles = [{"style": s, "percent": round((c / sum(sidebar_style_count.values())) * 100, 1)} for s, c in sorted(sidebar_style_count.items(), key=lambda x: x[1], reverse=True)] if style_list else []
        
        now = datetime.now()
        current_month = calendar.month_abbr[now.month]


        # ==========================================
        # PART 2: MARKET INTELLIGENCE (The New Insights)
        # ==========================================

        # 1. Fetch User Profiles (The Gold Mine)
        # We fetch profiles to analyze demographics
        users_res = supabase.table("user_profiles").select("user_city, user_budget, user_styles, user_property_type").execute()
        all_users = users_res.data or []

        # 2. Analyze User Locations (Cities)
        cities = [u['user_city'] for u in all_users if u.get('user_city')]
        city_counts = Counter(cities)
        top_cities = dict(city_counts.most_common(5)) # Top 5 cities

        # 3. Analyze User Budgets
        budgets = [u['user_budget'] for u in all_users if u.get('user_budget')]
        budget_counts = Counter(budgets)
        
        # 4. Analyze Property Types (Villa vs Apt)
        properties = [u['user_property_type'] for u in all_users if u.get('user_property_type')]
        property_counts = Counter(properties)

        # 5. Analyze Trending Styles (From User Preferences + Saved AI)
        # Combine explicit user choices with what they are generating
        user_pref_styles = []
        for u in all_users:
            if u.get('user_styles'):
                # user_styles is an array/list in DB
                user_pref_styles.extend(u['user_styles']) 
        
        # Also get recent AI saves
        ai_res = supabase.table("saved_ai_designs").select("style").limit(200).execute()
        ai_styles = [row['style'] for row in ai_res.data if row.get('style')]
        
        # Merge and Count
        total_market_styles = user_pref_styles + ai_styles
        market_style_counts = Counter(total_market_styles)
        top_market_styles = dict(market_style_counts.most_common(6))

        # 6. Metrics for KPI Cards
        total_users_platform = len(all_users)
        total_requests = len(bookings)
        confirmed_projects = len([b for b in bookings if b['booking_status'] == 'confirmed'])
        est_revenue = confirmed_projects * 25000 
        conversion_rate = round((confirmed_projects / total_requests * 100), 1) if total_requests else 0

        return render_template(
            "analytics.html",
            user=user,
            # Sidebar Data
            upcoming_schedule=upcoming_schedule,
            total_earnings=total_earnings,
            pending_earnings=pending_earnings,
            current_month=current_month,
            popular_styles=popular_styles,
            
            # New Market Data
            chart_data={
                "cities_labels": list(top_cities.keys()),
                "cities_values": list(top_cities.values()),
                "budget_labels": list(budget_counts.keys()),
                "budget_values": list(budget_counts.values()),
                "property_labels": list(property_counts.keys()),
                "property_values": list(property_counts.values()),
                "style_labels": list(top_market_styles.keys()),
                "style_values": list(top_market_styles.values())
            },
            kpi={
                "revenue": est_revenue,
                "bookings": total_requests,
                "conversion_rate": conversion_rate,
                "active_users": total_users_platform
            }
        )

    except Exception as e:
        print(f"Analytics Error: {e}")
        import traceback
        traceback.print_exc()
        flash("Could not load analytics.", "danger")
        return redirect(url_for("dashboard"))
    
@app.route("/browse_designers")
@login_required
def browse_designers():
    """
    Renders the page showing all designers.
    """
    user = session["user"]
    user_id = user["id"] # This is the UUID from user_profiles

    try:
        # 1. Fetch all designers from the database
        designers_res = supabase.table("designers").select("*").execute()
        all_designers = designers_res.data or []

        # 2. Fetch this user's existing favorites
        favorites_res = supabase.table("saved_favorites").select("designer_id").eq("user_id", user_id).execute()
        
        # 3. Create a simple set of IDs for easy checking in the template
        liked_designer_ids = {f["designer_id"] for f in (favorites_res.data or [])}

        print(f"Found {len(all_designers)} designers.")
        print(f"User likes {len(liked_designer_ids)} designers.")

        return render_template(
            "browse_designers.html", 
            user=user, 
            all_designers=all_designers,
            liked_designer_ids=liked_designer_ids
        )

    except Exception as e:
        print(f"ERROR fetching designers: {e}")
        flash("Could not load designers page.", "danger")
        return redirect(url_for("user_dashboard"))


# The route MUST have <string:designer_id> because it's a UUID
@app.route("/api/designer/<string:designer_id>/like", methods=["POST"])
@login_required
def like_designer(designer_id):
    
    user = session["user"]
    user_id = user["id"] # This is the user's UUID
    
    try:
        # This query now works (UUID == UUID and UUID == UUID)
        existing_like = supabase.table("saved_favorites") \
            .select("id") \
            .eq("user_id", user_id) \
            .eq("designer_id", designer_id) \
            .execute()

        if existing_like.data:
            # It exists, so UN-like (DELETE)
            supabase.table("saved_favorites").delete().eq("id", existing_like.data[0]["id"]).execute()
            print(f"User {user_id} UN-liked designer {designer_id}")
            return jsonify({"status": "unliked", "designer_id": designer_id})
        
        else:
            # It does not exist, so LIKE (INSERT)
            new_like = {
                "user_id": user_id,       # This is a UUID
                "designer_id": designer_id  # This is also a UUID (as a string)
            }
            # This insert will now work
            supabase.table("saved_favorites").insert(new_like).execute()
            print(f"User {user_id} LIKED designer {designer_id}")
            return jsonify({"status": "liked", "designer_id": designer_id})

    except Exception as e:
        # The REAL error will be printed in your terminal
        print(f"ERROR LIKING DESIGNER: {e}") 
        return jsonify({"error": str(e)}), 500

# ... (add this with your other @app.route functions)

@app.route("/saved_favorites")
@login_required
def saved_favorites():
    """
    Renders the page showing BOTH saved designers and saved AI designs.
    """
    user = session["user"]
    user_id = user["id"]
    
    all_favorites = []

    try:
        # 1. Fetch Saved Designers
        designers_res = supabase.table("saved_favorites") \
            .select("designer_id, designers(*)") \
            .eq("user_id", user_id) \
            .execute()

        for f in (designers_res.data or []):
            if f.get("designers"):
                designer_data = f["designers"]
                designer_data["favorite_type"] = "designer" # Add a type
                # Get the 'created_at' from the join table to allow sorting
                designer_data["saved_at"] = f.get("created_at", "1970-01-01T00:00:00Z")
                all_favorites.append(designer_data)

        # 2. Fetch Saved AI Designs
        ai_designs_res = supabase.table("saved_ai_designs") \
            .select("*") \
            .eq("user_id", user_id) \
            .execute()
        
        for d in (ai_designs_res.data or []):
            d["favorite_type"] = "ai_image" # Add a type
            d["saved_at"] = d.get("created_at", "1970-01-01T00:00:00Z")
            all_favorites.append(d)
        
        # 3. Sort all favorites by creation/saved date, newest first
        all_favorites.sort(key=lambda x: x["saved_at"], reverse=True)

        print(f"User {user_id} has {len(all_favorites)} total saved items.")

        return render_template(
            "saved_favorites.html",
            user=user,
            all_favorites=all_favorites
        )

    except Exception as e:
        print(f"ERROR fetching all favorites: {e}")
        flash("Could not load your saved favorites.", "danger")
        return redirect(url_for("user_dashboard"))

@app.route("/designer/<string:designer_id>")
@login_required
def view_designer(designer_id):
    """
    Shows a public-facing portfolio page for a single designer.
    """
    user = session["user"] # For the layout

    try:
        # 1. Fetch the designer's main profile
        designer_res = supabase.table("designers") \
            .select("*") \
            .eq("id", designer_id) \
            .limit(1) \
            .execute()

        if not designer_res.data:
            flash("Sorry, that designer could not be found.", "danger")
            return redirect(request.referrer or url_for("user_dashboard"))

        designer = designer_res.data[0]

        # 2. Fetch all portfolio projects for that designer
        portfolio_res = supabase.table("designer_portfolio") \
            .select("*") \
            .eq("designer_id", designer_id) \
            .order("uploaded_at", desc=True) \
            .execute()
            
        portfolio_projects = portfolio_res.data or []

        print(f"Viewing profile for {designer['designer_name']}")
        print(f"Found {len(portfolio_projects)} portfolio projects.")

        # 3. Render the new template
        return render_template(
            "designer_portfolio_public.html",
            user=user,
            designer=designer,
            portfolio_projects=portfolio_projects
        )

    except Exception as e:
        print(f"ERROR viewing designer profile: {e}")
        flash("An error occurred while trying to load that profile.", "danger")
        return redirect(url_for("user_dashboard"))
    

# ... (add this with your other @app.route functions)

# ------------------ NEW BOOKING ROUTES ------------------

@app.route("/book_consultation/<string:designer_id>", methods=["GET", "POST"])
@login_required
def book_consultation(designer_id):
    """
    Shows the booking form (GET) and handles the submission (POST).
    """
    user = session["user"]
    designer_res = supabase.table("designers").select("*").eq("id", designer_id).limit(1).execute()
    if not designer_res.data:
        flash("Sorry, that designer could not be found.", "danger")
        return redirect(url_for("browse_designers"))
    designer = designer_res.data[0]

    if request.method == "POST":
        try:
            booking_date = request.form.get("booking_date")
            booking_time = request.form.get("booking_time")
            notes = request.form.get("notes")
            full_booking_datetime = f"{booking_date}T{booking_time}:00"

            new_booking = {
                "user_id": user["id"],
                "user_name": user["name"],
                "designer_id": designer["id"],
                "designer_email": designer["email"],
                "booking_date": full_booking_datetime,
                "notes": notes,
                "booking_status": "pending"
            }
            supabase.table("designer_bookings").insert(new_booking).execute()
            flash("Consultation requested! The designer will be notified.", "success")
            return redirect(url_for("my_consultations"))
        except Exception as e:
            print(f"ERROR creating booking: {e}")
            flash("An error occurred while booking. Please try again.", "danger")
    
    return render_template(
        "book_consultation.html", 
        user=user, 
        designer=designer
    )

@app.route("/my_consultations")
@login_required
def my_consultations():
    """
    Shows the HOMEOWNER all their pending/confirmed consultations.
    """
    user = session["user"]
    user_id = user["id"]
    try:
        bookings_res = supabase.table("designer_bookings") \
            .select("*, designers(designer_name, specialisation)") \
            .eq("user_id", user_id) \
            .order("booking_date", desc=True) \
            .execute()
        my_bookings = bookings_res.data or []
        return render_template(
            "my_consultations.html",
            user=user,
            my_bookings=my_bookings
        )
    except Exception as e:
        print(f"ERROR fetching user's consultations: {e}")
        flash("Could not load your consultations.", "danger")
        return redirect(url_for("user_dashboard"))

@app.route("/api/booking/update/<int:booking_id>", methods=["POST"])
@login_required
def update_booking_status(booking_id):
    """
    API route for DESIGNERS to accept/decline bookings.
    """
    user = session["user"]
    
    if user["role"] != "designer":
        return jsonify({"error": "Access denied."}), 403

    data = request.json
    new_status = data.get("status")

    if not new_status in ["confirmed", "declined"]:
        return jsonify({"error": "Invalid status."}), 400

    try:
        # Check that this designer owns this booking
        booking_res = supabase.table("designer_bookings") \
            .select("id, designer_id") \
            .eq("id", booking_id) \
            .eq("designer_id", user["id"]) \
            .limit(1) \
            .execute()

        if not booking_res.data:
            return jsonify({"error": "Booking not found or permission denied."}), 404

        # Update the booking
        update_res = supabase.table("designer_bookings") \
            .update({"booking_status": new_status}) \
            .eq("id", booking_id) \
            .execute()

        if update_res.data:
            print(f"Designer {user['id']} updated booking {booking_id} to {new_status}")
            return jsonify({
                "status": "success", 
                "new_status": new_status,
                "booking_id": booking_id
            }), 200
        else:
            raise Exception("Supabase update returned no data.")

    except Exception as e:
        print(f"ERROR updating booking: {e}")
        return jsonify({"error": str(e)}), 500
    
    
# ---------- Budget Estimator API (FINAL) ----------


@app.route("/budget_estimator", methods=["GET"])
@login_required
def budget_estimator_page():
    user = session["user"]
    return render_template("budget_estimator.html", user=user)

@app.route("/api/estimate_generate", methods=["POST"])
@login_required
def estimate_generate():
    import json
    import google.generativeai as genai
    import os
    from urllib.parse import quote # Crucial for Pollinations URL

    data = request.get_json(silent=True)

    if not data:
        return jsonify({"success": False, "error": "No JSON received"}), 400

    required = [
        "location", "area", "home_type", "style",
        "material", "user_budget", "room_type", "color_palette"
    ]

    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"success": False, "error": f"Missing fields: {missing}"}), 400

    # Configure Gemini
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

    system_prompt = """
    You are an expert interior design budget estimator.
    Output ONLY valid JSON in this format:
    {
      "estimated_cost": number,
      "breakdown": {
        "Furniture": number,
        "Kitchen": number,
        "Paint": number,
        "Electricals": number,
        "Civil": number,
        "Misc": number
      },
      "recommendations": ["string", "string"]
    }
    """

    user_prompt = f"""
    Estimate interior design cost.

    City: {data['location']}
    Area: {data['area']}
    Home Type: {data['home_type']}
    Style: {data['style']}
    Material Quality: {data['material']}
    User Budget: {data['user_budget']}
    """

    # -----------------------------
    # 1️⃣ COST ESTIMATE (Gemini) - CORRECTED MODEL
    # -----------------------------
    try:
        model = genai.GenerativeModel("gemini-2.5-flash") # <-- Corrected to free-tier model

        response = model.generate_content(
            system_prompt + "\n" + user_prompt,
            generation_config={"response_mime_type": "application/json"}
        )

        print("Gemini Raw Output:", response.text)

        cost_data = json.loads(response.text)

    except Exception as e:
        print("Gemini cost estimation error:", e)
        return jsonify({"success": False, "error": str(e)}), 500

    # -----------------------------
    # 2️⃣ IMAGE GENERATION (Pollinations.ai) - FREE SOLUTION
    # -----------------------------
    image_prompt = (
        f"{data['room_type']} interior in {data['style']} style, "
        f"{data['color_palette']} colors, high quality, realistic render, premium materials"
    )

    try:
        # URL Encode the prompt
        encoded_prompt = quote(image_prompt)
        
        # Build the Pollinations URL
        image_url = (
            f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            f"?width=1024&height=1024&nologo=true&model=flux" 
        )
        print("Pollinations Image URL:", image_url)


    except Exception as e:
        print("Pollinations image URL generation error:", e)
        image_url = None

    # -----------------------------
    # 3️⃣ SAVE TO SUPABASE
    # -----------------------------
    try:
        # NOTE: Assumes 'supabase' object is defined globally or passed in.
        supabase.table("budget_estimates").insert({
            "user_id": session["user"]["id"],
            "location": data["location"],
            "area": data["area"],
            "home_type": data["home_type"],
            "style": data["style"],
            "material": data["material"],
            "estimated_cost": cost_data["estimated_cost"],
            "breakdown": cost_data["breakdown"],
            "image_url": image_url
        }).execute()

    except Exception as e:
        print("Supabase Insert Error:", e)

    # -----------------------------
    # 4️⃣ SEND TO FRONTEND
    # -----------------------------
    return jsonify({
        "success": True,
        "estimated_cost": cost_data["estimated_cost"],
        "breakdown": cost_data["breakdown"],
        "image_url": image_url,
        "recommendations": cost_data.get("recommendations", [])
    })
#-----------------project timeline---------------------
# Add this import at the top of your app.py file

@app.route("/project_timeline")
@login_required
def project_timeline_page():
    """Serves the main HTML page for the timeline module."""
    # This route just renders the HTML file
    user = session["user"]
    return render_template("project_timeline.html",user=user)

# --- New API Endpoint ---
@app.route("/api/timeline_generate", methods=["POST"])
@login_required
def timeline_generate():
    import json
    import google.generativeai as genai
    import os
    from datetime import datetime, timedelta

    data = request.get_json(silent=True)

    required_budget = ["start_date", "area", "home_type", "style", "material"]
    if any(f not in data for f in required_budget):
        return jsonify({"success": False, "error": "Missing required project base fields for timeline"}), 400

    # Retrieve core budget inputs
    area = int(data.get('area', 1500))
    material = data.get('material', 'Premium')
    project_start = data['start_date']
    
    # Retrieve new optional inputs (with defaults)
    work_week_days = int(data.get('work_week', 5))
    site_complexity = data.get('site_complexity', 'Easy')
    decision_speed = data.get('decision_speed', 'Standard')

    # 1. Custom Logic to set the primary input variables (Procurement & Execution)
    
    # --- Base Durations ---
    concept_weeks = 2 # Base fixed duration for Phase 1
    
    # Procurement (Material-based Lead Time)
    if material == "Basic":
        procurement_weeks = 6
    elif material == "Premium":
        procurement_weeks = 8
    elif material == "Luxury":
        procurement_weeks = 12
    else:
        procurement_weeks = 8 # Default

    # On-Site Execution (Area-based Duration)
    if area < 1000:
        execution_weeks = 4
    elif area < 2000:
        execution_weeks = 6
    else:
        execution_weeks = 8
        
    # --- 1A. Apply Complexity Modifiers (Python Logic) ---
    
    # Modifier for Client Decision Speed (Phase 1 & 2)
    if decision_speed == 'Slow':
        concept_weeks += 1      # Add 1 week for extra design review time
        procurement_weeks += 1  # Add 1 week for delayed material selection sign-off
    
    # Modifier for Site Complexity (Phase 3)
    # Note: Standard adds 1 week, Difficult adds 2 weeks. Easy adds 0.
    if site_complexity == 'Difficult':
        execution_weeks += 2    
    elif site_complexity == 'Standard':
        execution_weeks += 1    

    # Phase 4 remains fixed
    installation_weeks = 1 
    
    # Configure Gemini
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

    # 2. Gemini System Prompt (Define the rules and output format)
    # UPDATED: Now uses the dynamic work_week_days variable
    system_prompt = f"""
    You are an expert interior design project scheduler.
    Your task is to calculate the start and end dates for a sequential 4-phase project timeline based on the client's inputs and assumed phase durations.
    - Assume a {work_week_days}-day work week. If {work_week_days} is 5, assume Mon-Fri. If 6, assume Mon-Sat. If 7, assume all days. Do not include non-working days in the duration calculation.
    - Output ONLY valid JSON in the specified format.
    - Provide realistic, descriptive text for the 'details' field for each phase.
    """ + json.dumps({
        "total_project_days": "number (total duration including weekends)",
        "end_date": "YYYY-MM-DD (final project completion date)",
        "phases": [
            {
                "name": "string (Concept & Design, Procurement & Manufacturing, On-Site Execution & Civil Works, Installation & Styling)",
                "duration_weeks": "number",
                "details": "string (brief description of the work)",
                "start_date": "YYYY-MM-DD",
                "end_date": "YYYY-MM-DD"
            }
        ]
    })
    
    # 3. Gemini User Prompt (Provide the inputs and calculated durations)
    # UPDATED: Uses the modified phase durations
    user_prompt = f"""
    Calculate a project timeline.
    Project Start Date: {project_start} (Must be the start of Phase 1)

    Phase 1 (Concept & Design): {concept_weeks} weeks (Fixed/Adjusted)
    Phase 2 (Procurement & Manufacturing): {procurement_weeks} weeks (Material-Based/Adjusted)
    Phase 3 (On-Site Execution & Civil Works): {execution_weeks} weeks (Area-Based/Adjusted)
    Phase 4 (Installation & Styling): {installation_weeks} week (Fixed)
    
    Ensure the start date of each phase is the day immediately following the end date of the previous phase.
    Return the full JSON.
    """
    # 4. API Call and Response
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")

        response = model.generate_content(
            system_prompt + "\n" + user_prompt,
            generation_config={"response_mime_type": "application/json"}
        )

        timeline_data = json.loads(response.text)
        return jsonify({"success": True, "timeline": timeline_data})

    except Exception as e:
        print("Gemini timeline estimation error:", e)
        # Fallback error for non-Gemini related issues like network or JSON parsing
        return jsonify({"success": False, "error": str(e)}), 500
# ... (other imports)
if __name__ == "__main__":
    app.run(debug=True)
