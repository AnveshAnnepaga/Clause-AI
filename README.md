---
title: Clause AI Agent
emoji: ⚖️
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---
# ClauseAI — Multi-Agent Contract Intelligence

AI-powered contract analysis using Retrieval-Augmented Generation (RAG), multi-agent architecture, and vector-based memory.

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![Pinecone](https://img.shields.io/badge/Pinecone-Vector%20DB-green)](https://www.pinecone.io/)
[![Transformers](https://img.shields.io/badge/HuggingFace-Transformers-orange)](https://huggingface.co/transformers/)

---

## 🚀 Overview

ClauseAI automates legal contract review using LLMs, semantic search, and domain-specialized AI agents.  

It transforms raw contracts into structured, risk-scored, and explainable insights.

### Key Features

- Vector-based semantic search (Pinecone)
- Multi-agent system (Legal, Compliance, Finance, Operations)
- Parallel async execution (3–4x faster)
- Persistent agent memory for instant recall
- Structured JSON risk reports
- FastAPI backend + Streamlit UI

---

## 🧠 Multi-Agent System

ClauseAI uses four specialized agents:

- **Legal** – Termination, breach, indemnification
- **Compliance** – Regulatory, privacy, audit risks
- **Finance** – Fees, penalties, liability caps
- **Operations** – SLAs, deliverables, timelines

Each agent retrieves relevant clauses, assigns risk levels (LOW / MEDIUM / HIGH), and provides confidence scores with supporting evidence.

---

## 🏗 Tech Stack

- Python 3.8+
- FastAPI
- Streamlit
- Pinecone (Vector DB)
- Sentence-Transformers
- HuggingFace Transformers
- LangChain / LangGraph
- AsyncIO

---

## ⚙️ Setup

### Clone Repository

```bash
git clone https://github.com/your-username/Clause-AI.git
cd Clause-AI
```
##### Install Dependencies

```bash 
pip install -r requirements.txt
```
##### Configure Environment
Create a .env file:
```bash
PINECONE_API_KEY=your_key
PINECONE_INDEX=cuad-index
HF_TOKEN=your_token
```

## ▶️ Run Application

#### Start Backend
 ```bash
 cd backend
 uvicorn app:app --reload --port 8000
```
#### Start UI
```bash
cd frontend
streamlit run app.py
```