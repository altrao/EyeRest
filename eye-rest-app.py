import tkinter as tk
import time
import threading
from tkinter import messagebox
import pystray
from PIL import Image, ImageDraw
import screeninfo
import logging
from device_checker import are_peripherals_in_use
from event_listener import EventListener


logging.basicConfig(
    filename="eye-rest-app.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

class EyeRestApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Eye Rest Timer")
        self.root.geometry("400x350")

        self.root.resizable(False, False)
        # self.root.iconbitmap(os.path.join(os.getcwd(), "icon.ico"))

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

        self.root.attributes("-topmost", True)

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

        logging.info(f"Timer started")

        self.root.withdraw()
        self.create_tray_icon()
        self.setup_system_events()


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

        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None

        self.unregister_system_events()
        self.root.deiconify()


    def timer_function(self):
        while self.timer_running:
            remaining_seconds = self.work_time

            while remaining_seconds > 0 and self.timer_running and not self.locked_event.is_set():
                minutes, seconds = divmod(remaining_seconds, 60)
                time_str = f"Next break in: {minutes:02d}:{seconds:02d}"

                # Update label in the main thread
                try:
                    self.root.after(0, lambda s=time_str: self.time_label.config(text=s))
                except tk.TclError:
                    return

                time.sleep(1)
                remaining_seconds -= 1

            if not self.timer_running:
                break

            if self.can_show_break():
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
                self.stop_event.set()
                self.countdown_threads = []

                logging.debug("Break completed")
            else:
                logging.debug("Skipping break")
                time.sleep(1)


    def countdown_function(self, label, window):
        logging.debug("Countdown thread started")

        for i in range(self.rest_time, 0, -1):
            if self.stop_event.is_set() or not self.timer_running or self.locked_event.is_set() or window is None or not window.winfo_exists():
                break
            try:
                window.after(0, lambda t=str(i): label.config(text=t))
            except tk.TclError:
                return

            time.sleep(1)
            
        logging.debug("Countdown thread finished")


    def reset_timer(self):
        logging.debug("Resetting timer")
        self.work_time = int(self.work_time_entry.get()) * 60


### Window management

    def show_break_screens(self):
        monitors = screeninfo.get_monitors()

        logging.debug(f"Showing break screens. Found {len(monitors)} monitors. Total threads: {threading.active_count()}")

        for monitor in monitors:
            break_window = tk.Toplevel(self.root)
            break_window.title("Eye Rest Time!")
            break_window.attributes("-topmost", True)

            break_window.geometry(f"{monitor.width}x{monitor.height}+{monitor.x}+{monitor.y}")
            break_window.attributes("-fullscreen", True)

            break_window.configure(bg="#3498db")

            minutes, seconds = divmod(self.rest_time, 60)

            rest_label = tk.Label(break_window,
                                  text=f"REST YOUR EYES\n\nLook away from the screen\nFocus on something 20 feet away\n\nClosing in {minutes:02d}m{seconds:02d}s...",
                                  font=("Arial", 24, "bold"),
                                  bg="#3498db", fg="white")
            rest_label.pack(expand=True)

            # Add countdown display
            countdown_label = tk.Label(break_window, text=str(self.rest_time), font=("Arial", 48, "bold"),
                                       bg="#3498db", fg="white")
            countdown_label.pack(expand=True)

            # Start countdown in a separate thread
            countdown_thread = threading.Thread(target=self.countdown_function, args=(countdown_label, break_window,))
            countdown_thread.daemon = True
            countdown_thread.start()
            self.countdown_threads.append(countdown_thread)
            logging.debug(f"Countdown thread started for monitor {monitor.name}. Total threads: {threading.active_count()}")

            self.break_windows.append(break_window)


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
        menu = (
            pystray.MenuItem("Open", self.open_window),
            pystray.MenuItem("Stop Timer", self.stop_timer),
            pystray.MenuItem("Exit", self.exit_app)
        )
        self.tray_icon = pystray.Icon("EyeRest", image, "Eye Rest", menu)
        self.tray_icon.run_detached()


    def open_window(self):
        self.root.after(0, self.root.deiconify)


    def on_closing(self):
        if self.timer_running:
            self.stop_timer()

        self.unregister_system_events()
        self.root.destroy()

        logging.debug("Window closing")


    def can_show_break(self):
        return not(are_peripherals_in_use() or self.stop_event.is_set() or self.locked_event.is_set())


### System events

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


    def exit_app(self, icon, item):
        self.timer_running = False
        self.stop_event.set()
        self.locked_event.set()

        icon.stop()

        self.unregister_system_events()
        self.root.after(0, lambda: self.root.destroy())
        logging.info(f"Exiting app")



def main():
    root = tk.Tk()
    EyeRestApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
