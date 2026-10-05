# AI Analytics Copilot

Enterprise AI-powered Analytics Assistant for large-scale datasets.

AI Analytics Copilot enables business users, analysts, and decision-makers to ask natural language questions about enterprise data and receive deep analytical insights powered by Large Language Models (LLMs), Retrieval-Augmented Generation (RAG), and intelligent SQL generation.

---

## Overview

Modern enterprises generate massive volumes of data, making it difficult for business users to extract insights quickly.

AI Analytics Copilot bridges this gap by combining:

- Amazon Redshift
- OpenAI / Azure OpenAI
- LangChain
- Vector Databases (FAISS / ChromaDB)
- Streamlit

to create an intelligent analytics assistant capable of:

- Answering business questions
- Performing root cause analysis
- Generating executive summaries
- Identifying trends and anomalies
- Providing recommendations
- Generating SQL dynamically

---

## Key Features

### Data Connectivity

- Amazon Redshift Integration
- Schema Discovery
- Metadata Extraction
- Data Profiling

### AI Analytics

- Natural Language Querying
- Executive Summaries
- Trend Analysis
- KPI Analysis
- Root Cause Identification
- Business Recommendations

### Intelligent Retrieval

- LangChain Integration
- RAG Architecture
- Vector Database Search
- Metadata Retrieval

### Chat Experience

- Streamlit Chat Interface
- Conversational Analytics
- Context-Aware Responses

### Enterprise Security

- Credentials stored securely
- No database passwords exposed in UI
- Support for Secrets Management
- Read-only analytics access

---

## Architecture

```text
+------------------+
| Streamlit UI     |
+------------------+
          |
          v
+------------------+
| LangChain Agent  |
+------------------+
      |        |
      |        |
      v        v

+------------------+       +------------------+
| Vector Database  |       | SQL Generator    |
| FAISS/ChromaDB   |       +------------------+
+------------------+                 |
                                    v
                           +------------------+
                           | Amazon Redshift  |
                           +------------------+

                                    |
                                    v

                           +------------------+
                           | GPT-4o / GPT-5   |
                           +------------------+

                                    |
                                    v

                           +------------------+
                           | Business Insights|
                           +------------------+
```

---

## Technology Stack

### Frontend

- Streamlit

### Backend

- Python

### Database

- Amazon Redshift

### AI

- OpenAI
- Azure OpenAI
- LangChain

### Vector Databases

- FAISS
- ChromaDB

### Analytics

- Pandas
- Polars
- DuckDB

---

## Project Structure

```text
AI_Analytics_Copilot
│
├── app.py
│
├── config/
│   ├── settings.py
│   └── prompts.py
│
├── database/
│   ├── redshift_service.py
│   ├── query_executor.py
│   └── schema_extractor.py
│
├── llm/
│   ├── llm_service.py
│   ├── rag_pipeline.py
│   ├── sql_generator.py
│   └── insight_generator.py
│
├── vectorstore/
│   ├── embeddings.py
│   ├── faiss_manager.py
│   └── metadata_index.py
│
├── analytics/
│   ├── profiler.py
│   ├── anomaly_detector.py
│   ├── trend_analyzer.py
│   └── kpi_generator.py
│
├── ui/
│   ├── sidebar.py
│   ├── chat_page.py
│   ├── data_profile.py
│   └── settings_page.py
│
├── cache/
├── logs/
│
├── .streamlit/
│   └── secrets.toml
│
├── requirements.txt
├── README.md
└── .gitignore
```

---

## Installation

### Clone Repository

```bash
git clone https://github.com/<your-org>/AI_Analytics_Copilot.git

cd AI_Analytics_Copilot
```

### Create Virtual Environment

```bash
python -m venv .venv
```

### Activate Environment

Windows

```bash
.venv\Scripts\activate
```

Linux/Mac

```bash
source .venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Configuration

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

OPENAI_API_KEY="your-key"
```

### Important

- Never commit secrets to GitHub.
- Add secrets files to `.gitignore`.
- Use service accounts whenever possible.

---

## Running the Application

```bash
streamlit run app.py
```

Application URL:

```text
http://localhost:8501
```

---

## Typical User Workflow

### Step 1

Connect to Redshift metadata.

### Step 2

Load schema information.

### Step 3

Ask questions.

Examples:

```text
Which products have declining sales trends?
```

```text
Identify regions contributing most to revenue growth.
```

```text
What are the top customer churn drivers?
```

```text
Provide executive summary for last quarter performance.
```

---

## Example Analytics Questions

### Executive Insights

```text
Summarize the overall business performance.
```

```text
What are the most important trends?
```

### Sales Analytics

```text
Why are sales declining in APAC?
```

```text
Which products show highest growth?
```

### Customer Analytics

```text
Identify high-value customer segments.
```

```text
Analyze churn behavior.
```

### Operations Analytics

```text
What factors influence call quality?
```

```text
Identify operational bottlenecks.
```

---

## Future Roadmap

### Phase 1

- Streamlit UI
- Redshift Integration
- Metadata Extraction
- Chat Interface

### Phase 2

- LangChain
- RAG
- FAISS
- ChromaDB

### Phase 3

- Text-to-SQL Engine
- SQL Validation
- Query Optimization

### Phase 4

- Dashboard Generation
- Chart Generation
- Plotly Visualizations

### Phase 5

- Multi-Agent AI
- Forecasting
- Predictive Analytics
- Automated Insights
- Root Cause Analysis

---

## Security Guidelines

### Recommended

✅ Store credentials in Secrets Manager

✅ Use Read-Only Database Access

✅ Enable Audit Logging

✅ Use Corporate SSO

✅ Restrict Network Access

### Avoid

❌ Hardcoded passwords

❌ User-entered database credentials

❌ Direct production table access

❌ Unlimited SQL execution

---

## Author

**Raghavender Goud Palem**

Consultant - AI & Data Science

Enterprise Analytics & AI Solutions

---

## Vision

Transform enterprise data into actionable intelligence through conversational AI, advanced analytics, and intelligent decision support.