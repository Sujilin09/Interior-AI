"""
Interior AI - Blueprint Version
Converted from redesign_app.py for modular integration.
"""

import base64
import io
import json
import os
import uuid
import requests
import time
import warnings
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions as SyncClientOptions
import httpx

from dotenv import load_dotenv
# --- MODIFICATION: Import session, redirect, url_for, and flash ---
from flask import Blueprint, jsonify, render_template, request, session, redirect, url_for, flash
from flask_cors import CORS
from PIL import Image
from pydantic import BaseModel, Field, ValidationError

# Suppress SSL warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
http_client = httpx.Client(verify=False)
# options = SyncClientOptions(httpx_client=http_client)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ===========================
# FLASK BLUEPRINT SETUP
# ===========================

# --- MODIFICATION: Create Blueprint instead of App ---
# We'll prefix all routes with '/redesign'
redesign_bp = Blueprint('redesign', __name__, template_folder='templates')
CORS(redesign_bp) # Apply CORS to the blueprint

DESIGN_DATABASE: Dict[str, Dict] = {}

# FREE API Options - Choose one
API_PROVIDER = os.getenv("API_PROVIDER", "pollinations")
print(f"[INFO] Using API Provider: {API_PROVIDER}")


# ===========================
# ENUMS & DATA MODELS
# (UNCHANGED)
# ===========================

class DesignStyle(str, Enum):
    MODERN_MINIMALIST = "modern_minimalist"
    SCANDINAVIAN = "scandinavian"
    INDUSTRIAL = "industrial"
    BOHEMIAN = "bohemian"
    LUXURY = "luxury"
    JAPANESE_ZEN = "japanese_zen"
    COASTAL = "coastal"
    FARMHOUSE = "farmhouse"

class RoomType(str, Enum):
    BEDROOM = "bedroom"
    LIVING_ROOM = "living_room"
    KITCHEN = "kitchen"
    BATHROOM = "bathroom"
    OFFICE = "office"
    DINING_ROOM = "dining_room"

class UserPreferences(BaseModel):
    room_type: RoomType
    styles: List[DesignStyle]
    color_preferences: Optional[List[str]] = None
    budget_level: Optional[str] = "medium"
    keep_furniture: bool = False

class DesignResponse(BaseModel):
    design_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    style: str
    image_url: str
    processing_time: float
    confidence_score: float
    liked: bool = False


# ===========================
# STYLE & ROOM DESCRIPTIONS
# (UNCHANGGAED)
# ===========================

STYLE_DESCRIPTIONS = {
    DesignStyle.MODERN_MINIMALIST: "clean lines, minimal clutter, neutral palette with white gray beige, sleek furniture, open space, natural light",
    DesignStyle.SCANDINAVIAN: "Nordic style, light wood furniture, soft textiles, white walls, green plants, cozy hygge, functional minimalist design",
    DesignStyle.INDUSTRIAL: "exposed brick, metal fixtures, concrete floors, Edison bulbs, leather furniture, urban loft, raw materials, neutral tones",
    DesignStyle.BOHEMIAN: "colorful textiles, patterned rugs, abundant plants, eclectic vintage furniture, macrame, warm ambient lighting, vibrant colors",
    DesignStyle.LUXURY: "elegant furnishings, velvet upholstery, marble surfaces, gold accents, crystal fixtures, premium materials, sophisticated styling",
    DesignStyle.JAPANESE_ZEN: "minimalist, natural wood, bamboo elements, low furniture, earth tones, shoji screens, tranquil serene atmosphere, zen garden",
    DesignStyle.COASTAL: "light airy feel, white and blue palette, natural textures, driftwood, nautical elements, beach inspired, breezy atmosphere",
    DesignStyle.FARMHOUSE: "rustic charm, reclaimed wood, vintage furniture, shiplap walls, cozy textiles, warm inviting, farmhouse aesthetic"
}

ROOM_DESCRIPTIONS = {
    RoomType.BEDROOM: "comfortable bed with headboard, nightstands with lamps, dresser, soft bedding, pillows, window with curtains",
    RoomType.LIVING_ROOM: "sofa, armchairs, coffee table, entertainment center, bookshelf, area rug, window treatments, decorative accessories",
    RoomType.KITCHEN: "modern appliances, cabinetry, countertop, sink, stove, island or dining counter, lighting fixtures, backsplash",
    RoomType.BATHROOM: "vanity with sink, mirror with lighting, toilet, bathtub or shower, tile flooring, wall tiles, shelving, ambient lighting",
    RoomType.OFFICE: "desk with chair, computer setup, shelving or bookcases, task lighting, storage cabinets, organized workspace, plants",
    RoomType.DINING_ROOM: "dining table, dining chairs, buffet or sideboard, chandelier or pendant lights, area rug, centerpiece"
}


# ===========================
# IMAGE UTILITIES
# (UNCHANGED)
# ===========================

def resize_image(image: Image.Image, max_size: int = 768) -> Image.Image:
    """Resize image for API"""
    if max(image.size) <= max_size:
        return image
    
    ratio = max_size / max(image.size)
    new_size = (int(image.width * ratio), int(image.height * ratio))
    
    # Make dimensions divisible by 8
    new_size = (new_size[0] - new_size[0] % 8, new_size[1] - new_size[1] % 8)
    
    return image.resize(new_size, Image.Resampling.LANCZOS)


# ===========================
# AI DESIGN GENERATOR - FULLY FIXED
# (UNCHANGED)
# ===========================

class DesignGenerator:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.provider = API_PROVIDER

    def generate_designs(self, image: Image.Image, preferences: UserPreferences) -> List[DesignResponse]:
        """Generate room designs using free APIs"""
        
        if image.mode not in ('RGB', 'RGBA'):
            image = image.convert('RGB')
        
        image = resize_image(image, max_size=768)
        
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        image_b64 = base64.b64encode(buffered.getvalue()).decode()
        
        print(f"Image size: {image.size}")
        print(f"Generating {len(preferences.styles)} designs...")
        
        designs = []
        for idx, style in enumerate(preferences.styles[:4]):
            try:
                result = self._generate_single_design(image_b64, style, preferences)
                if result:
                    designs.append(result)
                    DESIGN_DATABASE[result.design_id] = result.dict()
                    print(f"[OK] Generated {style.value}")
                else:
                    print(f"[FAIL] Failed to generate {style.value}")
                
                # Rate limiting between requests
                if idx < len(preferences.styles) - 1:
                    time.sleep(1)
            
            except Exception as e:
                print(f"[ERROR] Error generating {style.value}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        return designs

    def _generate_single_design(
        self, 
        image_b64: str, 
        style: DesignStyle, 
        preferences: UserPreferences
    ) -> Optional[DesignResponse]:
        """Generate a single design"""
        start_time = datetime.now()
        
        try:
            style_desc = STYLE_DESCRIPTIONS[style]
            room_desc = ROOM_DESCRIPTIONS[preferences.room_type]
            room_name = preferences.room_type.value.replace('_', ' ')
            
            color_context = ""
            if preferences.color_preferences:
                colors = ", ".join(preferences.color_preferences)
                color_context = f", featuring {colors} tones"
            
            # Simplified prompt for better compatibility
            prompt = (
                f"interior design {room_name} {style.value.replace('_', ' ')} style "
                f"{style_desc} {room_desc}{color_context} "
                f"professional photography high quality well lit realistic"
            )
            
            print(f"[{style.value}] Generating with prompt length: {len(prompt)}")
            
            if self.provider == "pollinations":
                output_url = self._generate_pollinations(prompt)
            elif self.provider == "segmind":
                output_url = self._generate_segmind(prompt)
            elif self.provider == "huggingface":
                output_url = self._generate_huggingface(prompt)
            else:
                print(f"[WARNING] Unknown provider: {self.provider}, using Pollinations")
                output_url = self._generate_pollinations(prompt)
            
            if not output_url:
                print(f"[{style.value}] Failed - no output URL")
                return None
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return DesignResponse(
                style=style.value,
                image_url=output_url,
                processing_time=processing_time,
                confidence_score=0.88
            )
        
        except Exception as e:
            print(f"[{style.value}] Error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _generate_pollinations(self, prompt: str) -> Optional[str]:
        """Pollinations.ai - Fixed version with proper error handling"""
        try:
            # Clean and encode prompt properly
            clean_prompt = prompt.replace('\n', ' ').strip()
            encoded_prompt = quote(clean_prompt)
            
            # Use the correct API endpoint
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            
            # Add parameters for better results
            params = {
                "width": 768,
                "height": 768,
                "nologo": "true",
                "enhance": "true"
            }
            
            # Build URL with params
            param_str = "&".join([f"{k}={v}" for k, v in params.items()])
            full_url = f"{url}?{param_str}"
            
            print(f"Calling Pollinations API...")
            print(f"URL: {full_url[:80]}...")
            
            # Use headers to mimic browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Make request with SSL verification disabled and longer timeout
            response = requests.get(
                full_url, 
                headers=headers, 
                timeout=120, 
                allow_redirects=True,
                verify=False
            )
            
            print(f"Response status: {response.status_code}")
            print(f"Content type: {response.headers.get('Content-Type', 'unknown')}")
            
            if response.status_code == 200:
                # Check if we got an image
                content_type = response.headers.get('Content-Type', '')
                if 'image' in content_type or len(response.content) > 1000:
                    image_data = response.content
                    image_b64 = base64.b64encode(image_data).decode()
                    print(f"[OK] Pollinations Success! Image size: {len(image_data)} bytes")
                    return f"data:image/png;base64,{image_b64}"
                else:
                    print(f"[ERROR] Response is not an image: {content_type}")
                    print(f"Response text: {response.text[:200]}")
                    return None
            else:
                print(f"[ERROR] Pollinations error {response.status_code}")
                print(f"Response: {response.text[:200]}")
                return None
        
        except requests.exceptions.Timeout:
            print(f"[ERROR] Pollinations timeout after 120s")
            return None
        except requests.exceptions.ConnectionError as e:
            print(f"[ERROR] Pollinations connection error: {e}")
            return None
        except Exception as e:
            print(f"[ERROR] Pollinations error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _generate_segmind(self, prompt: str) -> Optional[str]:
        """Segmind API - Free tier option"""
        try:
            api_key = os.getenv("SEGMIND_API_KEY")
            
            if not api_key:
                print("[ERROR] Segmind API key not found in .env")
                return None
            
            url = "https://api.segmind.com/v1/sd1.5-txt2img"
            
            headers = {
                "x-api-key": api_key,
                "Content-Type": "application/json"
            }
            
            payload = {
                "prompt": prompt,
                "negative_prompt": "ugly, blurry, low quality, distorted",
                "samples": 1,
                "steps": 20,
                "width": 768,
                "height": 768
            }
            
            print(f"Calling Segmind API...")
            response = requests.post(url, headers=headers, json=payload, timeout=90, verify=False)
            
            if response.status_code == 200:
                image_data = response.content
                image_b64 = base64.b64encode(image_data).decode()
                print(f"[OK] Segmind Success!")
                return f"data:image/png;base64,{image_b64}"
            else:
                print(f"[ERROR] Segmind error: {response.status_code}")
                print(f"Response: {response.text[:200]}")
                return None
        
        except Exception as e:
            print(f"[ERROR] Segmind error: {e}")
            return None

    def _generate_huggingface(self, prompt: str) -> Optional[str]:
        """HuggingFace Inference API - Free tier"""
        try:
            api_key = os.getenv("HUGGINGFACE_API_KEY")
            
            if not api_key:
                print("[ERROR] HuggingFace API key not found in .env")
                return None
            
            url = "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "inputs": prompt,
                "parameters": {
                    "negative_prompt": "ugly, blurry, low quality, distorted"
                }
            }
            
            print(f"Calling HuggingFace API...")
            response = requests.post(url, headers=headers, json=payload, timeout=90, verify=False)
            
            if response.status_code == 200:
                image_data = response.content
                image_b64 = base64.b64encode(image_data).decode()
                print(f"[OK] HuggingFace Success!")
                return f"data:image/png;base64,{image_b64}"
            elif response.status_code == 503:
                print(f"[ERROR] HuggingFace model loading, retry in 20s...")
                return None
            else:
                print(f"[ERROR] HuggingFace error: {response.status_code}")
                print(f"Response: {response.text[:200]}")
                return None
        
        except Exception as e:
            print(f"[ERROR] HuggingFace error: {e}")
            return None


# ===========================
# API ENDPOINTS
# --- MODIFICATION: Use @redesign_bp.route ---
# ===========================

generator = DesignGenerator()

# --- *** THIS IS THE CRITICAL FIX *** ---
@redesign_bp.route("/upload")
def upload_wizard():
    """Serves the multi-step upload wizard page."""
    
    # We must check for the user in the session, just like your
    # @login_required decorator does in app.py
    if "user" not in session:
        flash("You must be logged in to start a new design.", "warning")
        # Redirect to the main app's login page for users
        return redirect(url_for("login_user")) 
    
    # If they are logged in, get the user from the session
    user = session["user"]
    
    # Now we pass the REAL user object to the template,
    # which satisfies layout.html
    return render_template("room_upload.html", user=user)
# --- *** END OF FIX *** ---


@redesign_bp.route("/api/generate", methods=['POST'])
def generate_room_designs():
    """Generate interior designs"""
    
    # --- ADDED: A login check for the API endpoint too ---
    if "user" not in session:
        return jsonify({"detail": "Authentication required."}), 401
    # --- END ADDITION ---

    try:
        # Validate request
        if 'image' not in request.files:
            return jsonify({"detail": "No image file provided"}), 400
        if 'preferences' not in request.form:
            return jsonify({"detail": "No preferences provided"}), 400

        image_file = request.files['image']
        preferences_str = request.form['preferences']
        
        # Parse preferences
        try:
            user_prefs = UserPreferences(**json.loads(preferences_str))
        except ValidationError as e:
            print(f"Validation error: {e}")
            return jsonify({"detail": f"Invalid preferences: {str(e)}"}), 400
        except json.JSONDecodeError as e:
            print(f"JSON error: {e}")
            return jsonify({"detail": f"Invalid JSON in preferences: {str(e)}"}), 400
        
        # Process image
        try:
            pil_image = Image.open(image_file.stream)
            
            if pil_image.mode not in ('RGB', 'RGBA'):
                pil_image = pil_image.convert('RGB')
                
            print(f"Processing image: {pil_image.size}")
            print(f"Room: {user_prefs.room_type}, Styles: {[s.value for s in user_prefs.styles]}")
            
        except Exception as e:
            print(f"Image error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"detail": f"Invalid image file: {str(e)}"}), 400
        
        # Generate designs
        designs = generator.generate_designs(pil_image, user_prefs)
        
        if not designs:
            print("ERROR: No designs generated!")
            return jsonify({
                "detail": "Could not generate designs. The API may be unavailable. Please try again later.",
                "suggestion": "Try a different image or check your internet connection."
            }), 500
        
        print(f"Successfully generated {len(designs)} designs")
        return jsonify([d.dict() for d in designs])
        
    except Exception as e:
        print(f"CRITICAL Generation error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "detail": f"Server error: {str(e)}",
            "error_type": type(e).__name__
        }), 500


@redesign_bp.route("/api/designs/<string:design_id>/like", methods=['POST'])
def like_design(design_id: str):
    """Toggle like status and save to Supabase."""

    if "user" not in session:
        return jsonify({"detail": "Authentication required."}), 401

    user = session["user"]
    user_id = user["id"]

    # Find the design in our temporary database
    design_data = DESIGN_DATABASE.get(design_id)
    if not design_data:
        return jsonify({"detail": "Design not found or app was restarted."}), 404

    try:
        # Check if it's already liked in the database
        existing_like = supabase.table("saved_ai_designs") \
            .select("id") \
            .eq("user_id", user_id) \
            .eq("design_id", design_id) \
            .execute()

        if existing_like.data:
            # UN-like (DELETE)
            supabase.table("saved_ai_designs").delete().eq("id", existing_like.data[0]["id"]).execute()
            print(f"User {user_id} UN-liked AI design {design_id}")
            return jsonify({"status": "unliked", "design_id": design_id, "liked": False})

        else:
            # LIKE (INSERT)
            new_like = {
                "user_id": user_id,
                "design_id": design_data["design_id"],
                "style": design_data["style"],
                "image_url": design_data["image_url"]
            }
            supabase.table("saved_ai_designs").insert(new_like).execute()
            print(f"User {user_id} LIKED AI design {design_id}")
            return jsonify({"status": "liked", "design_id": design_id, "liked": True})

    except Exception as e:
        print(f"ERROR LIKING AI DESIGN: {e}")
        return jsonify({"error": str(e)}), 500

@redesign_bp.route("/api/styles", methods=['GET'])
def get_available_styles():
    """Get all available design styles"""
    # No login needed for this
    return jsonify({
        "modern_minimalist": {"name": "Modern Minimalist"},
        "scandinavian": {"name": "Scandinavian"},
        "industrial": {"name": "Industrial"},
        "bohemian": {"name": "Bohemian"},
        "luxury": {"name": "Luxury"},
        "japanese_zen": {"name": "Japanese Zen"},
        "coastal": {"name": "Coastal"},
        "farmhouse": {"name": "Farmhouse"}
    })


@redesign_bp.route("/api/room-types", methods=['GET'])
def get_room_types():
    """Get all available room types"""
    # No login needed for this
    return jsonify([e.value for e in RoomType])


@redesign_bp.route("/health", methods=['GET'])
def health_check():
    """Health check"""
    return jsonify({
        "status": "healthy", 
        "service": "Interior AI FREE (Blueprint)",
        "provider": API_PROVIDER
    })


# ===========================
# DESIGNER PROFILE PAGE (EDIT PROFILE + PORTFOLIO)
# ===========================
@redesign_bp.route("/designer/profile", methods=["GET", "POST"])
def designer_profile():
    """Show and update designer's profile & portfolio (blueprint version)."""

    # 1) Use the unified session structure used by app.py
    user = session.get("user")
    if not user:
        flash("Please log in to view your profile.", "error")
        # Redirect to main app login (keeps original behavior)
        return redirect(url_for("login_user"))

    # Ensure this is a designer
    if user.get("role") != "designer":
        flash("Access denied. Only designers can access this page.", "error")
        return redirect(url_for("user_dashboard"))

    designer_id = user.get("id")

    # 2) Fetch designer details
    try:
        response = supabase.table("designers").select("*").eq("id", designer_id).limit(1).execute()
        if not response.data:
            flash("Designer profile not found.", "error")
            return redirect(url_for("dashboard"))
        designer = response.data[0]
    except Exception as e:
        print(f"[ERROR] Could not fetch designer: {e}")
        flash("Database error fetching profile.", "error")
        return redirect(url_for("dashboard"))

    # 3) Handle POST (update)
    if request.method == "POST":
        try:
            # Read and normalise inputs
            specialisation = request.form.get("specialisation")
            studio_name = request.form.get("studio_name")
            years_experience = request.form.get("years_experience")
            portfolio_url = request.form.get("portfolio_url")
            bio = request.form.get("bio")
            design_styles = request.form.getlist("design_styles")  # list

            # Convert numeric fields safely
            years_experience_val = None
            if years_experience and years_experience.strip():
                try:
                    years_experience_val = int(years_experience)
                except ValueError:
                    # If invalid number, flash and return
                    flash("Please enter a valid number for years of experience.", "error")
                    return redirect(url_for("redesign.designer_profile"))

            updated_data = {
                "specialisation": specialisation,
                "studio_name": studio_name,
                "years_experience": years_experience_val,
                "portfolio_url": portfolio_url,
                "bio": bio,
                "design_styles": design_styles
            }

            # IMPORTANT: Do not delete keys from the payload here.
            # Let Supabase set fields to null if you explicitly want to.
            supabase.table("designers").update(updated_data).eq("id", designer_id).execute()

            # Supabase .update() may return empty .data — treat execute success as success if no exception
            flash("✅ Profile updated successfully!", "success")
            return redirect(url_for("redesign.designer_profile"))

        except Exception as e:
            print(f"[ERROR] Failed to update profile: {e}")
            flash("❌ Could not update profile. Check server logs.", "error")
            return redirect(url_for("redesign.designer_profile"))

    # 4) GET — render the edit template. Make sure the template exists and extends layout
    return render_template("edit_designer_profile.html", designer=designer, user=user)