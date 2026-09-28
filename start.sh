#!/usr/bin/env bash

pid_chromecast=$(ps ax -o pid,command | awk '/python chromecast/' |
                     awk '!/awk / {print $1}')
if [ ${pid_chromecast} ]; then
    wid_chromecast=$(wmctrl -lp | awk "/${pid_chromecast}/"' {print $1}')
    wmctrl -ia ${wid_chromecast}
else
    cd "$(dirname $(realpath $0))"

    if [ -d .venv ]; then
        source .venv/bin/activate
    else
        python -m venv .venv
        source .venv/bin/activate
        pip install -r requirements.txt
    fi

    python chromecast.py
fi
