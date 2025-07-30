####################################################################################################################################
# Add code at the bottom that runs with the start of the program.
####################################################################################################################################
import settings # imports and converts user variables (e.g., name: value) in settings.yaml (access value via dictionary: s["name"])
####################################################################################################################################

# import time
# time.sleep(10)

import os
print(os.getcwd())  # prints the current working directory

for i in range(20):
    print(i)
    import time
    time.sleep(1)  # sleep for 0.1 seconds

# import win32gui
# import win32con
# import time
# import fnmatch

# import pywinauto  # type:ignore (for interacting with windows)
# def get_window_titles() -> list[str]:
#     """returns a list of all windows window titles"""
#     windows = pywinauto.Desktop(backend="uia").windows()  # type: ignore
#     return [w.window_text() for w in windows]  # type: ignore

# print(get_window_titles())

# def close_window(window_title):
#     """closes all windows with window_title. Wildcards with "*" """
#     if "*" in window_title:
#         window_titles = find_window_titles(window_title)
#     else:
#         titles = get_window_titles()
#         count = titles.count(window_title)
#         window_titles = [window_title]*count

#     for window_title in window_titles:
#         handle = win32gui.FindWindow(None, rf'{window_title}')
#         win32gui.PostMessage(handle, win32con.WM_CLOSE, 0, 0)
#         if len(window_titles) > 1:
#             # needed to close mutiple windows with same name because slow
#             time.sleep(0.1)
            
# def find_window_titles(wildcard_title: str) -> list[str]:
#     """
#     Returns list of window titles matching wildcard_title. One can use wildcards in the title. Capitalization is ignored.
#     """
#     return find_wildcard_in_list(get_window_titles(), wildcard_title)

# def find_wildcard_in_list(lis: list[str], wildcard, exclude_subfolders=False, exclude_folders=False, real_paths=None) -> list[str]:
#     """searches for wildcard match in every element in lis and return elements in lis that have a match.
#     exclude_subfolders=True prevents return of matches that contain // or \\.
#     exclude_folders=True prevents results without "." if real_paths!=True
#     and prevents actual folder results if real_paths==True"""
#     if not is_list(lis):
#         lis = [lis]  # type:ignore
#     res0 = fnmatch.filter(lis, wildcard)
#     if exclude_folders == True and real_paths == True:
#         accepted_lis = []
#         for found_lis in res0:
#             if not os.path.isdir(found_lis):
#                 accepted_lis.append(found_lis)
#         res1 = accepted_lis
#     else:
#         res1 = res0
#     if exclude_subfolders == True:
#         res1 = [res_elem for res_elem in res1 if len(split_path(res_elem)) == len(
#             split_path(wildcard))]  # rejects elements with wrong folder depth
#     if exclude_folders == True:
#         # reject paths of folders based on info of folder element paths
#         res1 = [res_elem for res_elem in res1 if len(
#             find_wildcard_in_list(lis=res0, wildcard=res_elem+"\\*")) == 0]
#     return res1

# def is_list(x):
#     """returns True if x is a list type"""
#     if str(type(x)) in ["<class 'list'>", "<class 'tuple'>", "<class 'numpy.ndarray'>", "<class 'sympy.tensor.array.dense_ndim_array.ImmutableDenseNDimArray'>", "sympy.tensor.array.dense_ndim_array.ImmutableDenseNDimArray"]:
#         return True
#     else:
#         return False
    
# def split_path(path: str) -> list[str]:
#     """splits path from string into list of path sections. If the path ends in \\ there won't be an empty string at the end of the list"""
#     return os.path.normpath(path).split(os.sep)

# close_window("program name")

# print(get_window_titles())
