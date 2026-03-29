# ProcureNow — RFP Compliance Auditor

ProcureNow is a high-end, AI-powered platform designed to automate the compliance auditing of construction proposals against Request for Proposal (RFP) requirements. Using a 4-phase multimodal pipeline driven by Google Gemini AI, it identifies compliance gaps, evaluates risk factors, and provides a structured audit report with high precision.

## 🚀 Features

- **Multimodal PDF Ingestion**: Processes complex documents (tables, charts, grids) using Gemini Vision to ensure no data is missed.
- **Dynamic RFP Rubric Extraction**: Automatically identifies and extracts requirements from the RFP to build a custom compliance rubric.
- **Section-Routed Audit**: Semantically routes requirements to the relevant sections of the proposal for accurate presence and accuracy evaluation.
- **Interactive Dashboard**: A professional, data-dense interface for visualizing overall compliance, critical focus areas, and detailed requirement status.
- **Evidence Viewer**: A side-by-side viewer that allows users to verify AI-extracted findings directly against the source proposal PDF.
- **Branded Exports**: Generate professional PDF audit reports or export results to CSV for further analysis.

## 🛠 Tech Stack

- **Backend**: [FastAPI](https://fastapi.tiangolo.com/), [Uvicorn](https://www.uvicorn.org/), Python 3.11+
- **AI/LLM**: [Google Gemini Pro](https://deepmind.google/technologies/gemini/) (Multimodal)
- **PDF Engine**: [PyMuPDF (fitz)](https://pymupdf.readthedocs.io/), [fpdf2](https://pyfpdf.github.io/fpdf2/)
- **Frontend**: Vanilla JavaScript (ES6+), Modern CSS (Flexible Layout, Glassmorphism), Semantic HTML5
- **Database**: SQLite (via standard Python library)

## 📂 Project Structure

```text
ProcureNow/
├── backend/                # FastAPI application logic
│   ├── auditor.py          # Core compliance auditing logic
│   ├── extractor.py        # RFP requirement extraction
│   ├── server.py           # Entry point and API routes
│   └── ...                 # Helpers (PDF reading, database, reporting)
├── frontend/               # Static dashboard files
│   ├── index.html          # Main dashboard structure
│   ├── app.js              # Frontend logic and API integration
│   └── index.css           # Styling (Forest & Lime theme)
├── data/                   # Local database storage
├── design-system.md        # Detailed Design Tokens and UI/UX rules
├── requirements.txt        # Python dependencies
└── .env                    # Environment variables (API Keys)
```

## ⚙️ Setup & Installation

### 1. Prerequisites
- Python 3.11 or higher installed on your system.
- A Google Gemini API Key (available via [Google AI Studio](https://aistudio.google.com/)).

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
Create a `.env` file in the root directory (or update the existing one):
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

## 🏃‍♂️ How to Run

Start the server using the following command:

```bash
python3 -m backend.server
```

Once the server is running, access the dashboard at:
👉 **[http://localhost:8000](http://localhost:8000)**

## 🎨 Design System
The project follows a strict brand guideline defined in [design-system.md](./design-system.md). It utilizes a professional **Forest Green** and **Lime** palette, prioritizing readability, data density, and a "No-Line" visual philosophy.
