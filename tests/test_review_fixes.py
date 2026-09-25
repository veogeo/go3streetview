"""Offline checks for snapshot downloads and callback lifecycle changes."""
import ast
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
from urllib.parse import parse_qs, urlencode, urlsplit
import unittest
from unittest.mock import Mock

from test_webengine_startup import ROOT, method


class ReviewFixTests(unittest.TestCase):
    def download(self, status, data=b'image'):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        destination = Path(directory.name) / 'snapshot.jpg'
        response = Mock(status=status)
        response.read.side_effect = [data, b'']
        connection = Mock()
        connection.getresponse.return_value = response
        factory = Mock(return_value=connection)
        plugin = SimpleNamespace(
            pov={'lat': '1', 'lon': '2', 'heading': '3', 'pitch': '4'},
            parent=SimpleNamespace(APIkey='test&injected=value'),
        )
        save = method('saveImg', {
            'HTTPSConnection': factory, 'urlencode': urlencode,
            'core': Mock(), 'os': os,
        }, filename='snapshot.py', classname='snapShot')
        return save, plugin, destination, factory, connection

    def test_snapshot_uses_fixed_https_host_and_encodes_parameters(self):
        save, plugin, path, factory, connection = self.download(200)
        save(plugin, str(path))
        factory.assert_called_once_with('maps.googleapis.com', timeout=30)
        verb, target = connection.request.call_args.args
        self.assertEqual(verb, 'GET')
        self.assertEqual(urlsplit(target).path, '/maps/api/streetview')
        parameters = parse_qs(urlsplit(target).query)
        self.assertEqual(parameters['key'], ['test&injected=value'])
        self.assertNotIn('injected', parameters)
        self.assertEqual(path.read_bytes(), b'image')
        connection.close.assert_called_once_with()

    def test_redirect_or_error_cannot_overwrite_existing_snapshot(self):
        for status in (302, 403, 500):
            with self.subTest(status=status):
                save, plugin, path, factory, connection = self.download(status)
                path.write_bytes(b'original')
                with self.assertRaises(OSError):
                    save(plugin, str(path))
                self.assertEqual(path.read_bytes(), b'original')
                connection.request.assert_called_once()
                connection.close.assert_called_once_with()

    def test_connection_closed_on_network_error(self):
        save, plugin, path, factory, connection = self.download(200)
        connection.request.side_effect = TimeoutError('timeout')
        with self.assertRaises(TimeoutError):
            save(plugin, str(path))
        connection.close.assert_called_once_with()
        self.assertFalse(path.exists())

    def test_resize_connects_once_and_disconnects_only_its_callback(self):
        plugin = SimpleNamespace(
            _webengine_ready=True, pointWgs84=Mock(), actualPOV={'lat': 1},
            view=Mock(), resizeWidget=Mock(), refreshWidget=Mock(), endRefreshWidget=Mock(),
        )
        resize = method('resizeStreetview')
        resize(plugin)
        resize(plugin)
        plugin.view.SV.loadFinished.connect.assert_called_once_with(plugin.endRefreshWidget)
        method('endRefreshWidget')(plugin)
        plugin.view.SV.loadFinished.disconnect.assert_called_once_with(plugin.endRefreshWidget)
        self.assertFalse(plugin._resize_refresh_pending)

    def test_recursive_position_update_returns_without_canvas_changes(self):
        plugin = SimpleNamespace(_updating_position=True, apdockwidget=Mock())
        method('setPosition')(plugin)

    def test_runtime_has_no_silently_ignored_exceptions(self):
        for filename in ('go3streetview.py', 'go3streetviewDialog.py', 'snapshot.py'):
            tree = ast.parse((ROOT / filename).read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler):
                    self.assertIsNotNone(node.type, (filename, node.lineno))
                    self.assertFalse(all(isinstance(stmt, ast.Pass) for stmt in node.body),
                                     (filename, node.lineno))


if __name__ == '__main__':
    unittest.main()
