# MIT License

Copyright (c) 2026 Florian Lindinger

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

---

The license above covers every file in this directory and its subdirectories (SPDX: `MIT`),
including the banner font in `data/fonts`, except:

* **Bundled xterm.js files** in `browser_terminal/web` (`xterm.js`, `xterm.css`, `addon-fit.js`,
  `addon-web-links.js`): also MIT, but copyright the xterm.js authors; their notice is in
  `browser_terminal/web/LICENSE-xterm.js.txt` and must stay with those files.

uv, the Python distributions it installs and the app's third-party packages live outside this
directory (see the project's root `LICENSE.md`) and keep their own licenses. `.gitignore` does not
alter licensing terms. If you distribute a prepared folder, retain the license and notice files of
every included distribution and package.
