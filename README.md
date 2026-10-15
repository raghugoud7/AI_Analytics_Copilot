# AI Analytics Copilot

Enterprise AI-powered Analytics Assistant for Amazon Redshift datasets.

AI Analytics Copilot enables business users, analysts, and decision-makers to interact with enterprise data using natural language and receive intelligent insights, automated analytics, visualizations, and privacy-aware data exploration powered by Generative AI.

---

# Overview

Modern enterprises generate massive volumes of structured and semi-structured data, making it difficult for users to extract meaningful insights quickly.

AI Analytics Copilot bridges this gap by combining:

- Amazon Redshift
- Azure OpenAI / OpenAI
- Streamlit
- FAISS Vector Search
- Metadata Intelligence
- Multi-Agent AI Architecture
- Privacy-Aware Analytics

The platform allows users to:

- Explore datasets without writing SQL
- Ask business questions in natural language
- Generate SQL automatically
- Visualize data instantly
- Perform advanced analytics
- Detect trends and anomalies
- Generate executive summaries
- Protect sensitive information using privacy controls
- Load full datasets when deeper analysis is required

---

# Key Features

## Data Connectivity

- Amazon Redshift Integration
- Dynamic Schema Discovery
- Column Metadata Extraction
- Brand-Level Data Loading
- Metadata Profiling

---

## Conversational Analytics

- Natural Language Querying
- Business Question Answering
- Metadata Intelligence
- Executive Summaries
- Automated Recommendations
- Root Cause Analysis

---

## AI-Powered SQL Generation

- Text-to-SQL Generation
- SQL Validation
- Schema-Aware Query Generation
- Brand-Level Query Enforcement
- Privacy-Aware SQL Execution

---

## Visualization Intelligence

- Automatic Chart Generation
- Plotly Visualizations
- Bar Charts
- Line Charts
- Area Charts
- Scatter Plots
- Histograms
- Box Plots
- Pie Charts

---

## Advanced Analytics

- Data Profiling
- Executive Summary
- KPI Analysis
- Segment Analysis
- Trend Analysis
- Correlation Analysis
- Outlier Detection
- Driver Analysis

---

## Privacy & Governance

- Dynamic PII Detection
- Privacy Inspection Workflow
- Privacy Policy Builder
- Mandatory Sensitive Field Exclusions
- Optional User-Controlled Exclusions
- Privacy-Aware Query Validation
- Result Sanitization

---

## Full Dataset Analytics

- Sample-Based Analysis
- Full Dataset Loading
- Brand-Specific Analytics
- Analysis Refresh Controls
- Memory-Aware Processing
- Privacy-Preserving Data Retrieval

---

## Metadata Intelligence

- Metadata Repository
- Schema Profiling
- Column Intelligence
- Vector Search
- Semantic Metadata Retrieval
- Dataset Understanding

---

# Architecture

```text
┌──────────────────────────────────────────────┐
│                 Streamlit UI                 │
│──────────────────────────────────────────────│
│ Data Overview                                │
│ Data Analysis                                │
│ Data Quality                                 │
│ Chat Analytics                               │
│ Privacy Controls                             │
│ Full Data Controls                           │
└──────────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────┐
│           Analytics Orchestrator             │
└──────────────────────────────────────────────┘
                        │
       ┌────────────────┼────────────────┐
       ▼                ▼                ▼

┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Metadata     │ │ SQL Agent    │ │ Visualization│
│ Agent        │ │              │ │ Agent        │
└──────────────┘ └──────────────┘ └──────────────┘
       │                │
       ▼                ▼

┌──────────────────────────────────────────────┐
│            Intent Router Agent               │
└──────────────────────────────────────────────┘
                        │
                        ▼

┌──────────────────────────────────────────────┐
│         Metadata Intelligence Layer          │
│──────────────────────────────────────────────│
│ Metadata Repository                          │
│ Metadata Profiling                           │
│ FAISS Retrieval                              │
│ Semantic Search                              │
└──────────────────────────────────────────────┘
                        │
                        ▼

┌──────────────────────────────────────────────┐
│            SQL Validator Agent               │
│──────────────────────────────────────────────│
│ Privacy Enforcement                          │
│ Brand Enforcement                            │
│ Query Validation                             │
│ Sensitive Column Protection                  │
└──────────────────────────────────────────────┘
                        │
                        ▼

┌──────────────────────────────────────────────┐
│              Amazon Redshift                 │
└──────────────────────────────────────────────┘
                        │
                        ▼

┌──────────────────────────────────────────────┐
│       Privacy & Governance Layer             │
│──────────────────────────────────────────────│
│ PII Detector                                 │
│ Privacy Policy Builder                       │
│ Dynamic Field Classification                 │
│ Sensitive Column Removal                     │
└──────────────────────────────────────────────┘
                        │
                        ▼

┌──────────────────────────────────────────────┐
│          Data Analysis Engine                │
│──────────────────────────────────────────────│
│ Data Profiling                               │
│ Executive Summary                            │
│ KPI Analysis                                 │
│ Segment Analysis                             │
│ Trend Analysis                               │
│ Correlation Analysis                         │
│ Outlier Detection                            │
│ Driver Analysis                              │
└──────────────────────────────────────────────┘
                        │
                        ▼

┌──────────────────────────────────────────────┐
│             GPT-5 / Azure OpenAI             │
└──────────────────────────────────────────────┘
                        │
                        ▼

┌──────────────────────────────────────────────┐
│    Insights, Visualizations & SQL Output     │
└──────────────────────────────────────────────┘
```

---

# Technology Stack

## Frontend

- Streamlit
- Plotly

---

## Backend

- Python 3.11+
- Pandas
- NumPy

---

## Database

- Amazon Redshift

---

## AI / LLM

- Azure OpenAI
- OpenAI GPT Models

---

## Retrieval

- FAISS
- Vector Embeddings
- Metadata Search

---

## Analytics

- Pandas
- Scikit-Learn
- SciPy

---

## Validation

- SQLGlot

---

## Optional Caching

- Redis

---

# Project Structure

```text
AI_Analytics_Copilot
│
├── app.py
│
├── agents/
│   ├── orchestrator.py
│   ├── general_agent.py
│   ├── metadata_agent.py
│   ├── metadata_insight_agent.py
│   ├── sql_agent.py
│   ├── sql_validator_agent.py
│   ├── visualization_agent.py
│   └── intent_router_agent.py
│
├── analytics/
│   ├── data_analysis_orchestrator.py
│   ├── profiling_analysis.py
│   ├── summary_analysis.py
│   ├── kpi_analysis.py
│   ├── segment_analysis.py
│   ├── trend_analysis.py
│   ├── correlation_analysis.py
│   ├── outlier_analysis.py
│   └── driver_analysis.py
│
├── cache/
│   └── redis_service.py
│
├── config/
│   ├── privacy.py
│   ├── settings.py
│   └── prompts.py
│
├── database/
│   ├── query_executor.py
│   ├── schema_extractor.py
│   └── redshift_service.py
│
├── llm/
│   └── llm_service.py
│
├── memory/
│   └── chat_memory.py
│
├── metadata/
│   ├── metadata_filter.py
│   ├── metadata_repository_builder.py
│   └── metadata_profiler_agent.py
│
├── prompts/
│   ├── metadata_prompt.py
│   ├── sql_prompt.py
│   └── insight_prompt.py
│
├── ui/
│   ├── summary_tab.py
│   ├── kpis_tab.py
│   ├── segment_tab.py
│   ├── trend_tab.py
│   ├── correlation_tab.py
│   ├── outliers_tab.py
│   ├── drivers_tab.py
│   ├── profiling_tab.py
│   ├── chat_visualization.py
│   └── full_data_controls.py
│
├── utils/
│   ├── privacy.py
│   ├── privacy_policy.py
│   ├── pii_detector.py
│   └── cache_utils.py
│
├── vectorstore/
│   ├── build_index.py
│   ├── embeddings.py
│   └── faiss_manager.py
│
├── requirements.txt
├── README.md
└── .streamlit/
    └── secrets.toml
```

---

# Installation

## Clone Repository

```bash
git clone https://github.com/<your-org>/AI_Analytics_Copilot.git

cd AI_Analytics_Copilot
```

---

## Create Virtual Environment

```bash
python -m venv .venv
```

---

## Activate Environment

### Windows

```bash
.venv\Scripts\activate
```

### Linux / Mac

```bash
source .venv/bin/activate
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

# Configuration

Create:

```text
.streamlit/secrets.toml
```

Example:

```toml
REDSHIFT_HOST="your-host"
REDSHIFT_PORT="5439"
REDSHIFT_DB="your-database"
REDSHIFT_USER="service-account"
REDSHIFT_PASSWORD="password"

AZURE_OPENAI_API_KEY="your-key"
AZURE_OPENAI_ENDPOINT="your-endpoint"
AZURE_OPENAI_DEPLOYMENT="gpt-5"
```

---

# Running The Application

```bash
streamlit run app.py
```

Application URL:

```text
http://localhost:8501
```

---

# Typical User Workflow

### Step 1

Fetch schema metadata and available brands.

### Step 2

Select a brand.

### Step 3

Run Privacy Inspection.

### Step 4

Review detected sensitive fields.

### Step 5

Apply Privacy Settings and Load Dataset.

### Step 6

Explore:

- Data Overview
- Data Analysis
- Data Quality

### Step 7

Ask questions using Chat Analytics.

### Step 8

Load Full Data if deeper analysis is required.

---

# Example Analytics Questions

## Business Insights

```text
Summarize overall business performance.
```

```text
What are the most important trends?
```

```text
Provide key recommendations based on this dataset.
```

---

## Quality Analytics

```text
What factors influence call quality?
```

```text
Which segments have the highest QA scores?
```

---

## Trend Analytics

```text
Show monthly QA score trends.
```

```text
Which brands are improving over time?
```

---

## Driver Analysis

```text
What variables drive overall QA score?
```

```text
Which features most strongly influence customer satisfaction?
```

---

## Visualization Requests

```text
Plot average QA score by language.
```

```text
Create a trend chart for call quality.
```

```text
Show a distribution of sentiment scores.
```

---

# Security Guidelines

## Recommended

✅ Use Read-Only Redshift Access

✅ Store Credentials in Secrets Manager

✅ Enable Audit Logging

✅ Restrict Network Access

✅ Apply Privacy Inspection Before Loading Data

✅ Use Mandatory Sensitive Data Exclusions

---

## Avoid

❌ Hardcoded Credentials

❌ Direct Production Write Access

❌ Exposing Sensitive Columns

❌ Unvalidated SQL Execution

❌ Sharing Secrets in Source Control

---

# Future Roadmap

## Completed ✅

- Amazon Redshift Integration
- Metadata Retrieval
- Text-to-SQL
- Metadata Intelligence
- Visualization Generation
- Privacy Controls
- Dynamic PII Detection
- SQL Validation
- Data Analysis Dashboard
- Full Dataset Loading
- Multi-Agent Architecture

---

## In Progress 🚧

- Semantic Response Caching
- Access-Aware Caching
- Enhanced Metadata Intelligence
- Performance Optimization
- Large Dataset Scaling

---

## Planned 📌

- Predictive Analytics
- Forecasting
- What-If Analysis
- Multi-Table Analytics
- Automated Alerting
- Scheduled Insights
- Role-Based Access Control

---

# Author

**Raghavender Goud Palem**

Consultant – AI & Data Science

Enterprise Analytics & AI Solutions

---

# Vision

Transform enterprise data into actionable intelligence through conversational AI, advanced analytics, privacy-aware governance, and intelligent decision support.