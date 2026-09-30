#!/usr/bin/env bash
# Build and run the challenge container locally.
# Usage: ./build/build_and_run.sh [port]
set -euo pipefail
cd "$(dirname "$0")/.."

PORT="${1:-5000}"

docker build -f build/Dockerfile -t saint-vespers-and-the-copper-choir .
docker run --rm -it -p "${PORT}:5000" --name vespers-local saint-vespers-and-the-copper-choir
