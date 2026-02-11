import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request

import launcher_utilities as utils


def find_latest_full_version(ver_input):
    base_url = "https://www.python.org/ftp/python/"
    try:
        req = urllib.request.Request(base_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as response:
            html = response.read().decode("utf-8")

        pattern = r'href="(\d+\.\d+\.\d+)/"'
        versions = re.findall(pattern, html)

        if ver_input:
            versions = [v for v in versions if v.startswith(ver_input)]

        if not versions:
            return None

        versions.sort(key=lambda s: list(map(int, s.split("."))), reverse=True)

        for v in versions:
            amd64_url = f"{base_url}{v}/amd64/"
            try:
                req_v = urllib.request.Request(amd64_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req_v) as resp:
                    if resp.status == 200:
                        return v
            except:
                continue
        return None
    except Exception as e:
        print(f"[Error] Version lookup failed: {e}")
        return None


def download_msi_files(full_ver, download_dir, exclude_pattern):
    base_url = f"https://www.python.org/ftp/python/{full_ver}/amd64/"
    try:
        req = urllib.request.Request(base_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as response:
            html = response.read().decode("utf-8")

        msi_links = re.findall(r'href="([^"]+\.msi)"', html)
        downloaded = []

        for link in msi_links:
            if link.endswith("_d.msi") or link.endswith("_pdb.msi"):
                continue

            component_name = link.split(".")[0]
            if re.search(exclude_pattern, component_name, re.I):
                continue

            out_path = download_dir / link
            print(f"Downloading {link}...")
            urllib.request.urlretrieve(base_url + link, out_path)
            downloaded.append(out_path)
        return downloaded
    except Exception as e:
        print(f"[Error] Download failed: {e}")
        return []


def extract_msi_files(msi_files, target_dir):
    for msi in msi_files:
        print(f"Extracting {msi.name}...")
        # msiexec is picky about TARGETDIR quoting.
        # Using shell=True and manual quoting for maximum reliability on Windows.
        cmd = f'msiexec /a "{msi}" TARGETDIR="{target_dir}" /qn'
        subprocess.run(cmd, check=True, shell=True)
        copied_msi = target_dir / msi.name
        if copied_msi.exists():
            copied_msi.unlink()


def main():
    script_dir = pathlib.Path(__file__).parent.resolve()
    settings_path = (script_dir / "../../non-user_settings.ini").resolve()
    settings = utils.get_settings(settings_path)

    py_env_dir = (settings_path.parent / "py_env").resolve()
    python_dist = py_env_dir / "py_dist"

    requested_v = settings.get("python_version", "3.13")
    print(f"[Info] Identifying latest compatible Python for '{requested_v}'...")
    full_v = find_latest_full_version(requested_v)

    if not full_v:
        print("[Error] Could not find compatible Python version. Check internet connection.")
        sys.exit(1)

    print(f"[Info] Found Python {full_v}. Preparing installation...")

    excludes = ["path", "appendpath", "pip", "launcher", "freethreaded"]
    if settings.get("install_tkinter", "false").lower() != "true":
        excludes.append("tcltk")
    if settings.get("install_tests", "false").lower() != "true":
        excludes.append("test")
    if settings.get("install_tools", "false").lower() != "true":
        excludes.append("tools")
    if settings.get("install_docs", "false").lower() != "true":
        excludes.append("doc")
    exclude_pattern = "^(" + "|".join(excludes) + r")$"

    if python_dist.exists():
        if (python_dist / "python.exe").exists() or not any(python_dist.iterdir()):
            shutil.rmtree(python_dist)
        else:
            print(f"[Error] {python_dist} exists but isn't a Python folder. Aborting.")
            sys.exit(2)

    python_dist.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = pathlib.Path(tmp_dir)
        msi_list = download_msi_files(full_v, tmp_path, exclude_pattern)
        if not msi_list:
            print("[Error] No MSI files downloaded.")
            sys.exit(3)

        print(f"\n==== Installing Python {full_v} locally ====\n")
        extract_msi_files(msi_list, python_dist)

    with open(python_dist / ".gitignore", "w", encoding="utf-8") as f:
        f.write("# Auto added to prevent sync\n*\n")

    ruff_cfg = python_dist / "Lib/test/.ruff.toml"
    if ruff_cfg.exists():
        content = ruff_cfg.read_text(encoding="utf-8")
        content = re.sub(r"(?m)^(\s*extend\s*=)", r"# \1", content)
        ruff_cfg.write_text(content, encoding="utf-8")

    with open(python_dist / "pip.ini", "w", encoding="utf-8") as f:
        f.write("[global]\nno-warn-script-location = false\n")

    print("[Info] Setting up pip...")
    py_exe = str(python_dist / "python.exe")
    subprocess.run([py_exe, "-m", "ensurepip", "--upgrade"], capture_output=True)
    subprocess.run([py_exe, "-m", "pip", "install", "--upgrade", "pip"], capture_output=True)
    subprocess.run([py_exe, "-m", "pip", "install", "--upgrade", "pip"], capture_output=True)

    print(f"\n[Success] Portable Python {full_v} created at {python_dist}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[FATAL ERROR] Installation failed: {e}")
        input("\nPress Enter to exit...")
        sys.exit(1)
