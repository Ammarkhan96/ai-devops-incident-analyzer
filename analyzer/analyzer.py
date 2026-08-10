import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests
from fastapi import FastAPI
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    generate_latest,
)
from starlette.responses import Response


# ============================================================
# CONFIGURATION
# ============================================================

LOG_FILE = os.getenv(
    "LOG_FILE",
    "/tmp/ai-devops-app.log",
)

# Docker:
#   INCIDENT_DIR=/incidents
#
# Local pytest:
#   /tmp/ai-devops-incidents
#
# This prevents PermissionError when running tests as a
# normal Linux user.
INCIDENT_DIR = Path(
    os.getenv(
        "INCIDENT_DIR",
        "/tmp/ai-devops-incidents",
    )
)

AI_ENABLED = os.getenv(
    "AI_ENABLED",
    "true",
).lower() == "true"

OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://host.docker.internal:11434",
).rstrip("/")

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "llama3.2:1b",
)

WEBHOOK_URL = os.getenv(
    "WEBHOOK_URL",
    "",
)

BATCH_SIZE = int(
    os.getenv(
        "ERROR_BATCH_SIZE",
        "3",
    )
)

POLL_INTERVAL = float(
    os.getenv(
        "POLL_INTERVAL",
        "2",
    )
)


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="AI DevOps Incident Analyzer",
    version="1.0.0",
)


# ============================================================
# PROMETHEUS METRICS
# ============================================================

logs_processed = Counter(
    "logs_processed_total",
    "Total log lines processed",
)

incidents_created = Counter(
    "incidents_created_total",
    "Total incidents created",
)

ai_requests = Counter(
    "ai_requests_total",
    "Total requests sent to Ollama",
)

ai_failures = Counter(
    "ai_failures_total",
    "Total failed AI requests",
)


# ============================================================
# DIRECTORIES
# ============================================================

INCIDENT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# AI PROMPT
# ============================================================

def build_prompt(logs):
    """
    Build a structured prompt for Ollama.
    """

    joined_logs = "\n".join(logs)

    return f"""
You are a senior DevOps incident responder.

Analyze these application error logs:

{joined_logs}

Return ONLY valid JSON.

Required JSON schema:

{{
  "title": "short incident title",
  "severity": "LOW|MEDIUM|HIGH|CRITICAL",
  "root_cause": "most likely root cause",
  "evidence": [
    "evidence 1",
    "evidence 2"
  ],
  "recommended_actions": [
    "action 1",
    "action 2",
    "action 3"
  ]
}}

Rules:

1. Use only evidence present in the logs.
2. Do not invent infrastructure details.
3. Be concise.
4. This is a DevOps incident analysis.
5. Severity must be one of:
   LOW, MEDIUM, HIGH, CRITICAL.
"""


# ============================================================
# FALLBACK ANALYZER
# ============================================================

def fallback_analysis(logs):
    """
    Deterministic analysis used when:
    - AI is disabled
    - Ollama is unavailable
    - AI returns invalid JSON
    """

    text = " ".join(logs).lower()

    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    if (
        "database" in text
        or "postgres" in text
    ):
        return {
            "title": "Database connectivity incident",
            "severity": "HIGH",
            "root_cause": (
                "The application cannot connect "
                "to the PostgreSQL dependency."
            ),
            "evidence": logs[:3],
            "recommended_actions": [
                "Check PostgreSQL health.",
                "Verify port 5432 connectivity.",
                "Inspect database connection-pool limits.",
            ],
        }

    # --------------------------------------------------------
    # PAYMENT
    # --------------------------------------------------------

    if (
        "payment" in text
        or "provider" in text
    ):
        return {
            "title": "Payment provider timeout",
            "severity": "HIGH",
            "root_cause": (
                "The upstream payment provider "
                "is timing out."
            ),
            "evidence": logs[:3],
            "recommended_actions": [
                "Check payment provider availability.",
                "Inspect timeout and retry settings.",
                "Check recent application changes.",
            ],
        }

    # --------------------------------------------------------
    # REDIS
    # --------------------------------------------------------

    if (
        "redis" in text
        or "cache" in text
    ):
        return {
            "title": "Redis connectivity incident",
            "severity": "MEDIUM",
            "root_cause": (
                "The application cannot reach "
                "the Redis dependency."
            ),
            "evidence": logs[:3],
            "recommended_actions": [
                "Check Redis health.",
                "Verify port 6379 connectivity.",
                "Inspect Redis connection limits.",
            ],
        }

    # --------------------------------------------------------
    # GENERIC
    # --------------------------------------------------------

    return {
        "title": "Application dependency failure",
        "severity": "MEDIUM",
        "root_cause": (
            "An application dependency "
            "appears unavailable."
        ),
        "evidence": logs[:3],
        "recommended_actions": [
            "Identify the failed dependency.",
            "Check dependency health.",
            "Review recent deployments.",
        ],
    }


# ============================================================
# OLLAMA AI ANALYSIS
# ============================================================

def analyze_with_ai(logs):
    """
    Send logs to Ollama and return structured incident data.
    Falls back to deterministic analysis if AI fails.
    """

    # --------------------------------------------------------
    # AI DISABLED
    # --------------------------------------------------------

    if not AI_ENABLED:
        result = fallback_analysis(logs)

        result["ai_status"] = "AI_DISABLED"

        return result

    ai_requests.inc()

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": build_prompt(logs),
        "stream": False,
        "format": "json",
    }

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=90,
        )

        response.raise_for_status()

        body = response.json()

        ai_response = body.get(
            "response",
            "",
        )

        if not ai_response:
            raise ValueError(
                "Ollama returned an empty response"
            )

        result = json.loads(
            ai_response
        )

        # ----------------------------------------------------
        # Validate required fields
        # ----------------------------------------------------

        required_fields = {
            "title",
            "severity",
            "root_cause",
            "evidence",
            "recommended_actions",
        }

        missing_fields = (
            required_fields
            - result.keys()
        )

        if missing_fields:
            raise ValueError(
                "AI response missing fields: "
                + ", ".join(missing_fields)
            )

        # ----------------------------------------------------
        # Validate severity
        # ----------------------------------------------------

        valid_severities = {
            "LOW",
            "MEDIUM",
            "HIGH",
            "CRITICAL",
        }

        severity = str(
            result["severity"]
        ).upper()

        if severity not in valid_severities:
            result["severity"] = "MEDIUM"
        else:
            result["severity"] = severity

        result["ai_status"] = "SUCCESS"

        return result

    except Exception as exc:

        ai_failures.inc()

        print(
            f"[AI ERROR] {exc}",
            flush=True,
        )

        result = fallback_analysis(
            logs
        )

        result["ai_status"] = "FALLBACK"

        result["ai_error"] = str(
            exc
        )

        return result


# ============================================================
# SAVE INCIDENT
# ============================================================

def save_incident(
    analysis,
    logs,
):
    """
    Save incident as JSON.
    """

    incident_id = str(
        uuid.uuid4()
    )

    incident = {
        "id": incident_id,

        "created_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "logs": logs,

        **analysis,
    }

    path = (
        INCIDENT_DIR
        / f"{incident_id}.json"
    )

    path.write_text(
        json.dumps(
            incident,
            indent=2,
        ),
        encoding="utf-8",
    )

    incidents_created.inc()

    return path


# ============================================================
# OPTIONAL WEBHOOK
# ============================================================

def send_webhook(incident):
    """
    Send incident notification to a webhook if configured.
    """

    if not WEBHOOK_URL:
        return

    payload = {
        "content": (
            f"🚨 INCIDENT: "
            f"{incident['severity']} - "
            f"{incident['title']}\n"
            f"Root cause: "
            f"{incident['root_cause']}"
        )
    }

    try:
        response = requests.post(
            WEBHOOK_URL,
            json=payload,
            timeout=10,
        )

        response.raise_for_status()

    except Exception as exc:
        print(
            f"[WEBHOOK ERROR] {exc}",
            flush=True,
        )


# ============================================================
# LOG READER
# ============================================================

def process_new_lines(
    file,
    offset,
    error_buffer,
):
    """
    Read newly appended log lines.
    """

    file.seek(offset)

    while True:

        line = file.readline()

        if not line:
            break

        offset = file.tell()

        line = line.strip()

        if not line:
            continue

        logs_processed.inc()

        # Detect ERROR log lines
        if " ERROR " in f" {line} ":
            error_buffer.append(line)

    return (
        offset,
        error_buffer,
    )


# ============================================================
# BACKGROUND WORKER
# ============================================================

def worker():
    """
    Continuously monitors application logs.
    """

    print(
        f"Analyzer started | "
        f"log={LOG_FILE} | "
        f"AI={AI_ENABLED} | "
        f"model={OLLAMA_MODEL} | "
        f"incident_dir={INCIDENT_DIR}",
        flush=True,
    )

    offset = 0

    error_buffer = []

    while True:

        try:

            if not os.path.exists(
                LOG_FILE
            ):
                time.sleep(
                    POLL_INTERVAL
                )
                continue

            with open(
                LOG_FILE,
                "r",
                encoding="utf-8",
            ) as file:

                (
                    offset,
                    error_buffer,
                ) = process_new_lines(
                    file,
                    offset,
                    error_buffer,
                )

            # ------------------------------------------------
            # Process batches
            # ------------------------------------------------

            while len(
                error_buffer
            ) >= BATCH_SIZE:

                logs = error_buffer[
                    :BATCH_SIZE
                ]

                error_buffer = (
                    error_buffer[
                        BATCH_SIZE:
                    ]
                )

                # --------------------------------------------
                # AI ANALYSIS
                # --------------------------------------------

                analysis = (
                    analyze_with_ai(
                        logs
                    )
                )

                # --------------------------------------------
                # SAVE INCIDENT
                # --------------------------------------------

                path = save_incident(
                    analysis,
                    logs,
                )

                # --------------------------------------------
                # WEBHOOK
                # --------------------------------------------

                send_webhook(
                    {
                        **analysis,
                        "id": path.stem,
                    }
                )

                print(
                    f"[INCIDENT] "
                    f"{analysis['severity']} | "
                    f"{analysis['title']} | "
                    f"AI={analysis.get('ai_status')} | "
                    f"{path}",
                    flush=True,
                )

        except Exception as exc:

            print(
                f"[WORKER ERROR] {exc}",
                flush=True,
            )

        time.sleep(
            POLL_INTERVAL
        )


# ============================================================
# API ENDPOINTS
# ============================================================

@app.get("/health")
def health():
    """
    Health endpoint.
    """

    return {
        "status": "healthy",
        "ai_enabled": AI_ENABLED,
        "ollama_url": OLLAMA_URL,
        "model": OLLAMA_MODEL,
        "incident_dir": str(
            INCIDENT_DIR
        ),
    }


@app.get("/incidents")
def incidents():
    """
    Return all saved incidents.
    """

    result = []

    for path in sorted(
        INCIDENT_DIR.glob("*.json"),
        reverse=True,
    ):

        try:

            result.append(
                json.loads(
                    path.read_text(
                        encoding="utf-8"
                    )
                )
            )

        except Exception as exc:

            print(
                f"[INCIDENT READ ERROR] "
                f"{path}: {exc}",
                flush=True,
            )

    return {
        "count": len(result),
        "incidents": result,
    }


@app.get("/metrics")
def metrics():
    """
    Prometheus metrics endpoint.
    """

    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


# ============================================================
# APPLICATION START
# ============================================================

if __name__ == "__main__":

    # Start log monitoring in background
    threading.Thread(
        target=worker,
        daemon=True,
    ).start()

    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
    )
