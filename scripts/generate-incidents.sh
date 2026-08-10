#!/usr/bin/env bash

set -euo pipefail


echo "Generating database errors..."


for i in {1..3}; do

    curl -fsS \
        http://localhost:8000/test/db-failure

    echo

    sleep 1

done


echo
echo "Generating payment errors..."


for i in {1..3}; do

    curl -fsS \
        http://localhost:8000/test/payment-failure

    echo

    sleep 1

done


echo
echo "Generating Redis errors..."


for i in {1..3}; do

    curl -fsS \
        http://localhost:8000/test/cache-failure

    echo

    sleep 1

done


echo
echo "Finished."
