# browser_terminal_path,
# compiled_terminal_path,
# developer_settings_dir,
# developer_settings_path,
# uncompiled_terminal_path,
# button_settings,
# dark_mode,
# stylesheet_path,
# terminal_needs_input,


# if dark_mode is None:
#     dark_mode = "auto"
# elif dark_mode is True:
#     dark_mode = "1"
# elif dark_mode is False:  # type:ignore
#     dark_mode = "0"
# if stylesheet_path in [False, None, ""]:
#     stylesheet_path = EMPTY_ARG_INDICATOR
# else:
#     if not os.path.isabs(stylesheet_path):
#         stylesheet_path = os.path.normpath(developer_settings_dir + "\\" + stylesheet_path)


# if launch_mode == "browser":

#     args += [python_exe_for_script_path]
#     launched_backend_path = browser_terminal_path
#     proc = subprocess.Popen(  #type:ignore
#         [
#             sys.executable,
#             "-X",
#             "faulthandler",
#             browser_terminal_path,
#             *args,
#         ],
#         creationflags=subprocess.CREATE_NO_WINDOW,
#         stdout=subprocess.PIPE,
#         stderr=subprocess.STDOUT,
#         text=True,
#     )

# ==============

# elif launch_mode in ["terminal_emulator", "uncompiled_terminal_emulator"]:

#     # run in terminal emulator
#     import json

#     # pass button settings via json
#     if button_settings in [None, False, ""]:
#         button_settings_path = EMPTY_ARG_INDICATOR
#     else:
#         try:
#             button_settings_path = json.dumps(dict(button_settings))
#         except TypeError as e:
#             raise TypeError(
#                 f'[Error] button_settings in developer settings at "{developer_settings_path}" must be JSON serializable and convertible to a dict.'
#             ) from e
#         except ValueError as e:
#             raise ValueError(
#                 f'[Error] button_settings in developer settings at "{developer_settings_path}" must be a dict or an iterable of (button_name, settings) pairs.'
#             ) from e

#     args += [
#         python_exe_for_script_path,
#         bool_to_arg(terminal_needs_input),
#         stylesheet_path,
#         dark_mode,
#         button_settings_path,
#     ]

#     if launch_mode == "uncompiled_terminal_emulator":
#         launched_backend_path = uncompiled_terminal_path
#         proc = subprocess.Popen( #type:ignore
#             [
#                 "py",
#                 "-X",
#                 "faulthandler",
#                 uncompiled_terminal_path,
#                 *args,
#             ],
#             creationflags=subprocess.CREATE_NO_WINDOW,
#             stdout=subprocess.PIPE,
#             stderr=subprocess.STDOUT,
#             text=True,
#         )
#     else:
#         # run and wait (using the compiled terminal emulator)
#         launched_backend_path = compiled_terminal_path
#         proc = subprocess.Popen(  #type:ignore
#             [compiled_terminal_path, *args],
#             creationflags=subprocess.CREATE_NO_WINDOW,
#             startupinfo=generate_minimized_startupinfo() if start_minimized else None,
#             stdout=subprocess.PIPE,
#             stderr=subprocess.STDOUT,
#             text=True,
#         )
