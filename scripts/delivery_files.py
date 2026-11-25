"""Replace delivery assets atomically, even when a previous copy was read-only."""
import os
from pathlib import Path
import tempfile


VIEWER_DIR = Path(__file__).resolve().parents[1] / "templates/viewer"
PREVIEW_FILES = frozenset({"model.glb", "model.manifest.json", "explorer.json", "explosion-audit.json"})

REQUIRED_VIEWER_FILES = (
    'EARCUT-LICENSE.txt',
    'THREE-LICENSE.txt',
    'camera-director.js',
    'camera-views.json',
    'explorer-controller.js',
    'explorer-state.js',
    'explorer.css',
    'guide-core.js',
    'guide-player.js',
    'guide.css',
    'index.html',
    'maketwin-logo.png',
    'maketwin.css',
    'reference-ui.css',
    'showcase-state.js',
    'vendor-build-three.module.js',
    'vendor-examples-jsm-controls-OrbitControls.js',
    'vendor-examples-jsm-environments-RoomEnvironment.js',
    'vendor-examples-jsm-loaders-GLTFLoader.js',
    'vendor-examples-jsm-utils-BufferGeometryUtils.js',
    'vendor-sources.json',
)

def viewer_assets():
    """Return the portable viewer files shared by all product deliveries."""
    return sorted(path for path in VIEWER_DIR.iterdir()
                  if path.is_file() and not path.name.startswith(".") and path.name not in PREVIEW_FILES)


def copy_asset(source, target):
    source, target = Path(source), Path(target)
    if source.is_symlink() or target.is_symlink():
        raise ValueError('Delivery assets must not be symlinks')
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.asset-', dir=target.parent)
    tmp = Path(name)
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(source.read_bytes())
        tmp.chmod(0o644)
        tmp.replace(target)
    finally:
        tmp.unlink(missing_ok=True)
    return target
