#!/usr/bin/env bash

set -euo pipefail


echo "=============================="
echo "Docker Compose"
echo "=============================="

docker compose ps


echo
echo "=============================="
echo "Application Health"
echo "=============================="

curl -fsS \
    http://localhost:8000/health

echo


echo
echo "=============================="
echo "Analyzer Health"
echo "=============================="

curl -fsS \
    http://localhost:8001/health

echo


echo
echo "=============================="
echo "Incidents"
echo "=============================="

curl -fsS \
    http://localhost:8001/incidents

echo
