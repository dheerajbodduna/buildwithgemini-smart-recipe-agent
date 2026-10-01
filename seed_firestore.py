#!/usr/bin/env python3
# Copyright 2026 Google LLC
# Seed script for Smart Recipe Agent Firestore collections.

import time
import subprocess
import google.auth
import google.oauth2.credentials
from google.cloud import firestore

# Hardcoded GCP Project ID for Agent Platform compatibility
GCP_PROJECT_ID = "qwiklabs-gcp-01-7da9f962617c"


def get_credentials():
    try:
        token = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()
        if token:
            return google.oauth2.credentials.Credentials(token)
    except Exception:
        pass
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    return creds


def set_doc_with_retry(doc_ref, data, max_attempts=5):
    for attempt in range(max_attempts):
        try:
            doc_ref.set(data, merge=True)
            return
        except Exception as e:
            if attempt == max_attempts - 1:
                raise e
            time.sleep(1)


def seed():
    print(f"Connecting to Firestore for project: {GCP_PROJECT_ID}...")
    creds = get_credentials()
    db = firestore.Client(project=GCP_PROJECT_ID, credentials=creds)

    # 1. Seed Recipes
    recipes = [
        {
            "id": "mediterranean_quinoa_bowl",
            "title": "Mediterranean Quinoa Bowl",
            "cuisine": "Mediterranean",
            "prep_time_minutes": 20,
            "dietary_tags": ["vegan", "gluten-free", "healthy"],
            "ingredients": [
                "1 cup quinoa",
                "1 cup cherry tomatoes, halved",
                "1 cucumber, diced",
                "1/2 cup kalamata olives",
                "2 tbsp extra virgin olive oil",
                "1 tbsp lemon juice",
                "Salt and black pepper to taste",
            ],
            "instructions": "Rinse quinoa and cook in 2 cups water for 15 minutes. Fluff with a fork, combine with tomatoes, cucumber, and olives. Toss with olive oil, lemon juice, salt, and pepper.",
        },
        {
            "id": "avocado_chickpea_salad",
            "title": "Avocado Chickpea Power Salad",
            "cuisine": "American",
            "prep_time_minutes": 15,
            "dietary_tags": ["vegan", "gluten-free", "quick"],
            "ingredients": [
                "1 can (15 oz) chickpeas, rinsed and drained",
                "2 ripe avocados, diced",
                "1/4 cup red onion, finely chopped",
                "1/4 cup fresh cilantro, chopped",
                "2 tbsp lime juice",
                "1 tbsp olive oil",
            ],
            "instructions": "In a large bowl, mash half the avocado. Add chickpeas, remaining diced avocado, red onion, and cilantro. Drizzle with lime juice and olive oil, then gently toss.",
        },
        {
            "id": "creamy_tuscan_garlic_pasta",
            "title": "Creamy Tuscan Garlic Pasta",
            "cuisine": "Italian",
            "prep_time_minutes": 25,
            "dietary_tags": ["vegetarian"],
            "ingredients": [
                "8 oz fettuccine pasta",
                "2 tbsp butter",
                "4 cloves garlic, minced",
                "1/2 cup sun-dried tomatoes",
                "2 cups fresh spinach",
                "1 cup heavy cream",
                "1/2 cup grated parmesan cheese",
            ],
            "instructions": "Cook pasta according to package instructions. In a skillet, melt butter and sauté garlic for 1 minute. Add sun-dried tomatoes and spinach until wilted. Stir in heavy cream and parmesan until thick and smooth. Toss with cooked pasta.",
        },
    ]

    print("Seeding 'recipes' collection...")
    for recipe in recipes:
        doc_id = recipe.pop("id")
        doc_ref = db.collection("recipes").document(doc_id)
        set_doc_with_retry(doc_ref, recipe)
        print(f"  ✓ Added recipe: {doc_id} ({recipe['title']})")

    # 2. Seed Pantry Items
    pantry_items = [
        {"id": "quinoa", "name": "Quinoa", "quantity": 2.0, "unit": "cups", "category": "Grains"},
        {"id": "cherry_tomatoes", "name": "Cherry Tomatoes", "quantity": 2.0, "unit": "cups", "category": "Produce"},
        {"id": "chickpeas", "name": "Chickpeas (Canned)", "quantity": 4.0, "unit": "cans", "category": "Canned Goods"},
        {"id": "avocado", "name": "Avocado", "quantity": 3.0, "unit": "units", "category": "Produce"},
        {"id": "olive_oil", "name": "Extra Virgin Olive Oil", "quantity": 500.0, "unit": "ml", "category": "Pantry"},
        {"id": "garlic", "name": "Garlic", "quantity": 1.0, "unit": "head", "category": "Produce"},
        {"id": "spinach", "name": "Fresh Spinach", "quantity": 1.0, "unit": "bag", "category": "Produce"},
    ]

    print("Seeding 'pantry' collection...")
    for item in pantry_items:
        doc_id = item.pop("id")
        doc_ref = db.collection("pantry").document(doc_id)
        set_doc_with_retry(doc_ref, item)
        print(f"  ✓ Added pantry item: {doc_id} ({item['name']})")

    print("\n🎉 Firestore seeding complete!")


if __name__ == "__main__":
    seed()
