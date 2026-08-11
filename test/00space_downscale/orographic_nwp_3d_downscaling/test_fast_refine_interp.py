from importlib import import_module
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_plugin_module = import_module(
    "NIMM.00space_downscale.orographic_nwp_3d_downscaling.fast_refine_interp_plugin"
)
FastRefineInterpPlugin = _plugin_module.FastRefineInterpPlugin


def test_plugin_can_be_constructed():
    plugin = FastRefineInterpPlugin(work_dir="D:/tmp/EC_12P5KM", model_region="EC_12P5KM")
    assert plugin.model_region == "EC_12P5KM"
    assert plugin.operation == "i"
