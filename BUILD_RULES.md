# VAYUNET BUILD RULES & SYSTEM CONSTRAINTS

> **Status:** LOCKED & ACTIVE  
> These architectural rules and engineering constraints are mandatory across all backend, frontend, ML, and agent implementations.

---

## 1. Role Separation: Gemini vs. Event Engine
- **Gemini's Role:** Interprets multimodal evidence (photo, text, voice) into structured JSON, formulates source hypotheses, and generates plain-language, evidence-cited risk explanations.
- **Deterministic Boundary:** Gemini **never** calculates or overrides the final event confidence score or the risk level. 
- Scoring and classification must remain strictly auditable, deterministic, and executed by the Pollution Event Engine.

---

## 2. Event Confidence Scoring Formula
- The event confidence calculation is **frozen** to the `weighted_fusion_v1` specification:
  $$\text{event\_confidence} = 0.35 \times \text{sensor} + 0.30 \times \text{gemini} + 0.20 \times \text{weather} + 0.15 \times \text{satellite}$$
- Every calculation must be tagged with method: `"weighted_fusion_v1"`.
- Confidence tiers:
  - `< 0.40`: **LOW** (logged only)
  - `0.40 – 0.70`: **MODERATE** (shown on authority dashboard)
  - `> 0.70`: **HIGH** (triggers priority authority alert)

---

## 3. Anti-Abuse & Corroboration Guardrail
- **Citizen Evidence Ceiling:** Citizen evidence alone can **never** push the overall event confidence score above **0.70**.
- Corroboration from ground sensors or satellite signals is **mandatory** for an event to qualify as `HIGH` confidence or trigger critical alerts.
- This prevents spam or fabricated photos from generating false public alarms.

---

## 4. Strict Free-Tier Infrastructure
- **Zero Paid Services:** Strictly **no** paid Google Cloud or third-party services (No Vertex AI, Cloud Run, BigQuery, Google Maps Platform paid tiers, etc.).
- **Approved Stack Only:**
  - **Gemini API:** Free tier via Google AI Studio key (`google-genai` SDK).
  - **Google Earth Engine:** Free non-commercial / educational tier.
  - **Firebase:** Spark plan (free tier Firestore, Auth, Hosting).
  - **Mapping:** Open-source Leaflet.js + OpenStreetMap tiles.
  - **Forecasting & Federated ML:** Local Python (XGBoost, scikit-learn, Flower `flwr`).
  - **Automation:** Self-hosted n8n via Docker.

---

## 5. Security & Secret Management
- **No Hardcoded Secrets:** API keys, database credentials, tokens, or endpoints must **never** be committed to source control or hardcoded in any file.
- All secrets must be loaded dynamically through environment variables via `.env` files.
- `.env` files must remain strictly ignored in `.gitignore`. Provide documented template keys in `.env.example`.
