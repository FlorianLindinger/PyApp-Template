"""python <this folder> [options] [-- command]  or  python -m <package> ...: see host.main()."""

import sys
from pathlib import Path

if __package__:
    from .host import main
else:
    # Run as a folder: Python put the folder itself on sys.path (or nothing, with -I), so the
    # package cannot be imported by name. host.py then imports ui.py from its own folder.
    sys.path.append(str(Path(__file__).resolve().parent))
    from host import main  # type: ignore[import-not-found]

sys.exit(main())
