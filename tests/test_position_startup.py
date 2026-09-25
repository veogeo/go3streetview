"""Regression checks for dock callbacks before lazy WebEngine initialization."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]


def plugin_method(name, scope=None):
    tree = ast.parse((ROOT / 'go2streetview.py').read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'go2streetview')
    node = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == name)
    namespace = {} if scope is None else dict(scope)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(ROOT / 'go2streetview.py'), 'exec'), namespace)
    return namespace[name]


class PositionStartupTests(unittest.TestCase):
    def test_canvas_signal_before_first_panorama_does_not_touch_placeholders(self):
        plugin = SimpleNamespace(_webengine_ready=False,
                                 view=SimpleNamespace(SV=object(), BE=object()))
        plugin_method('setPosition')(plugin, 1000)

    def test_toolbar_visibility_callback_before_first_panorama(self):
        plugin = SimpleNamespace(
            _webengine_ready=False, view=SimpleNamespace(SV=object(), BE=object()),
            apdockwidget=Mock(), StreetviewAction=Mock(), explore=Mock(),
            infoBoxManager=Mock(),
        )
        plugin.infoBoxManager.isEnabled.return_value = False
        plugin.apdockwidget.isVisible.return_value = False
        plugin.setPosition = lambda: plugin_method('setPosition')(plugin)
        visibility = plugin_method('apdockChangeVisibility', {
            'QtGui': SimpleNamespace(QIcon=lambda path: path),
            'os': __import__('os'), '__file__': str(ROOT / 'go2streetview.py'),
        })
        plugin.apdockwidget.show.side_effect = lambda: visibility(plugin, True)
        plugin_method('StreetviewRun')(plugin)
        plugin.apdockwidget.show.assert_called_once_with()
        plugin.explore.assert_called_once_with()

    def test_panorama_initializes_engine_before_touching_view(self):
        class InitializationReached(Exception):
            pass
        initialize = Mock(side_effect=InitializationReached)
        plugin = SimpleNamespace(ensureWebEngine=initialize)
        with self.assertRaises(InitializationReached):
            plugin_method('openSVDialog')(plugin)
        initialize.assert_called_once_with()

    def test_ready_engine_still_checks_dock_visibility(self):
        plugin = SimpleNamespace(_webengine_ready=True, apdockwidget=Mock())
        plugin.apdockwidget.isVisible.return_value = False
        plugin_method('setPosition')(plugin)
        plugin.apdockwidget.isVisible.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
