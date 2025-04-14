import logging
import pystray
import screeninfo
import sys
import threading
import time
import time
import tkinter as tk
import win32con
import win32gui

from config import OnComputerSleepOption
from PIL import Image, ImageDraw
from device_checker import are_peripherals_in_use
from event_listener import EventListener
from tkinter import messagebox
from win_32_pystray_icon import Win32PystrayIcon
from window_checker import is_any_app_fullscreen
import config


logging.basicConfig(
    filename="eye-rest-app.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class EyeRestApp:
    def __init__(self, root):
        self.root = root
        self.root.geometry("400x350")

        self.root.resizable(False, False)
        # self.root.iconbitmap("icon.ico")

        self.timer_running = False
        self.work_time = 20 * 60
        self.rest_time = 20
        self.timer_thread = None
        self.break_windows = []
        self.countdown_threads = []
        self.tray_icon = None
        self.in_meeting = False
        self.stop_event = threading.Event()
        self.sleep_event = threading.Event()
        self.locked_event = threading.Event()
        self.on_computer_sleep_option = config.load_config()
        self.event_listener = EventListener()

        # Create the UI
        self.title_label = tk.Label(root, text="Eye Rest Timer", font=("Arial", 18, "bold"))
        self.title_label.pack(pady=20)

        self.status_label = tk.Label(root, text="Timer is ready to start", font=("Arial", 12))
        self.status_label.pack(pady=10)

        self.time_label = tk.Label(root, text="Next break in: Not started", font=("Arial", 12))
        self.time_label.pack(pady=10)

        # Work time input
        self.work_time_frame = tk.Frame(root)
        self.work_time_frame.pack(pady=5)
        self.work_time_label = tk.Label(self.work_time_frame, text="Work Time (minutes):", font=("Arial", 10))
        self.work_time_label.pack(side=tk.LEFT)
        self.work_time_entry = tk.Entry(self.work_time_frame, width=5)
        self.work_time_entry.insert(0, "20")
        self.work_time_entry.pack(side=tk.LEFT)

        # Rest time input
        self.rest_time_frame = tk.Frame(root)
        self.rest_time_frame.pack(pady=5)
        self.rest_time_label = tk.Label(self.rest_time_frame, text="Rest Time (seconds):", font=("Arial", 10))
        self.rest_time_label.pack(side=tk.LEFT)
        self.rest_time_entry = tk.Entry(self.rest_time_frame, width=5)
        self.rest_time_entry.insert(0, "20")
        self.rest_time_entry.pack(side=tk.LEFT)

        self.start_button = tk.Button(root, text="Start Timer", command=self.start_timer, width=15, height=2, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        self.start_button.pack(pady=10)

        self.stop_button = tk.Button(root, text="Stop Timer", command=self.stop_timer,
                                     width=15, height=2, bg="#f44336", fg="white", font=("Arial", 10, "bold"))
        self.stop_button.pack(pady=10)
        self.stop_button.config(state=tk.DISABLED)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.create_tray_icon()


### Timer management

    def start_timer(self):
        try:
            self.work_time = int(self.work_time_entry.get()) * 60
            self.rest_time = int(self.rest_time_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for work and rest times.")
            return

        self.timer_running = True
        self.stop_event.clear()
        self.locked_event.clear()
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_label.config(text="Timer is running")

        # Start timer in a separate thread to keep UI responsive
        self.timer_thread = threading.Thread(target=self.timer_function)
        self.timer_thread.daemon = True
        self.timer_thread.start()

        logging.debug(f"Timer started")

        self.root.withdraw()
        self.setup_system_events()
        self.tray_icon.update_menu()


    def handle_tray_timer_button(self):
        if self.timer_running:
            self.stop_timer()
        else:
            self.start_timer()


    def stop_timer(self):
        self.timer_running = False
        self.stop_event.set()
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_label.config(text="Timer stopped")
        self.time_label.config(text="Next break in: Not started")

        for window in self.break_windows:
            if window.winfo_exists():
                window.destroy()

        self.break_windows = []
        self.countdown_threads = []

        logging.debug("Timer stopped")

        self.root.after(0, lambda: self.unregister_system_events())

        self.update_tray_icon_title("Not started")
        self.tray_icon.update_menu()


    def timer_function(self):
        while self.timer_running:
            remaining_seconds = self.work_time

            while remaining_seconds > 0 and self.timer_running and not self.locked_event.is_set():
                minutes, seconds = divmod(remaining_seconds, 60)
                time_str = f"Next break in: {minutes:02d}:{seconds:02d}"

                # Update label in the main thread
                try:
                    self.root.after(0, lambda s=time_str: self.time_label.config(text=s))
                    self.root.after(0, lambda s=time_str: self.update_tray_icon_title(s))
                except tk.TclError:
                    return

                time.sleep(1)
                remaining_seconds -= 1

            if not self.timer_running:
                break

            if self.can_show_break():
                self.stop_event.clear()

                try:
                    self.root.after(0, self.show_break_screens)
                except tk.TclError:
                    return

                time.sleep(self.rest_time)

                for window in self.break_windows:
                    if window.winfo_exists():
                        try:
                            self.root.after(0, window.destroy)
                        except tk.TclError:
                            logging.error("Error ocurred when closing break screens.")
                            return

                self.break_windows = []
                self.countdown_threads = []

                logging.debug("Break completed")
            else:
                logging.debug("Skipping break")
                time.sleep(1)


    def countdown_function(self, label, window):
        try:
            for i in range(self.rest_time, 0, -1):
                if self.stop_event.is_set():
                    break

                try:
                    window.update()
                    label.configure(text=str(i))
                except Exception:
                    break

                time.sleep(1)
        except Exception as e:
            logging.error(f"Error in countdown: {e}")


    def reset_timer(self):
        logging.debug("Resetting timer")
        self.work_time = int(self.work_time_entry.get()) * 60


### Window management

    def show_break_screens(self):
        monitors = screeninfo.get_monitors()
        logging.debug(f"Showing break screens. Found {len(monitors)} monitors.")

        for i, monitor in enumerate(monitors):
            window_title = f"Eye Rest Time! - Monitor {i}"

            break_window = tk.Toplevel(self.root)
            break_window.title(window_title)
            break_window.configure(bg="#3498db")
            minutes, seconds = divmod(self.rest_time, 60)

            rest_label = tk.Label(break_window,
                                text=f"REST YOUR EYES\n\nLook away from the screen\nFocus on something 20 feet away\n\nClosing in {minutes:02d}m{seconds:02d}s...",
                                font=("Arial", 24, "bold"), bg="#3498db", fg="white")
            rest_label.pack(expand=True)

            countdown_label = tk.Label(break_window, text=str(self.rest_time), font=("Arial", 48, "bold"),
                                    bg="#3498db", fg="white")
            countdown_label.pack(expand=True)

            break_window.update()

            hwnd = win32gui.FindWindow(None, window_title)

            if hwnd:
                # Set window style for full screen (no borders)
                style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
                win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style & ~(win32con.WS_CAPTION | win32con.WS_THICKFRAME))

                # Move to the correct monitor and resize
                win32gui.SetWindowPos(
                    hwnd,
                    win32con.HWND_TOPMOST,
                    monitor.x, monitor.y,
                    monitor.width, monitor.height,
                    win32con.SWP_SHOWWINDOW
                )
            else:
                logging.error(f"Could not find window with title: {window_title}")

            countdown_thread = threading.Thread(target=self.countdown_function, args=(countdown_label, break_window,))
            countdown_thread.daemon = True
            countdown_thread.start()

            self.break_windows.append(break_window)
            self.countdown_threads.append(countdown_thread)


    def create_icon_image(self):
        width = 64
        height = 64
        color = (66, 133, 244)

        image = Image.new('RGB', (width, height), color=(0, 0, 0))
        dc = ImageDraw.Draw(image)

        dc.ellipse([(8, 16), (width - 8, height - 16)], fill='white', outline='black')
        dc.ellipse([(24, 24), (width - 24, height - 24)], fill=color, outline='black')

        return image


    def create_tray_icon(self):
        image = self.create_icon_image()
        config_menu = pystray.Menu(
            pystray.MenuItem(
                OnComputerSleepOption.STOP_TIMER.value,
                action=lambda item: self.set_option(OnComputerSleepOption.STOP_TIMER),
                radio=True,
                checked=lambda item: self.on_computer_sleep_option == OnComputerSleepOption.STOP_TIMER),
            pystray.MenuItem(
                OnComputerSleepOption.RESET_TIMER.value,
                action=lambda item: self.set_option(OnComputerSleepOption.RESET_TIMER),
                radio=True,
                checked=lambda item: self.on_computer_sleep_option == OnComputerSleepOption.RESET_TIMER),
        )

        menu = (
            pystray.MenuItem("Open", self.open_window),
            pystray.MenuItem("Config", action=config_menu),
            pystray.MenuItem(lambda _: "Stop Timer" if self.timer_running else "Start Timer", self.handle_tray_timer_button),
            pystray.MenuItem("Exit", self.exit_app)
        )

        self.tray_icon = Win32PystrayIcon(
            "EyeRest",
            image,
            "Eye Rest - Not started",
            menu,
            **{ 'on_double_click': lambda icon, _: self.open_window(icon) } if sys.platform == "win32" else {}
        )

        self.tray_icon.run_detached()


    def set_option(self, option):
        self.on_computer_sleep_option = option
        config.save_config(option)
        logging.debug(f"On computer sleep option set to: {option.value}")


    def open_window(self, icon):
        self.root.after(0, self.root.deiconify)

    def update_tray_icon_title(self, title):
        if self.tray_icon:
            self.tray_icon.title = f"Eye Rest - {title}"


    def on_closing(self):
        self.root.withdraw()


    def can_show_break(self):
        peripherals_in_use = are_peripherals_in_use()
        full_screen = is_any_app_fullscreen()

        logging.debug(f"Peripherals in use: {peripherals_in_use}, Any app in full screen: {full_screen}, Stop event: {self.stop_event.is_set()}, Locked event: {self.locked_event.is_set()}, Timer running: {self.timer_running}")

        return not(peripherals_in_use or self.stop_event.is_set() or self.locked_event.is_set() or full_screen)


### Events

    def setup_system_events(self):
        self.event_listener.start(self.handle_system_event)


    def unregister_system_events(self):
        self.event_listener.stop()


    def handle_system_event(self, event_type):
        logging.debug(f"Handling system event: {event_type}")

        match event_type:
            case "lock":
                logging.debug("System event: Screen locked")
                self.locked_event.set()
            case "unlock":
                logging.debug("System event: Screen unlocked")
                self.reset_timer()
                self.locked_event.clear()
            case "suspend":
                logging.debug("System event: Screen suspended")
                self.handle_sleep()
            case "resume":
                logging.debug("System event: Screen resumed")
                self.handle_sleep()


    def handle_sleep(self):
        """
        The action is the same for both events, just in case.
        """

        if self.on_computer_sleep_option == OnComputerSleepOption.STOP_TIMER:
            self.stop_timer()
            logging.debug("Action: Stop timer")
        elif self.on_computer_sleep_option == OnComputerSleepOption.RESET_TIMER:
            self.reset_timer()
            logging.debug("Action: Reset timer")


    def exit_app(self, icon, item):
        self.timer_running = False
        self.stop_event.set()
        self.locked_event.set()

        icon.stop()

        self.unregister_system_events()
        self.root.after(0, lambda: self.root.destroy())
        logging.debug(f"Exiting app")



def main():
    root = tk.Tk()

    window_title = "Eye Rest Timer"
    existing_window = win32gui.FindWindow(None, window_title)

    if existing_window:
        win32gui.ShowWindow(existing_window, win32con.SW_SHOWNORMAL)
        win32gui.SetForegroundWindow(existing_window)
        logging.debug("Existing instance found, bringing to front.")
    else:
        root.title(window_title)
        EyeRestApp(root)
        root.mainloop()


if __name__ == "__main__":
    main()
