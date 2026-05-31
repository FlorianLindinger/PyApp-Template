"""Common code for scripts that are run with frontend Python in PyApp-Template.

This script is supposed to be as compatible as feasable for lower Python versions:
- No type annotations (for >= 3.y)
- No "from __future__ import annotations" (for >= 3.7)
- No f-strings with backslashes in the {} (for >= 3.x)
- No f-strings (for >= 3.6)
- No .astimezone() (for >= 3.5)

"""

# ====================================
# import packages
import atexit
import os
import sys
import threading

# ====================================
# add root dir for debug cases where this script is called on its own:

root_dir = os.path.dirname(__file__) + "\\..\\.."
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# ====================================
# import from files

from developer_settings import (
    input_prepend,
    log_input_prepend,
    log_print_prepend,
    play_sound_on_crash,
    play_sound_on_failure,
    play_sound_on_success,
    print_prepend,
    python_version,
    start_in_shortcut_folder,
)
from DONT_CHANGE.specific_scripts.common_variables import (
    CORRECT_START_SIGNAL_FILE_PATH,
    env_var_to_signal_startup_time_measurement,
    play_sound_on_crash_default,
    play_sound_on_failure_default,
    play_sound_on_success_default,
    process_id_file_path,
    python_script_path,
    start_time_dummy_main_script,
    windows_dir,
)

# ====================================
# process developer_settings settings

# change main_script if in startup time measurement mode
if os.environ.get(env_var_to_signal_startup_time_measurement):
    python_script_path = start_time_dummy_main_script

# raise error if script not found
if not os.path.exists(python_script_path):
    raise FileNotFoundError(f'[Error] Python script not found at "{python_script_path}"')

if start_in_shortcut_folder == True:
    wdir_is_script_dir = False
else:
    wdir_is_script_dir = True

if python_version in [None, False, ""]:
    python_version = ""
if log_print_prepend in [None, False, ""]:
    log_print_prepend = ""
if log_input_prepend in [None, False, ""]:
    log_input_prepend = ""
if print_prepend in [None, False, ""]:
    print_prepend = ""
if input_prepend in [None, False, ""]:
    input_prepend = ""

# Normalize optional sound settings to concrete .wav paths. Each setting accepts False/None/"", True for the template default, a media filename, or an absolute path.
if play_sound_on_crash is True:
    wav_on_crash = play_sound_on_crash_default
elif play_sound_on_crash in [False, None, ""]:
    wav_on_crash = ""
elif not os.path.isabs(play_sound_on_crash):
    wav_on_crash = os.path.normpath(windows_dir + "\\Media\\" + play_sound_on_crash)
else:
    wav_on_crash = play_sound_on_crash
if wav_on_crash != "":
    if wav_on_crash[-4:] != ".wav":
        wav_on_crash += ".wav"
    if not os.path.exists(wav_on_crash):
        print(f"[Warning] Sound file does not exist: {wav_on_crash}")
        wav_on_crash = ""

if play_sound_on_success is True:
    wav_on_success = play_sound_on_success_default
elif play_sound_on_success in [False, None, ""]:
    wav_on_success = ""
elif not os.path.isabs(play_sound_on_success):
    wav_on_success = os.path.normpath(windows_dir + "\\Media\\" + play_sound_on_success)
else:
    wav_on_success = play_sound_on_success
if wav_on_success != "":
    if wav_on_success[-4:] != ".wav":
        wav_on_success += ".wav"
    if not os.path.exists(wav_on_success):
        print(f"[Warning] Sound file does not exist: {wav_on_success}")
        wav_on_success = ""

if play_sound_on_failure is True:
    wav_on_failure = play_sound_on_failure_default
elif play_sound_on_failure in [False, None, ""]:
    wav_on_failure = ""
elif not os.path.isabs(play_sound_on_failure):
    wav_on_failure = os.path.normpath(windows_dir + "\\Media\\" + play_sound_on_failure)
else:
    wav_on_failure = play_sound_on_failure
if wav_on_failure != "":
    if wav_on_failure[-4:] != ".wav":
        wav_on_failure += ".wav"
    if not os.path.exists(wav_on_failure):
        print(f"[Warning] Sound file does not exist: {wav_on_failure}")
        wav_on_failure = ""

# ====================================
#  define common code


class _ProcessIdRegistry:
    """Maintain the PID file entries created by this launcher process."""

    def __init__(self, path):
        self.path = path
        self._process_ids = set()
        self._lock = threading.RLock()

    def add(self, process_id):
        """Add a pid value to the local collection when valid and new."""
        if self.path == "" or process_id <= 0:
            return

        with self._lock:
            if process_id in self._process_ids:
                return
            self._process_ids.add(process_id)

            folder = os.path.dirname(self.path)
            if folder:
                os.makedirs(folder, exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as pid_file:
                pid_file.write(f"{process_id}\n")

    def remove(self, process_id):
        """Remove a value from the local collection and backing file."""
        if self.path == "" or process_id <= 0:
            return

        with self._lock:
            self._process_ids.discard(process_id)
            try:
                with open(self.path, encoding="utf-8") as pid_file:
                    lines = pid_file.readlines()
            except FileNotFoundError:
                return
            except Exception:
                return

            remaining_lines = []
            process_id_text = str(process_id)
            for line in lines:
                parts = line.strip().split(maxsplit=1)
                if parts and parts[0] == process_id_text:
                    continue
                remaining_lines.append(line)

            try:
                if any(line.strip() for line in remaining_lines):
                    with open(self.path, "w", encoding="utf-8") as pid_file:
                        pid_file.writelines(remaining_lines)
                else:
                    os.remove(self.path)
            except Exception:
                pass

    def cleanup(self):
        """Remove registered process IDs during interpreter shutdown."""
        for process_id in list(self._process_ids):
            self.remove(process_id)


def process_finish(wav_path="", log_path="", open_log=False):
    """Run completion side effects such as sounds and opening logs."""
    if wav_path:
        try:
            import winsound

            winsound.PlaySound(
                wav_path,
                winsound.SND_FILENAME | winsound.SND_NODEFAULT,
            )
        except Exception as e:
            print(f"[Error] Failed to play .wav file: {e}")

    if log_path and open_log:
        try:
            os.startfile(log_path)  # type: ignore[attr-defined]  # noqa:S606
        except Exception as e:
            print(f"[Error] Failed to open log: {e}")


def looks_like_interpreter_crash(returncode):
    """Return whether a process return code matches common Windows crash codes. A Python crash is meant to be a Python interpreter crash as opposed to a exit with a failure code for exampel with sys.exit(1)."""
    _WINDOWS_CRASH_CODES = {
        0xC0000005,  # access violation
        0xC00000FD,  # stack overflow
        0xC000001D,  # illegal instruction
        0xC0000096,  # privileged instruction
        0xC0000409,  # stack buffer overrun
    }

    def _int_to_unsigned32(n):
        """Convert a signed return code to an unsigned 32-bit value."""
        return n & 0xFFFFFFFF

    return isinstance(returncode, int) and (_int_to_unsigned32(returncode) in _WINDOWS_CRASH_CODES)


# ====================================
#  define common variables


# ====================================
#  execute common code

# tell the backend terminal via a signal file to close because successful start
if CORRECT_START_SIGNAL_FILE_PATH:
    folder = os.path.dirname(CORRECT_START_SIGNAL_FILE_PATH)
    if folder:
        os.makedirs(folder, exist_ok=True)
    open(CORRECT_START_SIGNAL_FILE_PATH, "w", encoding="utf-8").close()

# add pid to "currently running" file
if process_id_file_path != "":
    try:
        process_id_registry = _ProcessIdRegistry(process_id_file_path)
        process_id_registry.add(os.getpid())
        atexit.register(process_id_registry.cleanup)
    except Exception as e:
        print(f"[Warning] Failed to write script-wrapper PID file: {e}")

# ====================================
