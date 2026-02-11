import pathlib
import sys

import launcher_utilities as utils

# Add terminal_emulator to path to import the shortcut utility
script_dir = pathlib.Path(__file__).parent.resolve()
emulator_dir = (script_dir / "../terminal_emulator").resolve()
sys.path.append(str(emulator_dir))

try:
    from create_shortcut_for_compiled import create_shortcut_with_appid
except ImportError as e:
    print(f"[Error] Failed to import shortcut utility: {e}")
    sys.exit(1)


def main():
    settings_path = (script_dir / "../../non-user_settings.ini").resolve()
    settings = utils.get_settings(settings_path)
    if not settings:
        sys.exit(1)

    prog_name = settings.get("program_name", "App")
    dest_dir = (settings_path.parent / settings.get("shortcut_destination_path", "..")).resolve()
    icon_dir = settings_path.parent
    python_exe = sys.executable

    # Target scripts
    launcher_py = (script_dir / "start_program.py").resolve()
    settings_py = (script_dir / "open_settings.py").resolve()
    stop_py = (script_dir / "stop_program.py").resolve()

    def clean(name):
        return name.replace("!program_name!", prog_name)

    def make_lnk(name_key, icon_key, target, args, _desc, appid):
        name = clean(settings.get(name_key, prog_name))
        icon = (icon_dir / settings.get(icon_key, "")).resolve()
        output_path = dest_dir / f"{name}.lnk"

        print(f"[Info] Generating: {name}")
        create_shortcut_with_appid(
            args=f'"{target}" {args}',
            output=str(output_path),
            app_id=f"{prog_name}.{appid}",
            icon_path=str(icon) if icon.exists() else None,
            target=python_exe,
            wdir=str(script_dir),
        )

    # Generate the 4 standard shortcuts
    make_lnk("start_name", "icon_path", launcher_py, "", prog_name, "Main")
    make_lnk("settings_name", "settings_icon_path", settings_py, "", "Settings", "Settings")
    make_lnk("start_no_terminal_name", "icon_path", launcher_py, "--background", "Background", "Background")
    make_lnk("stop_no_terminal_name", "stop_icon_path", stop_py, "", "Stop", "Stop")

    print(f"\n[Success] Shortcuts created in: {dest_dir}")


if __name__ == "__main__":
    main()
