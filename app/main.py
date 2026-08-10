import logging
import os
from datetime import datetime, timezone

from fastapi import FastAPI


LOG_FILE = os.getenv(
    "LOG_FILE",
    "/data/app.log"
)


os.makedirs(
    os.path.dirname(LOG_FILE),
    exist_ok=True
)


logger = logging.getLogger("demo-app")

logger.setLevel(logging.INFO)


handler = logging.FileHandler(
    LOG_FILE
)


handler.setFormatter(
    logging.Formatter(
        "%(asctime)s %(levelname)s %(message)s"
    )
)


logger.addHandler(handler)


app = FastAPI(
    title="AI DevOps Demo Application"
)


@app.get("/")
def root():

    return {
        "service": "demo-app",
        "status": "running"
    }


@app.get("/health")
def health():

    return {
        "status": "healthy"
    }


@app.get("/test/success")
def success():

    logger.info(
        "request completed successfully "
        "path=/test/success"
    )

    return {
        "status": "ok"
    }


@app.get("/test/db-failure")
def db_failure():

    logger.error(
        "database connection failed "
        "host=postgres "
        "port=5432 "
        "error=connection_refused "
        "pool=exhausted"
    )

    logger.error(
        "orders API returning HTTP 503 "
        "dependency=postgres"
    )

    return {
        "status": "simulated failure",
        "type": "database"
    }


@app.get("/test/payment-failure")
def payment_failure():

    logger.error(
        "payment provider timeout "
        "provider=payment-api "
        "error=upstream_timeout "
        "timeout=30s"
    )

    logger.error(
        "checkout request failed "
        "status=502 "
        "dependency=payment-provider"
    )

    return {
        "status": "simulated failure",
        "type": "payment"
    }


@app.get("/test/cache-failure")
def cache_failure():

    logger.error(
        "redis connection timeout "
        "host=redis "
        "port=6379 "
        "error=connection_timeout"
    )

    logger.error(
        "session service unavailable "
        "dependency=redis"
    )

    return {
        "status": "simulated failure",
        "type": "cache"
    }


@app.get("/time")
def current_time():

    return {
        "utc": datetime.now(
            timezone.utc
        ).isoformat()
    }
