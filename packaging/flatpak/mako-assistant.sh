#!/bin/sh
# Flatpak entry point: the package lives in /app/share/mako-assistant.
export PYTHONPATH="/app/share/mako-assistant${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m mako_assistant "$@"
