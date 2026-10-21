# Sourced by the scripts that start a server: `hold_server_lock` holds the machine-wide one-server lock on fd 9 for
# the rest of the script and every process it starts (an `exec`ed server, a `nohup` child), so the lock lives exactly
# as long as the servers. Skipped when a parent run holds it (GEM_SERVER_LOCK_HELD, demo/systems/server_lock.py) or when the
# script was started under `flock <lock> <command>`. A busy lock is refused: a server started by hand never queues.
# GEM_SERVER_LOCK overrides the path (tests); the default is demo/paths.py's SERVER_LOCK.
hold_server_lock() {
  local shared lock fd
  shared="$(cd "$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --path-format=absolute --git-common-dir)/.." && pwd)"
  lock="${GEM_SERVER_LOCK:-$(dirname "$shared")/$(basename "$shared")-wt/server.lock}"
  lock="$(realpath -m "$lock")"
  [[ "${GEM_SERVER_LOCK_HELD:-}" == "$lock" ]] && return 0
  for fd in /proc/$$/fd/*; do
    [[ "$(readlink "$fd" 2>/dev/null)" == "$lock" ]] && return 0
  done
  mkdir -p "$(dirname "$lock")"
  exec 9>>"$lock"
  if ! flock -n 9; then
    echo "another run holds the machine-wide server lock $lock; stop it or wait, then retry" >&2
    exit 1
  fi
  export GEM_SERVER_LOCK_HELD="$lock"
}
