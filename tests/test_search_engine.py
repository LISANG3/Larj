import importlib
import sys
import types
import unittest
from pathlib import Path


class DummySignal:
    def __init__(self):
        self._handlers = []

    def connect(self, handler):
        self._handlers.append(handler)

    def emit(self, *args, **kwargs):
        for handler in self._handlers:
            handler(*args, **kwargs)


class DummyQObject:
    def __init__(self, *args, **kwargs):
        super().__init__()


class DummyQThread:
    def __init__(self, *args, **kwargs):
        super().__init__()


class DummyQTimer:
    def __init__(self, *args, **kwargs):
        self.timeout = DummySignal()

    def setSingleShot(self, value):
        return None

    def stop(self):
        return None

    def start(self, value):
        return None


def pyqtSignal(*args, **kwargs):
    return DummySignal()


class FakeConfigManager:
    def __init__(self, values=None):
        self.values = values or {}

    def get(self, key_path, default=None):
        return self.values.get(key_path, default)


class SearchEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fake_pyqt5 = types.ModuleType("PyQt5")
        fake_qtcore = types.ModuleType("PyQt5.QtCore")
        fake_qtcore.QObject = DummyQObject
        fake_qtcore.pyqtSignal = pyqtSignal
        fake_qtcore.QTimer = DummyQTimer
        fake_qtcore.QThread = DummyQThread
        sys.modules["PyQt5"] = fake_pyqt5
        sys.modules["PyQt5.QtCore"] = fake_qtcore

        sys.modules.pop("src.core.search_engine", None)
        cls.module = importlib.import_module("src.core.search_engine")

    def test_default_es_path_is_project_relative(self):
        engine = self.module.SearchEngine(FakeConfigManager())
        expected = (Path(__file__).resolve().parents[1] / "everything" / "es.exe").resolve()
        self.assertEqual(engine.es_path, expected)

    def test_relative_configured_es_path_is_resolved_from_project_root(self):
        engine = self.module.SearchEngine(FakeConfigManager({"search.es_path": "bin/es.exe"}))
        expected = (Path(__file__).resolve().parents[1] / "bin" / "es.exe").resolve()
        self.assertEqual(engine.es_path, expected)

    def test_tilde_configured_es_path_expands_user_home(self):
        engine = self.module.SearchEngine(FakeConfigManager({"search.es_path": "~/bin/es.exe"}))
        expected = Path("~/bin/es.exe").expanduser()
        self.assertEqual(engine.es_path, expected)


if __name__ == "__main__":
    unittest.main()
