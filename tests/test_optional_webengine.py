"""Exercise installations without the optional WebEngine bindings."""
import ast
import builtins
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from test_webengine_startup import ROOT, method


class OptionalWebEngineTests(unittest.TestCase):
    def test_missing_module_is_recorded_without_aborting_import(self):
        tree = ast.parse((ROOT / 'go3streetview.py').read_text())
        start = next(i for i, node in enumerate(tree.body)
                     if isinstance(node, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id == 'WEBENGINE_IMPORT_ERROR' for t in node.targets))
        statements = tree.body[start:start + 3]
        imports = []

        def missing_import(name, *args, **kwargs):
            imports.append(name)
            raise ModuleNotFoundError("No module named 'PyQt6.QtWebEngineWidgets'")

        scope = {'__builtins__': dict(vars(builtins), __import__=missing_import)}
        exec(compile(ast.Module(body=statements, type_ignores=[]), '<optional-import>', 'exec'), scope)
        self.assertFalse(scope['WEBENGINE_AVAILABLE'])
        self.assertIn('QtWebEngineWidgets', scope['WEBENGINE_IMPORT_ERROR'])
        self.assertEqual(imports, ['qgis.PyQt.QtWebEngineWidgets'])

    def test_missing_engine_does_not_create_any_widgets(self):
        self.assertFalse(method('ensureWebEngine', {'WEBENGINE_AVAILABLE': False})(SimpleNamespace()))

    def test_open_panorama_falls_back_without_accessing_embedded_view(self):
        plugin = SimpleNamespace(ensureWebEngine=Mock(return_value=False),
                                 notifyExternalBrowserMode=Mock(), openInBrowserOnCTRLClick=Mock())
        method('openSVDialog')(plugin)
        plugin.openInBrowserOnCTRLClick.assert_called_once_with()
        plugin.notifyExternalBrowserMode.assert_called_once_with()

    def test_toolbar_activates_map_tool_without_dock(self):
        plugin = SimpleNamespace(notifyExternalBrowserMode=Mock(), explore=Mock())
        method('StreetviewRun', {'WEBENGINE_AVAILABLE': False})(plugin)
        plugin.explore.assert_called_once_with()

    def test_nearest_panorama_query_returns_without_waiting_or_opening_browser(self):
        result = method('getNearestSVLocation', {'WEBENGINE_AVAILABLE': False})(SimpleNamespace(), 1, 2)
        self.assertIsNone(result)

    def test_external_mode_message_is_shown_once(self):
        plugin = SimpleNamespace(iface=Mock(), tr=lambda text: text)
        notify = method('notifyExternalBrowserMode', {
            'core': Mock(), 'WEBENGINE_IMPORT_ERROR': 'missing WebEngine',
        })
        notify(plugin)
        notify(plugin)
        plugin.iface.messageBar.return_value.pushWarning.assert_called_once()


if __name__ == '__main__':
    unittest.main()
