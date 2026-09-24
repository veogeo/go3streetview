"""Headless regression checks; these do not exercise native Qt/Chromium.

Extract methods with AST so the checks can run without importing QGIS.
Run: python3 -m unittest discover -s tests -v
"""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def method(name, namespace=None):
    tree = ast.parse((ROOT / 'go3streetview.py').read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'go3streetview')
    node = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == name)
    scope = {} if namespace is None else namespace
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(ROOT / 'go3streetview.py'), 'exec'), scope)
    return scope[name]


class WebEngineStartupTests(unittest.TestCase):
    def test_designer_ui_cannot_create_chromium(self):
        root = ET.parse(ROOT / 'ui_go3streetview.ui').getroot()
        for name in ('SV', 'BE'):
            widget = root.find(f".//widget[@name='{name}']")
            self.assertEqual(widget.attrib['class'], 'QWidget')
            self.assertIsNone(widget.find("property[@name='url']"))
        self.assertIsNone(root.find(".//customwidget[class='QWebEngineView']"))

    def test_first_use_configures_both_views_and_reuses_them(self):
        view = Mock()
        plugin = SimpleNamespace(_webengine_ready=False, view=view)
        snapshot = Mock(side_effect=lambda parent: SimpleNamespace(webview=parent.view.SV))
        channel = Mock()
        ensure = method('ensureWebEngine', {
            'snapShot': snapshot, 'QWebChannel': channel, 'web_attr': lambda name: name,
        })
        ensure(plugin)
        ensure(plugin)
        view.initializeWebViews.assert_called_once_with()
        snapshot.assert_called_once_with(plugin)
        self.assertIs(plugin.snapshotOutput.webview, view.SV)
        channel.assert_called_once_with()
        channel.return_value.registerObject.assert_called_once_with('backend', plugin)
        for browser in (view.SV, view.BE):
            browser.page.return_value.setWebChannel.assert_called_once_with(plugin.channel)
            browser.settings.return_value.setAttribute.assert_any_call('JavascriptEnabled', True)
            browser.settings.return_value.setAttribute.assert_any_call('LocalContentCanAccessRemoteUrls', True)
        self.assertTrue(plugin._webengine_ready)

    def test_early_resize_and_project_info_do_not_touch_webengine(self):
        # Any access beyond the readiness flag would raise AttributeError.
        plugin = SimpleNamespace(_webengine_ready=False)
        method('resizeStreetview')(plugin)
        method('infoLayerDefinedAction')(plugin)

    def test_open_initializes_before_accessing_browser(self):
        class StopAfterInitialization(Exception):
            pass
        initialize = Mock(side_effect=StopAfterInitialization)
        plugin = SimpleNamespace(ensureWebEngine=initialize)
        with self.assertRaises(StopAfterInitialization):
            method('openSVDialog')(plugin)
        initialize.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
