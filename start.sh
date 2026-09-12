#!/usr/bin/env bash

cd "$(dirname $(realpath $0))"

if [ -d .venv ]; then
    source .venv/bin/activate
else
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
fi

python chromecast.py
