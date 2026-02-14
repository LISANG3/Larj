import importlib
import sys
import types
import unittest


class DummyListener:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def start(self):
        return None

    def stop(self):
        return None


class KeyCode:
    def __init__(self, char=None):
        self.char = char


class Key:
    ctrl = "ctrl"
    ctrl_l = "ctrl_l"
    ctrl_r = "ctrl_r"
    alt = "alt"
    alt_l = "alt_l"
    alt_r = "alt_r"
    shift = "shift"
    shift_l = "shift_l"
    shift_r = "shift_r"
    cmd = "cmd"
    cmd_l = "cmd_l"
    cmd_r = "cmd_r"
    space = "space"


class FakeConfigManager:
    def __init__(self, trigger_key="XButton1", fallback_keys=None, enabled=True):
        self._data = {
            "hotkey.trigger_key": trigger_key,
            "hotkey.fallback_keys": fallback_keys or ["Ctrl+Space"],
            "hotkey.enabled": enabled,
        }

    def get(self, key_path, default=None):
        return self._data.get(key_path, default)


class HotkeyListenerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fake_pyqt5 = types.ModuleType("PyQt5")
        fake_qtcore = types.ModuleType("PyQt5.QtCore")

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

        def pyqtSignal(*args, **kwargs):
            return DummySignal()

        fake_qtcore.QObject = DummyQObject
        fake_qtcore.pyqtSignal = pyqtSignal
        fake_qtcore.QTimer = object
        sys.modules["PyQt5"] = fake_pyqt5
        sys.modules["PyQt5.QtCore"] = fake_qtcore

        fake_pynput = types.ModuleType("pynput")
        fake_pynput.mouse = types.SimpleNamespace(Listener=DummyListener)
        fake_pynput.keyboard = types.SimpleNamespace(Listener=DummyListener, Key=Key, KeyCode=KeyCode)
        sys.modules["pynput"] = fake_pynput

        sys.modules.pop("src.core.hotkey_listener", None)
        cls.module = importlib.import_module("src.core.hotkey_listener")

    def test_mouse_trigger_matches_configured_button_only(self):
        listener = self.module.HotkeyListener(FakeConfigManager(trigger_key="XButton1"))
        triggered = []
        listener.hotkey_triggered.connect(lambda: triggered.append(True))

        listener.last_trigger_time = 0
        listener._on_mouse_click(0, 0, types.SimpleNamespace(name="left"), True)
        self.assertEqual(len(triggered), 0)

        listener.last_trigger_time = 0
        listener._on_mouse_click(0, 0, types.SimpleNamespace(name="x2"), True)
        self.assertEqual(len(triggered), 0)

        listener.last_trigger_time = 0
        listener._on_mouse_click(0, 0, types.SimpleNamespace(name="x1"), True)
        self.assertEqual(len(triggered), 1)

    def test_keyboard_fallback_shortcut_triggers(self):
        listener = self.module.HotkeyListener(FakeConfigManager(fallback_keys=["Ctrl+Space"]))
        triggered = []
        listener.hotkey_triggered.connect(lambda: triggered.append(True))

        listener.last_trigger_time = 0
        listener._on_key_press(Key.ctrl_l)
        listener._on_key_press(Key.space)

        self.assertEqual(len(triggered), 1)


if __name__ == "__main__":
    unittest.main()
