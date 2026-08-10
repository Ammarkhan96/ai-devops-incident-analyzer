# 🤖 AI DevOps Incident Analyzer

An AI-powered DevOps incident analysis system that automatically monitors application logs, detects failures, and uses a local Ollama LLM to analyze incidents.

The system identifies incident severity, root cause, evidence, and recommended remediation actions.

---

## 🚀 Features

- 🔍 Automatic application log monitoring
- 🤖 AI-powered incident analysis using Ollama
- 🧠 Local LLM inference with `llama3.2:1b`
- 🚨 Automatic incident detection
- 📊 Incident severity classification
- 🔎 Root-cause analysis
- 🛠️ Recommended remediation actions
- 🐳 Docker & Docker Compose
- ⚡ FastAPI REST APIs
- 📈 Prometheus metrics
- ❤️ Health checks
- 🧪 Automated tests with Pytest
- 🔄 Fallback analysis when AI is unavailable

---

## 🏗️ Architecture

```text
                    ┌─────────────────────┐
                    │    Demo Application │
                    │      FastAPI        │
                    └──────────┬──────────┘
                               │
                               │ Application Logs
                               ▼
                    ┌─────────────────────┐
                    │   Shared Log File   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ AI Incident Analyzer│
                    │      FastAPI        │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │       Ollama        │
                    │    llama3.2:1b      │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Incident Analysis   │
                    │                     │
                    │ Severity             │
                    │ Root Cause           │
                    │ Evidence             │
                    │ Remediation          │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ JSON Incident Store │
                    └─────────────────────┘
