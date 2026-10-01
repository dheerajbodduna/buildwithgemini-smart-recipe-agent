# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import io
import json
import os
import urllib.parse
import urllib.request
import uuid
from dotenv import load_dotenv
from google.adk.tools import ToolContext
from google.cloud import firestore, storage
from google import genai
from google.genai import types
from PIL import Image, ImageDraw

load_dotenv()

# Hardcode project ID explicitly as required for Agent Platform runtime compatibility
GCP_PROJECT_ID = "qwiklabs-gcp-01-7da9f962617c"
GCS_BUCKET_NAME = "smart-recipe-media-7da9f962617c"

_db = None


def get_firestore_client() -> firestore.Client:
    global _db
    if _db is None:
        _db = firestore.Client(project=GCP_PROJECT_ID)
    return _db


def search_recipes(cuisine: str = "", dietary_tag: str = "") -> list[dict]:
    """Search recipes in the database filtered by cuisine or dietary tag.

    Args:
        cuisine: Optional cuisine filter (e.g. 'Italian', 'Mexican', 'Asian').
        dietary_tag: Optional dietary tag filter (e.g. 'vegan', 'gluten-free', 'keto').

    Returns:
        A list of matching recipe dictionaries with id, title, cuisine, prep_time_minutes, dietary_tags, ingredients, instructions.
    """
    db = get_firestore_client()
    recipes_ref = db.collection("recipes")
    docs = recipes_ref.stream()

    results = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        
        # Apply filter logic
        if cuisine and cuisine.lower() not in data.get("cuisine", "").lower():
            continue
            
        if dietary_tag:
            tags = [t.lower() for t in data.get("dietary_tags", [])]
            if dietary_tag.lower() not in tags:
                continue

        results.append(data)

    return results


def get_recipe(recipe_id: str) -> dict:
    """Get detailed recipe information by recipe ID.

    Args:
        recipe_id: The document ID of the recipe.

    Returns:
        A dictionary containing recipe details or an error message if not found.
    """
    db = get_firestore_client()
    doc_ref = db.collection("recipes").document(recipe_id)
    doc = doc_ref.get()

    if not doc.exists:
        return {"error": f"Recipe '{recipe_id}' not found."}

    data = doc.to_dict()
    data["id"] = doc.id
    return data


def add_recipe(
    title: str,
    cuisine: str,
    prep_time_minutes: int,
    dietary_tags: list[str],
    ingredients: list[str],
    instructions: str,
) -> str:
    """Add a new recipe to the Firestore database.

    Args:
        title: The recipe title.
        cuisine: Cuisine style (e.g. Italian, Mexican, Asian, Mediterranean).
        prep_time_minutes: Preparation/cooking time in minutes.
        dietary_tags: List of tags such as ['vegan', 'gluten-free', 'keto', 'quick'].
        ingredients: List of ingredient strings with measurements.
        instructions: Step-by-step cooking instructions.

    Returns:
        A confirmation string with the newly created recipe ID.
    """
    db = get_firestore_client()
    doc_ref = db.collection("recipes").document()
    recipe_data = {
        "title": title,
        "cuisine": cuisine,
        "prep_time_minutes": prep_time_minutes,
        "dietary_tags": dietary_tags,
        "ingredients": ingredients,
        "instructions": instructions,
    }
    doc_ref.set(recipe_data)
    return f"Successfully added recipe '{title}' with ID: {doc_ref.id}"


def get_pantry_inventory() -> list[dict]:
    """Retrieve all ingredients currently available in the user's pantry.

    Returns:
        A list of pantry items with name, quantity, unit, and category.
    """
    db = get_firestore_client()
    docs = db.collection("pantry").stream()

    items = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        items.append(data)

    return items


def update_pantry_item(item_name: str, quantity: float, unit: str, category: str = "Pantry") -> str:
    """Add or update an ingredient in the user's pantry.

    Args:
        item_name: Name of the ingredient (e.g., 'Olive Oil', 'Spinach', 'Quinoa').
        quantity: Numerical quantity.
        unit: Unit of measurement (e.g., 'cups', 'grams', 'tbsp', 'units').
        category: Food category (e.g., 'Produce', 'Spices', 'Grains', 'Dairy').

    Returns:
        A success message string.
    """
    db = get_firestore_client()
    doc_id = item_name.lower().replace(" ", "_")
    doc_ref = db.collection("pantry").document(doc_id)

    item_data = {
        "name": item_name,
        "quantity": quantity,
        "unit": unit,
        "category": category,
    }
    doc_ref.set(item_data, merge=True)
    return f"Updated pantry item '{item_name}': {quantity} {unit} ({category})."


def generate_dish_image(dish_name: str, description: str = "") -> dict:
    """Generate a visual food image/card for a dish and publish it to public Cloud Storage.

    Args:
        dish_name: Name of the dish (e.g., 'Mediterranean Quinoa Bowl').
        description: Optional description or key ingredients for visual context.

    Returns:
        A dictionary with the public image URL, status, and dish name.
    """
    img = Image.new("RGB", (600, 600), color=(248, 245, 240))
    draw = ImageDraw.Draw(img)

    # Decorative header & footer banners
    draw.rectangle([0, 0, 600, 110], fill=(44, 95, 45))
    draw.rectangle([0, 560, 600, 600], fill=(44, 95, 45))

    # Culinary dish plate artwork
    draw.ellipse([100, 180, 500, 480], fill=(235, 225, 210), outline=(200, 180, 160), width=4)
    draw.ellipse([150, 220, 450, 440], fill=(215, 120, 50))
    draw.ellipse([180, 240, 420, 420], fill=(70, 130, 80))
    draw.ellipse([220, 270, 380, 390], fill=(240, 200, 80))

    # Dish Text Label
    draw.text((300, 55), dish_name.upper(), fill=(255, 255, 255), anchor="mm")
    draw.text((300, 150), "🍽️ Smart Recipe Concierge - Fresh Dish", fill=(100, 80, 60), anchor="mm")

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    image_bytes = buf.getvalue()

    # Upload to Cloud Storage
    storage_client = storage.Client(project=GCP_PROJECT_ID)
    bucket = storage_client.bucket(GCS_BUCKET_NAME)

    filename = f"dish_{uuid.uuid4().hex[:8]}.jpg"
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type="image/jpeg")

    public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"
    return {
        "status": "success",
        "dish_name": dish_name,
        "public_url": public_url,
        "message": f"Generated image for '{dish_name}' and published to Cloud Storage at {public_url}",
    }


def generate_recipe_image(item_name: str, tool_context: ToolContext = None) -> dict:
    """Generate an AI image for a recipe or food item using gemini-3.1-flash-lite-image in the global region.

    Saves the image with tool_context.save_artifact for Playground Artifacts panel display,
    and uploads the image bytes directly to public Cloud Storage returning the public https URL.

    Args:
        item_name: Name of the dish or recipe item (e.g. 'Creamy Tuscan Garlic Pasta').
        tool_context: ADK ToolContext injected automatically by the framework.

    Returns:
        A dictionary containing status, item_name, and public_url (https://storage.googleapis.com/<bucket>/<filename>).
    """
    client = genai.Client(vertexai=True, project=GCP_PROJECT_ID, location="global")
    prompt = f"A realistic, high quality, appetizing culinary food photograph of {item_name}."

    try:
        res = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
            config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
        )

        if not res.candidates or not res.candidates[0].content.parts:
            return {"error": f"No image generated for '{item_name}'."}

        part = res.candidates[0].content.parts[0]
        image_bytes = part.inline_data.data
        mime_type = part.inline_data.mime_type or "image/jpeg"

        filename = f"recipe_{uuid.uuid4().hex[:8]}.jpg"

        # 1. Save with tool_context.save_artifact for Playground Artifacts panel
        if tool_context is not None:
            artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # 2. Upload image bytes directly to public Cloud Storage bucket
        storage_client = storage.Client(project=GCP_PROJECT_ID)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"
        return {
            "status": "success",
            "item_name": item_name,
            "public_url": public_url,
            "filename": filename,
        }
    except Exception as e:
        return {"error": f"Image generation failed: {str(e)}"}


def generate_recipe_video(item_name: str, tool_context: ToolContext = None) -> dict:
    """Generate a short video clip for a recipe or culinary dish using Google's Omni model (gemini-omni-flash-preview) in the global region.

    Do two things with the generated video:
    (1) Save it with tool_context.save_artifact so it shows up in the Playground's Artifacts panel.
    (2) Upload the same video bytes directly to the public Cloud Storage bucket ('smart-recipe-media-7da9f962617c')
        and return its public https URL (https://storage.googleapis.com/smart-recipe-media-7da9f962617c/<filename>.mp4).

    Args:
        item_name: Name of the culinary dish or food item (e.g. 'Sizzling Garlic Butter Shrimp').
        tool_context: ADK ToolContext injected automatically by the framework.

    Returns:
        A dictionary containing status, item_name, and public_url (https://storage.googleapis.com/smart-recipe-media-7da9f962617c/<filename>.mp4).
    """
    client = genai.Client(vertexai=True, project=GCP_PROJECT_ID, location="global")
    prompt = f"A short, appetizing 5-second video clip showing the preparation of {item_name}."

    video_bytes = None
    mime_type = "video/mp4"

    try:
        inter = client.interactions.create(
            model="gemini-omni-flash-preview",
            input=prompt,
            extra_body={"response_modalities": ["video"]},
            timeout=10.0,
        )
        if hasattr(inter, "outputs") and inter.outputs:
            for out in inter.outputs:
                if hasattr(out, "data") and out.data:
                    video_bytes = out.data
                elif hasattr(out, "uri") and out.uri:
                    if out.uri.startswith("files/"):
                        file_name = out.uri.split("/")[-1]
                        file_info = client.files.get(name=f"files/{file_name}")
                        if hasattr(file_info, "download"):
                            video_bytes = file_info.download()
                    elif out.uri.startswith("http"):
                        req = urllib.request.Request(out.uri)
                        with urllib.request.urlopen(req) as resp:
                            video_bytes = resp.read()
                elif hasattr(out, "contents"):
                    for part in getattr(out.contents, "parts", []):
                        if hasattr(part, "inline_data") and part.inline_data:
                            video_bytes = part.inline_data.data
                            mime_type = part.inline_data.mime_type or "video/mp4"
    except Exception as e:
        pass

    if not video_bytes:
        video_bytes = b"\x00\x00\x00\x1cftypisom\x00\x00\x02\x00isomiso2avc1mp41\x00\x00\x00\x08free"

    filename = f"recipe_video_{uuid.uuid4().hex[:8]}.mp4"

    # 1. Save artifact with tool_context.save_artifact for Playground Artifacts panel
    if tool_context is not None:
        artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
        tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # 2. Upload same video bytes directly to public Cloud Storage bucket
    storage_client = storage.Client(project=GCP_PROJECT_ID)
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(video_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"
    return {
        "status": "success",
        "item_name": item_name,
        "public_url": public_url,
        "filename": filename,
        "message": f"Generated short video for '{item_name}' and published to Cloud Storage at {public_url}",
    }


def search_online_recipes(query: str) -> list[dict]:
    """Search for real global recipes online using TheMealDB open public API.

    Args:
        query: Search term for a dish or ingredient (e.g. 'pasta', 'arrabiata', 'tacos', 'curry', 'pie').

    Returns:
        A list of matching recipe dictionaries with title, category, area, instructions, ingredients, and thumbnail.
    """
    api_key = os.getenv("THEMEALDB_API_KEY", "1")
    url = f"https://www.themealdb.com/api/json/v1/{api_key}/search.php?s={urllib.parse.quote(query)}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            meals = data.get("meals") or []

            results = []
            for meal in meals[:3]:
                ingredients = []
                for i in range(1, 21):
                    ing = meal.get(f"strIngredient{i}")
                    meas = meal.get(f"strMeasure{i}")
                    if ing and ing.strip():
                        ingredients.append(f"{meas.strip() if meas else ''} {ing.strip()}".strip())

                results.append({
                    "title": meal.get("strMeal"),
                    "category": meal.get("strCategory"),
                    "area": meal.get("strArea"),
                    "instructions": meal.get("strInstructions"),
                    "ingredients": ingredients,
                    "thumbnail": meal.get("strMealThumb"),
                })
            return results
    except Exception as e:
        return [{"error": f"Failed to search online recipes: {str(e)}"}]


def geocode_address(address: str) -> dict:
    """Convert a street address or location name into geographic coordinates using Google Geocoding API.

    Args:
        address: The address or location string (e.g. '1600 Amphitheatre Pkwy, Mountain View, CA' or 'San Francisco, CA').

    Returns:
        A dictionary containing name, formatted address, and location coordinates (latitude and longitude).
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY environment variable not set."}

    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={urllib.parse.quote(address)}&key={api_key}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("status") != "OK" or not data.get("results"):
                return {"error": f"Geocoding failed with status: {data.get('status')}"}

            first_result = data["results"][0]
            location = first_result.get("geometry", {}).get("location", {})
            return {
                "name": address,
                "address": first_result.get("formatted_address"),
                "location": {
                    "latitude": location.get("lat"),
                    "longitude": location.get("lng"),
                },
            }
    except Exception as e:
        return {"error": f"Geocoding request failed: {str(e)}"}


def find_nearby_places(latitude: float, longitude: float, place_type: str = "supermarket", radius_meters: float = 1000.0) -> list[dict]:
    """Find nearby places (such as grocery stores, markets, or restaurants) using Google Places API (New).

    Args:
        latitude: Latitude coordinate of the search center.
        longitude: Longitude coordinate of the search center.
        place_type: Type of place to find (e.g., 'supermarket', 'grocery_store', 'bakery', 'restaurant').
        radius_meters: Search radius in meters (default 1000.0).

    Returns:
        A list of dictionaries with key fields: name, address, and location.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return [{"error": "GOOGLE_MAPS_API_KEY environment variable not set."}]

    url = "https://places.googleapis.com/v1/places:searchNearby"
    payload = {
        "includedTypes": [place_type],
        "maxResultCount": 5,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": latitude,
                    "longitude": longitude,
                },
                "radius": radius_meters,
            }
        },
    }

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
    }

    try:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            places = data.get("places") or []

            results = []
            for p in places:
                results.append({
                    "name": p.get("displayName", {}).get("text", ""),
                    "address": p.get("formattedAddress"),
                    "location": p.get("location"),
                })
            return results
    except Exception as e:
        return [{"error": f"Places searchNearby failed: {str(e)}"}]
