#!/usr/bin/env bash
#
# Start the development server without typing the full command.
#
#   ./run.sh              -> auto-picks the first free port from 8000 up
#   ./run.sh 9000         -> use 9000 if free, otherwise fail loudly
#   ./run.sh --port 9000  -> same, explicit form
#
# Why the port is resolved automatically: Django hard-fails with
# "That port is already in use", and a leftover process from a previous run is
# the normal case in development. With no argument the script picks the next
# free port instead.

set -euo pipefail

# Run from the project root no matter where the script is invoked from, so
# manage.py and the settings module are always found.
cd "$(dirname "${BASH_SOURCE[0]}")"

DEFAULT_PORT=8000
PORT_PROMPT=false
PORT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --port)
      [[ $# -ge 2 ]] || { echo "Error: --port needs a value." >&2; exit 2; }
      PORT="$2"; shift 2 ;;
    --port=*)
      PORT="${1#*=}"; shift ;;
    -h|--help)
      sed -n '2,12p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    [0-9]*)
      PORT="$1"; shift ;;
    *)
      echo "Error: unknown argument '$1'." >&2; exit 2 ;;
  esac
done

# Is the port free? Binding to it is the only reliable test: `ss`/`lsof` report
# listening sockets, but a port can also be held in another state.
port_is_free() {
  uv run python - "$1" <<'PY' 2>/dev/null
import socket, sys
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    s.bind(("127.0.0.1", int(sys.argv[1])))
except OSError:
    sys.exit(1)
finally:
    s.close()
PY
}

if [[ -n "$PORT" ]]; then
  if ! port_is_free "$PORT"; then
    echo "Error: port $PORT is already in use." >&2
    echo "Run ./run.sh with no arguments to auto-pick a free one." >&2
    exit 1
  fi
else
  PORT="$DEFAULT_PORT"
  for _ in $(seq 1 20); do
    if port_is_free "$PORT"; then break; fi
    PORT=$((PORT + 1))
  done
  if ! port_is_free "$PORT"; then
    echo "Error: no free port in ${DEFAULT_PORT}-$((DEFAULT_PORT + 19))." >&2
    exit 1
  fi
  PORT_PROMPT=true
fi

# uv provides the project's own interpreter and dependencies; falling back to
# manage.py directly keeps the script usable outside a uv checkout.
RUNNER=(uv run python manage.py)
if ! command -v uv >/dev/null 2>&1; then
  echo "Warning: 'uv' not found, falling back to the active Python." >&2
  RUNNER=(python manage.py)
fi

echo "Project : $(pwd)"
echo "Python  : $(${RUNNER[0]} ${RUNNER[1]} ${RUNNER[2]} --version 2>&1)"
if [[ "$PORT_PROMPT" == true && "$PORT" != "$DEFAULT_PORT" ]]; then
  echo "Port    : $PORT  (auto-selected; $DEFAULT_PORT was busy)"
else
  echo "Port    : $PORT"
fi
echo "URL     : http://127.0.0.1:${PORT}/"
echo

exec "${RUNNER[@]}" runserver "127.0.0.1:${PORT}"
