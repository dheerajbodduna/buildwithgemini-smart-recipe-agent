# Smart Recipe & Meal Concierge 🍳🤖

An intelligent culinary AI agent built with **Google ADK (Agent Development Kit)**, **Gemini 2.5 & 3.1 models**, and **Google Cloud Services**. The agent helps home cooks discover recipes, track pantry stock, generate dish visual media, find nearby food markets, and enforce strict dietary & allergy safeguards.

![Smart Recipe Agent Demo](demo.gif)

---

## 🌟 Capabilities & Tools

The agent implements the following tools and integrations:

### 📖 Recipe & Database Management (Cloud Firestore)
- **`search_recipes`**: Searches local recipe collections stored in Firestore by query string or prep time constraints.
- **`get_recipe`**: Retrieves full recipe details (ingredients, step-by-step instructions, prep time, difficulty, dietary tags).
- **`add_recipe`**: Adds new custom user recipes directly into Firestore database collections.
- **`search_online_recipes`**: Queries external global recipe databases (TheMealDB API) for worldwide culinary discovery.

### 🥫 Pantry Inventory Management (Cloud Firestore)
- **`get_pantry_inventory`**: Fetches real-time ingredient quantities and expiration dates stored in Firestore.
- **`update_pantry_item`**: Adds or updates ingredient stock levels in the user's pantry.

### 🎨 Visual Media Generation (Gemini & Cloud Storage)
- **`generate_dish_image` / `generate_recipe_image`**: Generates high-quality food photography using `gemini-3.1-flash-lite-image` in the `global` region, saves artifacts, and uploads public images directly to Google Cloud Storage (`smart-recipe-media-*`).
- **`generate_recipe_video`**: Generates short cooking video clips using `gemini-omni-flash-preview` in the `global` region, saving artifacts to the ADK Playground and publishing MP4 videos to Cloud Storage.

### 📍 Maps & Geolocation (Google Maps API)
- **`geocode_address`**: Converts street addresses or location names into latitude and longitude coordinates.
- **`find_nearby_places`**: Locates nearby grocery stores, farmers markets, and food shops using the Google Maps Places API.

### 🧠 Persistent Session Memory (Vertex AI Memory Bank)
- **`PreloadMemoryTool` & `VertexAiMemoryBankService`**: Automatically extracts, persists, and preloads user facts, dietary restrictions, and food allergies across chat turns and sessions.

### 💻 Secure Code Execution
- **`AgentEngineSandboxCodeExecutor`**: Safely executes Python code snippets in an isolated Agent Engine sandbox environment.

### 🎨 Adaptive User Interface (A2UI v0.8)
- **A2UI Card Renderer**: Generates structured v0.8 A2UI JSON components (`Card`, `Column`, `Row`, `Text`, `Image`) with customized CSS pill badges for prep time, difficulty, calories, and dietary tags.

---

## 🏗 Project Architecture

```
smart-recipe-agent/
├── app/
│   ├── agent.py            # Agent definition, system prompt, Memory Bank, & tool registry
│   ├── tools.py            # Firestore, Media Generation, Maps, & Search tool implementations
│   └── a2ui_utils.py       # A2UI response transformation callbacks
├── frontend/
│   ├── main.py             # FastAPI proxy backend connecting to Agent Engine
│   └── static/
│       └── index.html      # Glassmorphic chat interface & A2UI card renderer
├── agents-cli-manifest.yaml # Agent Platform configuration & deployment manifest
├── deployment_metadata.json # Runtime resource references
└── demo.gif                # Embedded recorded application demonstration
```

---

## 🚀 Setup & Local Execution

### 1. Prerequisites & Environment Setup

Install dependencies using `uv` or `pip`:

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

Set required environment variables:

```bash
export GOOGLE_CLOUD_PROJECT="<your-gcp-project-id>"
export GOOGLE_MAPS_API_KEY="<your-google-maps-api-key>"
```

### 2. Running the Frontend Locally

Navigate to the `frontend/` directory, set environment variables pointing to your deployed Agent Engine resource name and agent directory, then start the FastAPI proxy server:

```bash
cd frontend
export AGENT_ENGINE_RESOURCE_NAME="projects/<project-number>/locations/us-east1/reasoningEngines/<engine-id>"
export AGENT_DIRECTORY="app"
export PORT=8080

uv run python main.py
```

Open your web browser and navigate to port `8080` on your host machine to interact with the agent.

---

## ☁️ Deployment Instructions

### Deploying the Agent to Agent Platform

Deploy or update the agent on Agent Platform using `agents-cli`:

```bash
agents-cli deploy --no-confirm-project --update-env-vars GOOGLE_MAPS_API_KEY=YOUR_MAPS_API_KEY
```

### Deploying the Frontend to Cloud Run

Deploy the web interface to Google Cloud Run:

```bash
gcloud run deploy smart-recipe-frontend \
  --source ./frontend \
  --region us-east1 \
  --allow-unauthenticated \
  --set-env-vars AGENT_ENGINE_RESOURCE_NAME="projects/<project-number>/locations/us-east1/reasoningEngines/<engine-id>",AGENT_DIRECTORY="app"
```

Grant the Cloud Run service account access to invoke Vertex AI Agent Engine:

```bash
gcloud projects add-iam-policy-binding <your-gcp-project-id> \
  --member="serviceAccount:<project-number>-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```
