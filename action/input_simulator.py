# File: action/input_simulator.py

import time
import threading
import pyautogui
import pynput
from typing import Optional, Dict, Any, List

class InputSimulator:
    """
    İnsan benzeri fare, klavye ve gamepad otomasyonunu sağlar.
    Oyun ve uygulama için gelişmiş input gönderme yeteneği.
    """

    def __init__(self):
        pyautogui.FAILSAFE = False
        self.keyboard = pynput.keyboard.Controller()
        self.mouse = pynput.mouse.Controller()
        # Gamepad eklemek için ek modül/plugin eklenebilir (ör: vgamepad, directinput)

    # FARE
    def move_mouse(self, x: int, y: int, duration: float = 0.0):
        """Mouse imleci verilen koordinata yumuşak geçişle gider."""
        pyautogui.moveTo(x, y, duration=duration)

    def click(self, x: Optional[int] = None, y: Optional[int] = None, button: str = "left", clicks: int = 1):
        """Verilen konumda tıklama yapar."""
        if x is not None and y is not None:
            pyautogui.click(x=x, y=y, clicks=clicks, button=button)
        else:
            pyautogui.click(clicks=clicks, button=button)

    def drag(self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.2, button: str = "left"):
        """Fareyi verilen iki nokta arasında sürükler."""
        pyautogui.moveTo(x1, y1)
        pyautogui.dragTo(x2, y2, duration=duration, button=button)

    # KLAVYE
    def type_text(self, text: str, interval: float = 0.05):
        """Verilen metni tek tek tuşlayarak yazar."""
        pyautogui.typewrite(text, interval=interval)

    def press_key(self, key: str, hold: float = 0.1):
        """Bir tuşa basar ve istenirse tutar."""
        self.keyboard.press(key)
        time.sleep(hold)
        self.keyboard.release(key)

    def combo(self, keys: List[str], hold: float = 0.05):
        """Birden fazla tuşa birlikte basar (ör: ctrl+alt+del)."""
        for k in keys:
            self.keyboard.press(k)
        time.sleep(hold)
        for k in reversed(keys):
            self.keyboard.release(k)

    # GAMEPAD (örnek stub, ileri modüllerle genişletilebilir)
    def gamepad_button(self, btn: str):
        """Gamepad tuşuna basar (geliştirilebilir)."""
        # vgamepad, directinput gibi modüllerle implement edilebilir.
        pass

    # Windows özel otomasyon (isteğe bağlı)
    def screenshot(self, path: str = "screen.png"):
        pyautogui.screenshot(path)

    # Makro oynatma (json ile kaydedilmiş hareketleri uygular)
    def play_macro(self, actions: List[Dict[str, Any]]):
        for act in actions:
            t = act.get("type")
            if t == "move_mouse":
                self.move_mouse(**act["params"])
            elif t == "click":
                self.click(**act["params"])
            elif t == "type_text":
                self.type_text(**act["params"])
            elif t == "press_key":
                self.press_key(**act["params"])
            elif t == "combo":
                self.combo(**act["params"])
            elif t == "drag":
                self.drag(**act["params"])
            elif t == "screenshot":
                self.screenshot(**act["params"])
            # Gamepad ve ileri eylemler eklenebilir
            time.sleep(act.get("delay", 0.01))
