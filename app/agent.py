# ruff: noqa
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

import json
import os
from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from app.a2ui_utils import a2ui_callback
from app.tools import (
    add_recipe,
    find_nearby_places,
    generate_dish_image,
    generate_recipe_image,
    generate_recipe_video,
    geocode_address,
    get_pantry_inventory,
    get_recipe,
    search_online_recipes,
    search_recipes,
    update_pantry_item,
)

# Load reasoning engine and sandbox from deployment_metadata.json
remote_engine_id = "projects/526468641419/locations/us-east1/reasoningEngines/4595252717638647808"
sandbox_id = "projects/526468641419/locations/us-east1/reasoningEngines/4595252717638647808/sandboxEnvironments/9137179121330159616"
MEMORY_BANK_ID = "4595252717638647808"

metadata_path = os.path.join(os.path.dirname(__file__), "..", "deployment_metadata.json")
if os.path.exists(metadata_path):
    try:
        with open(metadata_path, "r") as f:
            meta = json.load(f)
            if meta.get("remote_agent_runtime_id"):
                remote_engine_id = meta.get("remote_agent_runtime_id")
                MEMORY_BANK_ID = remote_engine_id.split("/")[-1]
    except Exception:
        pass

code_executor = AgentEngineSandboxCodeExecutor(
    sandbox_resource_name=sandbox_id,
    agent_engine_resource_name=remote_engine_id,
)

# WRITE: Callback to extract and save session facts & allergy information into Memory Bank after each turn
async def generate_memories_callback(callback_context: CallbackContext):
    await callback_context.add_session_to_memory()
    return None

# Memory Service Builder for redeploying to Agent Runtime
def memory_bank_service_builder():
    return VertexAiMemoryBankService(
        project="qwiklabs-gcp-01-7da9f962617c",
        location="us-east1",
        agent_engine_id=MEMORY_BANK_ID,
    )

memory_service = memory_bank_service_builder()

# Configure A2UI Schema Manager with version 0.8 and Basic Catalog
schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are Smart Recipe & Meal Concierge, a culinary AI assistant. "
        "Help home cooks discover recipes, manage pantry items, and plan meals based on personal dietary preferences and available ingredients. "
        "CRITICAL ALLERGY & MEMORY DIRECTIVE: Automatically remember, track, and strictly enforce all user allergies (e.g., peanuts, shellfish, dairy, gluten, tree nuts, eggs, soy) and dietary restrictions disclosed in current or past sessions. Preload user memories on every turn and filter out any recipes or ingredients that violate known user allergies."
    ),
    workflow_description=(
        "Analyze the user request and database tool outputs. Return structured UI cards when presenting recipes, pantry stock, locations, or food items, and plain text when answering simple clarifying questions. "
        "Use your database tools to search for local recipes, search online recipes via global databases, retrieve recipe details, add new recipes, inspect or update pantry stock, generate visual food images using gemini-3.1-flash-lite-image published to Cloud Storage and Playground artifacts, geocode addresses to coordinates, search for nearby grocery stores or food markets, and execute Python code safely in your AgentEngine sandbox."
    ),
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    code_executor=code_executor,
    tools=[
        PreloadMemoryTool(),
        search_recipes,
        search_online_recipes,
        get_recipe,
        add_recipe,
        get_pantry_inventory,
        update_pantry_item,
        generate_recipe_image,
        generate_dish_image,
        generate_recipe_video,
        geocode_address,
        find_nearby_places,
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
