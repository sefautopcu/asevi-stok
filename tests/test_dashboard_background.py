import ast
import base64
from pathlib import Path
from types import SimpleNamespace


class _SessionState(dict):
    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value


class _UploadedImage:
    type = "image/png"

    def getvalue(self):
        return b"test-image"


def _dashboard_background_callback():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    tree = ast.parse(app_path.read_text(encoding="utf-8"))
    callback = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_dashboard_arka_plan_yukleme_callback"
    )
    module = ast.fix_missing_locations(ast.Module(body=[callback], type_ignores=[]))
    state = _SessionState(dashboard_bg_uploader=_UploadedImage())
    namespace = {"base64": base64, "st": SimpleNamespace(session_state=state)}
    exec(compile(module, str(app_path), "exec"), namespace)
    return namespace[callback.name], state


def test_upload_callback_updates_dashboard_background_before_render():
    callback, state = _dashboard_background_callback()

    callback()

    encoded = base64.b64encode(b"test-image").decode("ascii")
    assert state["dashboard_arka_plan"] == f"data:image/png;base64,{encoded}"
    assert state["_dashboard_bg_upload_success"] is True
