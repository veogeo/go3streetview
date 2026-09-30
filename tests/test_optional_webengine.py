"""Exercise installations without the optional WebEngine bindings."""
import ast
import builtins
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from test_webengine_startup import ROOT, method


class OptionalWebEngineTests(unittest.TestCase):
    def test_native_crash_workaround_targets_running_windows_qt(self):
        tree = ast.parse((ROOT / 'go3streetview.py').read_text())
        guard = next(n for n in tree.body if isinstance(n, ast.If)
                     and 'sys.platform' in ast.unparse(n.test))
        for platform, version, expected in (
            ('win32', '6.11.1', False), ('win32', '5.15.2', True),
            ('linux', '6.11.1', True), ('darwin', '6.11.1', True),
        ):
            with self.subTest(platform=platform, version=version):
                scope = {'sys': SimpleNamespace(platform=platform),
                         'qVersion': lambda: version, 'WEBENGINE_AVAILABLE': True}
                exec(compile(ast.Module(body=[guard], type_ignores=[]), '<platform>', 'exec'), scope)
                self.assertEqual(scope['WEBENGINE_AVAILABLE'], expected)

    def test_external_url_preserves_coordinates_and_heading(self):
        browser = Mock()
        point = SimpleNamespace(x=lambda: 12.5, y=lambda: 41.9)
        method('openInBrowserOnCTRLClick', {'webbrowser': browser})(
            SimpleNamespace(pointWgs84=point, heading=123))
        url = browser.open.call_args.args[0]
        self.assertIn('cbll=41.9,12.5', url)
        self.assertIn('cbp=12,123,0,0,0', url)

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
