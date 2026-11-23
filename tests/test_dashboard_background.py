import ast
import base64
import io
from pathlib import Path
from types import SimpleNamespace

from PIL import Image


class _SessionState(dict):
    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value


class _UploadedImage:
    type = "image/png"

    def __init__(self, content):
        self.content = content

    def getvalue(self):
        return self.content


def _dashboard_background_functions(content):
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    tree = ast.parse(app_path.read_text(encoding="utf-8"))
    functions = {
        node.name: node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name in (
            "_dashboard_arka_plan_data_uri",
            "_dashboard_arka_plan_yukleme_callback",
        )
    }
    module = ast.fix_missing_locations(
        ast.Module(body=list(functions.values()), type_ignores=[])
    )
    state = _SessionState(
        dashboard_bg_uploader=_UploadedImage(content)
    )
    namespace = {
        "base64": base64,
        "io": io,
        "st": SimpleNamespace(session_state=state),
    }
    exec(compile(module, str(app_path), "exec"), namespace)
    return namespace["_dashboard_arka_plan_yukleme_callback"], state


def test_upload_callback_optimizes_and_updates_dashboard_background():
    source = io.BytesIO()
    Image.new("RGB", (3000, 2000), (40, 100, 160)).save(source, format="PNG")
    callback, state = _dashboard_background_functions(source.getvalue())

    callback()

    prefix, encoded = state["dashboard_arka_plan"].split(",", 1)
    assert prefix == "data:image/jpeg;base64"
    assert state["_dashboard_bg_upload_success"] is True
    with Image.open(io.BytesIO(base64.b64decode(encoded))) as processed:
        assert processed.format == "JPEG"
        assert processed.width <= 1920
        assert processed.height <= 1080


def test_invalid_dashboard_image_reports_error_without_success():
    callback, state = _dashboard_background_functions(b"not an image")

    callback()

    assert "dashboard_arka_plan" not in state
    assert "_dashboard_bg_upload_success" not in state
    assert "Görsel okunamadı" in state["_dashboard_bg_upload_error"]
