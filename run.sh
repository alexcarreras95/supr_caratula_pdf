#!/usr/bin/env bash
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-wayland;xcb}"
cd "$(dirname "$0")" && exec .venv/bin/python app.py "$@"
