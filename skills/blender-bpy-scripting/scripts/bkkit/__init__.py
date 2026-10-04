"""bkkit — verified helpers for driving Blender's bpy from scripts.

Written against Blender 5.2.2 LTS (commit d13f752e3b9c), bundled Python 3.13.13.
Every public function in this package was executed inside a real headless
Blender before being committed. See references/ for the full evidence log.

Import from inside a Blender script with:

    import sys; sys.path.insert(0, "/abs/path/to/scripts")
    from bkkit import scenecheck, imagecheck, introspect
"""

from . import compat, introspect, scenecheck, imagecheck  # noqa: F401

__all__ = ["compat", "introspect", "scenecheck", "imagecheck"]
__version__ = "1.0.0"
