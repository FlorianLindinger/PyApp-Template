#!/bin/sh
# --- Python selection (Linux only) ---
# ""             first working python3 or python on PATH (Python 3.8+)
# "python3.12"   a particular installed version on PATH
# "/usr/bin/python3" or "/home/me/my env/bin/python"   an explicit executable
# Relative paths containing / start at this shell file's folder.
# Supply one executable, without arguments. Nothing is installed or created.
python_command=""

# Run from any working folder; pass arguments unchanged to the app.
case $0 in
    */*) fallback_dir=${0%/*}; fallback_dir=${fallback_dir:-/} ;;
    *) fallback_dir=. ;;
esac
fallback_dir=$(CDPATH= cd -- "$fallback_dir" && pwd -P) || exit 1
fallback_script=$fallback_dir/../DONT_CHANGE/scripts/actions/start_without_launcher.py
if [ ! -f "$fallback_script" ]; then
    printf '%s\n' "ERROR: Fallback helper not found: $fallback_script" \
        'Restore code/pyapp/DONT_CHANGE from Git or a release.' >&2
    exit 1
fi

unset PYAPP_FALLBACK_VENV
fallback_python=$python_command
if [ -n "$fallback_python" ]; then
    case $fallback_python in
        /*) ;;
        */*) fallback_python=$fallback_dir/$fallback_python ;;
    esac
    if ! "$fallback_python" -I -c 'import sys; sys.exit(sys.version_info < (3, 8))' >/dev/null 2>&1; then
        printf '%s\n' "ERROR: Selected Python does not start or is older than 3.8: $fallback_python" \
            'Change python_command at the top of this shell file, or install that Python and make it accessible.' >&2
        exit 1
    fi
    PYAPP_FALLBACK_SOURCE=configured
else
    for fallback_command in python3 python; do
        if command -v "$fallback_command" >/dev/null 2>&1 && "$fallback_command" -I -c 'import sys; sys.exit(sys.version_info < (3, 8))' >/dev/null 2>&1; then
            fallback_python=$fallback_command
            PYAPP_FALLBACK_SOURCE=$fallback_command
            break
        fi
    done
fi
if [ -z "$fallback_python" ]; then
    printf '%s\n' 'ERROR: No working Python 3.8+ found on PATH (python3/python).' \
        'Set python_command at the top of this shell file to an installed Python executable, or install Python for Linux.' >&2
    exit 1
fi
export PYAPP_FALLBACK_SOURCE
exec "$fallback_python" -B "$fallback_script" "$@"
