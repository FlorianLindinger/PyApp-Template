import pathlib

import launcher_utilities as utils


def main():
    script_dir = pathlib.Path(__file__).parent.resolve()
    settings_path = (script_dir / "../../non-user_settings.ini").resolve()
    settings = utils.get_settings(settings_path)
    utils.stop_program(settings, settings_path)


if __name__ == "__main__":
    main()
