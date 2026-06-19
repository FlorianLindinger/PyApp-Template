# Composite License

This folder and its contents are **governed by separate licenses**, as described in the sections below.

---

## Section 1: Main Files (MIT License)

All files in this folder, **except for files in the folders described in the sections below**, are governed by the following license:

```
MIT License

Copyright (c) 2026 [Florian Lindinger]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
```

---

## Section 2: Embeddable Python Distribution (PSF License)

The contents of the folder `backend_python` are files from an embeddable Python distribution which has been modified by renaming and removing some files. All remaining files fall under the license located at `backend_python/LICENSE.txt`.

---

## Section 3: Third-Party Python Packages

The folder `backend_packages` contains third-party Python packages. These packages are not relicensed by this file. Each package remains under its own license, and the bundled license or metadata files listed below should be kept with the package when distributing it.

| Package or component | Bundled version | License shown by bundled metadata or license file | Bundled license / notice files |
| --- | --- | --- | --- |
| `certifi` | 2026.4.22 | MPL-2.0 | `certifi-2026.4.22.dist-info/licenses/LICENSE` |
| `charset-normalizer` | 3.4.7 | MIT | `charset_normalizer-3.4.7.dist-info/licenses/LICENSE` |
| `docopt` | 0.6.2 | MIT | `docopt-0.6.2.dist-info/licenses/LICENSE-MIT` |
| `idna` | 3.13 | BSD-3-Clause | `idna-3.13.dist-info/licenses/LICENSE.md` |
| `markdown-it-py` | 4.0.0 | MIT | `markdown_it_py-4.0.0.dist-info/licenses/LICENSE`, `markdown_it_py-4.0.0.dist-info/licenses/LICENSE.markdown-it` |
| `mdurl` | 0.1.2 | MIT | `mdurl-0.1.2.dist-info/LICENSE` |
| `pipreqs` | 0.5.0 | Apache-2.0 | `pipreqs-0.5.0.dist-info/LICENSE` |
| `Pygments` | 2.20.0 | BSD-2-Clause | `pygments-2.20.0.dist-info/licenses/LICENSE`, `pygments-2.20.0.dist-info/licenses/AUTHORS` |
| `requests` | 2.33.1 | Apache-2.0 | `requests-2.33.1.dist-info/licenses/LICENSE`, `requests-2.33.1.dist-info/licenses/NOTICE` |
| `rich` | 15.0.0 | MIT | `rich-15.0.0.dist-info/licenses/LICENSE` |
| `typing_extensions` | 4.15.0 | PSF-2.0 | `typing_extensions-4.15.0.dist-info/licenses/LICENSE` |
| `urllib3` | 2.6.3 | MIT | `urllib3-2.6.3.dist-info/licenses/LICENSE.txt` |
| `win11toast` | 0.36.3 | MIT | `win11toast-0.36.3.dist-info/licenses/LICENSE` |
| `winrt-runtime` | 3.2.1 | MIT | `winrt_runtime-3.2.1.dist-info/METADATA` |
| `winrt-Windows.Data.Xml.Dom` | 3.2.1 | MIT | `winrt_windows_data_xml_dom-3.2.1.dist-info/METADATA` |
| `winrt-Windows.Foundation` | 3.2.1 | MIT | `winrt_windows_foundation-3.2.1.dist-info/METADATA` |
| `winrt-Windows.Foundation.Collections` | 3.2.1 | MIT | `winrt_windows_foundation_collections-3.2.1.dist-info/METADATA` |
| `winrt-Windows.Globalization` | 3.2.1 | MIT | `winrt_windows_globalization-3.2.1.dist-info/METADATA` |
| `winrt-Windows.Graphics.Imaging` | 3.2.1 | MIT | `winrt_windows_graphics_imaging-3.2.1.dist-info/METADATA` |
| `winrt-Windows.Media.Core` | 3.2.1 | MIT | `winrt_windows_media_core-3.2.1.dist-info/METADATA` |
| `winrt-Windows.Media.Ocr` | 3.2.1 | MIT | `winrt_windows_media_ocr-3.2.1.dist-info/METADATA` |
| `winrt-Windows.Media.Playback` | 3.2.1 | MIT | `winrt_windows_media_playback-3.2.1.dist-info/METADATA` |
| `winrt-Windows.Media.SpeechSynthesis` | 3.2.1 | MIT | `winrt_windows_media_speechsynthesis-3.2.1.dist-info/METADATA` |
| `winrt-Windows.Storage` | 3.2.1 | MIT | `winrt_windows_storage-3.2.1.dist-info/METADATA` |
| `winrt-Windows.Storage.Streams` | 3.2.1 | MIT | `winrt_windows_storage_streams-3.2.1.dist-info/METADATA` |
| `winrt-Windows.UI.Notifications` | 3.2.1 | MIT | `winrt_windows_ui_notifications-3.2.1.dist-info/METADATA` |
| `yarg` | 0.1.10 | MIT, with bundled Apache-2.0 notice for requests-derived material | `yarg-0.1.10.dist-info/LICENSE`, `yarg-0.1.10.dist-info/LICENSE-REQUESTS` |

---

## Section 4: Practical Distribution Summary

This section is a practical summary, not legal advice. For an important commercial release, verify the exact license texts above with a lawyer or a dedicated license-compliance tool.

### Sharing the repository via Git

This repository may be shared through Git with `backend_packages` included. Keep the package metadata, license files, copyright notices, and notice files listed in Section 3. Do not remove `.dist-info` folders or bundled `LICENSE`, `NOTICE`, `AUTHORS`, or `license.txt` files.

Sharing through Git is distribution of these third-party packages, so the same license obligations still apply. In source-form Git distribution, the most important practical requirement is preserving the license and notice files. For MPL/LGPL-covered parts, also preserve source availability for those covered files and any modifications to them.

### Selling a product

Most packages listed here are permissive licenses such as MIT, BSD, Apache-2.0, or PSF-2.0. In broad terms, those licenses allow commercial use, distribution, and sale, provided the required copyright notices, license texts, and disclaimers are preserved. Apache-2.0 packages also have NOTICE and patent-related conditions; keep `NOTICE` files when present.

The `certifi` package is MPL-2.0. MPL-2.0 is a file-level copyleft license: you can combine it with proprietary code, but if you distribute modified MPL-covered files, those files and their modifications must remain available under MPL-2.0, and recipients must be told how to get the source for the MPL-covered parts.

The bundled `adodbapi` component is LGPL-2.1-or-later. If you distribute it as part of a product, keep the LGPL license text and notices, provide or offer the corresponding source for that LGPL component and any modifications to it, and avoid packaging it in a way that prevents users from replacing or modifying that LGPL component. If the product does not need `adodbapi`, excluding it from the shipped product can reduce license-compliance work.

For binary installers, zip files, or compiled applications, include a third-party notices file or license bundle containing the license files listed in Section 3. Also keep source or source-offer handling for MPL/LGPL-covered parts if those parts are distributed.

No package listed here appears to require the whole application to be open sourced merely because it is shared on Git or sold as a product. The main obligations are notice preservation, source availability for MPL/LGPL-covered parts, and not using upstream author or project names to imply endorsement.

---
