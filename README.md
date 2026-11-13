# FLARE AI — Microgravity Combustion & Hybrid Knowledge Platform

**NASA Space Apps Challenge 2026 | Flame in Freefall**  
*Expanded Data Strategy & Hybrid Knowledge Architecture (PostgreSQL + pgvector + FastAPI + Next.js + Plotly)*

> **Scientific & Product Guardrail:** FLARE AI is a scientific research and decision-support prototype, **not** a certified spacecraft fire-safety system. Similarity scores represent closeness of experimental conditions within compatible combustion domains—never ignition probability, fire-risk probability, or predictions of lunar/Martian fire behavior.

---

## 1. Architecture Overview (Hybrid Knowledge & Structured Data Pipeline)

```text
                       Data Sources (P0 / P1 / P2)
       NASA PSI (PSI-25, 98, 101, 102, 107, 69) · JAXA DARTS · UL FSRI MaP
                                    │
                  ┌─────────────────┴─────────────────┐
                  ▼                                   ▼
       Knowledge Pipeline                  Structured Data Pipeline
  PDF / DOC / Scientific Reports           CSV / JSON Raw Files (SHA-256)
  → Extraction → Chunking                  → Cleaning → Unit Normalization
                  │                                   │
                  ▼                                   ▼
          Knowledge Base                         PostgreSQL
   Embeddings (pgvector), Chunks,        Experiments, Measurements, Metadata,
       DOIs, Source Citations               Field Mappings, Derived Results
                  │                                   │
                  └─────────────────┬─────────────────┘
                                    ▼
                            Hybrid Retrieval
             Semantic Search + Keyword Search + SQL Queries
             Domain Gate + Gravity Regime + Fuel Context
                                    │
                                    ▼
                           FLARE AI Interface
      Experiment Explorer · Comparison Dashboard · Hybrid RAG Assistant
```

---

## 2. Verified Dataset Inventory

| Priority | Dataset / Investigation | Environment | Domain | Official Source / DOI |
| :--- | :--- | :--- | :--- | :--- |
| **P0** | **NASA PSI-25 — BASS-II** | ISS Microgravity | `solid` | DOI `10.60555/4qc4-de67` |
| **P0** | **NASA PSI-98 — SAFFIRE-I** | Cygnus Microgravity | `solid` | DOI `10.60555/0t15-1z43` |
| **P0** | **NASA PSI-101 — SAME-R** | ISS Microgravity | `aerosol_smoke` | DOI `10.60555/2np7-jv14` |
| **P0** | **NASA PSI-102 — SAME** | ISS Microgravity | `aerosol_smoke` | DOI `10.60555/gd4k-8h62` |
| **P0** | **NASA PSI-107 — SPICE** | ISS Microgravity + 1g Analog | `gas` | DOI `10.60555/9kbh-e962` |
| **P1** | **NASA PSI-69 — FLEX** | ISS CIR Microgravity | `liquid_droplet` | DOI `10.60555/mbq8-0451` |
| **P1** | **JAXA DARTS — Kibo Group Combustion** | ISS Kibo Microgravity | `liquid_droplet` | `https://darts.isas.jaxa.jp/en/datasets/kibo-pm-combusion-gc` |
| **P2** | **FSRI Materials & Products (MaP)** | Earth 1g Baseline Track | `solid` | `https://materials.fsri.org/` *(Strictly isolated from 0g rankings)* |

---

## 3. API Endpoints

- `GET /api/health` — System status, controlled vocabularies, and database record counts
- `GET /api/sources` — List registered publishers (`NASA PSI`, `JAXA DARTS`, `UL FSRI`) and field mappings
- `GET /api/investigations?source=&domain=&gravity=&priority=&search=` — Filter investigations
- `GET /api/investigations/{id}` — Full investigation metadata, source files, and runs
- `GET /api/investigations/{id}/files` — Source files with SHA-256 checksums and versions
- `POST /api/ingestion/jobs` — Execute the 7-stage ingestion workflow (`Discover -> Acquire -> Parse -> Normalize -> Validate -> Publish -> Audit`)
- `GET /api/experiments/{id}/measurements` — Return measurements with original and canonical normalized units + explicit `missing_reason`
- `POST /api/compare` — Run domain-gated, explainable similarity ranking ($D(S, E_i) = \sqrt{w_1(\Delta O_2)^2 + w_2(\Delta P)^2 + w_3(\Delta V_{\text{air}})^2}$)
- `GET /api/provenance/{record_id}` — Full provenance chain (DOI, source URL, SHA-256 checksum, unit transformations, derived audit trail)
- `POST /api/assistant/query` — Hybrid Retrieval (`Semantic Vector + Keyword + PostgreSQL SQL + Grounded Synthesis`) separating **Published Scientific Evidence** from **Generated Interpretation**

---

## 4. Quick Start

### Backend (FastAPI + Python)
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Run Automated Acceptance Checklist Tests
```bash
PYTHONPATH=backend python backend/tests/test_flare_api.py
```

### Frontend (Next.js + TypeScript + Tailwind CSS)
```bash
cd frontend
npm install
npm run dev
```

### Optional PostgreSQL + `pgvector` via Docker Compose
```bash
docker compose up -d
```
