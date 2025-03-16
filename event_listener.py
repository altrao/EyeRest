import win32con
import win32api
import win32gui
import ctypes
import time
import threading
import logging

logging.basicConfig(
    filename="eye-rest-app.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


# Constants
WM_WTSSESSION_CHANGE = 0x02B1
WTS_SESSION_LOCK = 0x7
WTS_SESSION_UNLOCK = 0x8
NOTIFY_FOR_THIS_SESSION = 0

# Power broadcast message
WM_POWERBROADCAST = 0x0218
PBT_APMSUSPEND = 0x0004
PBT_APMRESUMEAUTOMATIC = 0x0012
PBT_APMRESUMESUSPEND = 0x0007


class EventListener:
    def __init__(self):
        self.hwnd = None
        self.hinst = None
        self.class_atom = None
        self.class_name = "EventListenerClass"
        self.callback_function = None
        self.active = False
        self._listen_thread = None


    def _window_proc(self, hwnd, message, wparam, lparam):
        if message == WM_WTSSESSION_CHANGE:
            if wparam == WTS_SESSION_LOCK:
                self._callback("lock")
            elif wparam == WTS_SESSION_UNLOCK:
                self._callback("unlock")
        elif message == WM_POWERBROADCAST:
            if wparam == PBT_APMSUSPEND:
                self._callback("suspend")
            elif wparam == PBT_APMRESUMEAUTOMATIC or wparam == PBT_APMRESUMESUSPEND:
                self._callback("resume")

        return win32gui.DefWindowProc(hwnd, message, wparam, lparam)


    def _callback(self, message):
        if self.callback_function:
            self.callback_function(message)


    def start(self, callback_function):
        if self.class_atom and not self.active:
            self._start_thread()
            return

        self.callback_function = callback_function

        # Register window class
        self.hinst = win32api.GetModuleHandle(None)
        
        # Create window class
        wc = win32gui.WNDCLASS()
        wc.style = win32con.CS_VREDRAW | win32con.CS_HREDRAW
        wc.lpfnWndProc = self._window_proc
        wc.hInstance = self.hinst
        wc.hIcon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)
        wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        wc.hbrBackground = win32con.COLOR_WINDOW + 1
        wc.lpszClassName = self.class_name
        
        # Register class
        self.class_atom = win32gui.RegisterClass(wc)

        # Create window
        self.hwnd = win32gui.CreateWindow(
            self.class_name,
            "Event Listener",
            0,  # Hidden window
            0, 0, 0, 0,
            0, 0, self.hinst, None
        )

        # Register for session notifications
        result = ctypes.windll.wtsapi32.WTSRegisterSessionNotification(
            self.hwnd, 
            NOTIFY_FOR_THIS_SESSION
        )

        if not result:
            error = ctypes.GetLastError()
            logging.error(f"Failed to register for session notifications. Error code: {error}")
            return False

        self._start_thread()
        return True


    def _listen(self):
        try:
            while True:
                if not self.active:
                    time.sleep(5)
                    continue

                bRet, msg = win32gui.GetMessage(None, 0, 0)

                if bRet:
                    win32gui.TranslateMessage(msg)
                    win32gui.DispatchMessage(msg)

                time.sleep(0.1)
        finally:
            self.cleanup()


    def _start_thread(self):
        if not self._listen_thread or not self._listen_thread.is_alive():
            self._listen_thread = threading.Thread(target=self._listen)

        self._listen_thread.daemon = True
        self._listen_thread.start()
        self.active = True


    def stop(self):
        if (self._listen_thread):
            self._listen_thread.join(timeout=1)
            self._listen_thread = None

        self.active = False


    def cleanup(self):
        self.stop()

        if self.hwnd:
            ctypes.windll.wtsapi32.WTSUnRegisterSessionNotification(self.hwnd)
