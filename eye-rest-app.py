import tkinter as tk
import time
import threading
import sys
import os
from tkinter import messagebox
from datetime import datetime, timedelta
import pystray
from PIL import Image, ImageDraw

class EyeRestApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Eye Rest Timer")
        self.root.geometry("400x350")
        self.root.resizable(False, False)

        # App variables
        self.timer_running = False
        self.work_time = 20 * 60  # Default 20 minutes
        self.rest_time = 20  # Default 20 seconds
        self.timer_thread = None
        self.break_window = None
        self.countdown_thread = None
        self.tray_icon = None

        # Set window to stay on top
        self.root.attributes("-topmost", True)

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
        self.work_time_entry.insert(0, "20")  # Default value
        self.work_time_entry.pack(side=tk.LEFT)

        # Rest time input
        self.rest_time_frame = tk.Frame(root)
        self.rest_time_frame.pack(pady=5)
        self.rest_time_label = tk.Label(self.rest_time_frame, text="Rest Time (seconds):", font=("Arial", 10))
        self.rest_time_label.pack(side=tk.LEFT)
        self.rest_time_entry = tk.Entry(self.rest_time_frame, width=5)
        self.rest_time_entry.insert(0, "20")  # Default value
        self.rest_time_entry.pack(side=tk.LEFT)

        self.start_button = tk.Button(root, text="Start Timer", command=self.start_timer,
                                     width=15, height=2, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        self.start_button.pack(pady=10)

        self.stop_button = tk.Button(root, text="Stop Timer", command=self.stop_timer,
                                     width=15, height=2, bg="#f44336", fg="white", font=("Arial", 10, "bold"))
        self.stop_button.pack(pady=10)
        self.stop_button.config(state=tk.DISABLED)
        
        # Handle window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def start_timer(self):
        try:
            self.work_time = int(self.work_time_entry.get()) * 60
            self.rest_time = int(self.rest_time_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for work and rest times.")
            return

        self.timer_running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_label.config(text="Timer is running")

        # Start timer in a separate thread to keep UI responsive
        self.timer_thread = threading.Thread(target=self.timer_function)
        self.timer_thread.daemon = True
        self.timer_thread.start()

        #minimize to tray
        self.root.withdraw()
        self.create_tray_icon()

    def stop_timer(self):
        self.timer_running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_label.config(text="Timer stopped")
        self.time_label.config(text="Next break in: Not started")

        # Close break window if it's open
        if self.break_window is not None and self.break_window.winfo_exists():
            self.break_window.destroy()
            self.break_window = None
        
        #destroy tray
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
        
        #reopen window
        self.root.deiconify()

    def timer_function(self):
        while self.timer_running:
            # Calculate and display the next break time
            next_break_time = datetime.now() + timedelta(seconds=self.work_time)

            # Count down until break time
            remaining_seconds = self.work_time
            while remaining_seconds > 0 and self.timer_running:
                minutes, seconds = divmod(remaining_seconds, 60)
                time_str = f"Next break in: {minutes:02d}:{seconds:02d}"

                # Update label in the main thread
                try:
                    self.root.after(0, lambda s=time_str: self.time_label.config(text=s))
                except tk.TclError:
                    #Window closed - exit thread
                    return

                time.sleep(1)
                remaining_seconds -= 1

            # If timer was stopped, exit the function
            if not self.timer_running:
                break

            # Create break window
            try:
                self.root.after(0, self.show_break_screen)
            except tk.TclError:
                # Window closed - exit thread
                return

            # Wait for break to complete
            time.sleep(self.rest_time)

            # Close break window
            if self.break_window is not None and self.break_window.winfo_exists():
                try:
                    self.root.after(0, self.break_window.destroy)
                    self.break_window = None
                except tk.TclError:
                    #Window closed - exit thread
                    return
                

    def show_break_screen(self):
        # Create full-screen break window
        self.break_window = tk.Toplevel(self.root)
        self.break_window.title("Eye Rest Time!")

        # Make it cover the full screen
        self.break_window.attributes("-fullscreen", True)
        self.break_window.attributes("-topmost", True)

        # Set background color
        self.break_window.configure(bg="#3498db")

        minutes, seconds = divmod(self.rest_time, 60)
        # Add rest message
        rest_label = tk.Label(self.break_window,
                             text=f"REST YOUR EYES\n\nLook away from the screen\nFocus on something 20 feet away\n\nClosing in {minutes:02d}m{seconds:02d}s...",
                             font=("Arial", 24, "bold"),
                             bg="#3498db", fg="white")
        rest_label.pack(expand=True)

        # Add countdown display
        countdown_label = tk.Label(self.break_window, text=str(self.rest_time), font=("Arial", 48, "bold"),
                                  bg="#3498db", fg="white")
        countdown_label.pack(expand=True)

        # Start countdown in a separate thread
        self.countdown_thread = threading.Thread(target=self.countdown_function, args=(countdown_label,))
        self.countdown_thread.daemon = True
        self.countdown_thread.start()

    def countdown_function(self, label):
        for i in range(self.rest_time, 0, -1):
            if not self.timer_running or self.break_window is None or not self.break_window.winfo_exists():
                break
            try:
                self.break_window.after(0, lambda t=str(i): label.config(text=t))
            except tk.TclError:
                #Window closed - exit thread
                return
            time.sleep(1)
    
    def create_icon_image(self):
        # Create a simple eye icon
        width = 64
        height = 64
        color = (66, 133, 244)  # Blue
        
        image = Image.new('RGB', (width, height), color=(0, 0, 0))
        dc = ImageDraw.Draw(image)
        
        # Draw a simple eye
        dc.ellipse([(8, 16), (width-8, height-16)], fill='white', outline='black')
        dc.ellipse([(24, 24), (width-24, height-24)], fill=color, outline='black')
        
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

    def open_window(self, icon, item):
        self.root.after(0, self.root.deiconify)

    def exit_app(self, icon, item):
        self.timer_running = False
        icon.stop()
        self.root.after(0, self.root.destroy)
        
    def on_closing(self):
        if self.timer_running:
            self.stop_timer()
        self.root.destroy()
        

# Function to run when the app starts
def main():
    root = tk.Tk()
    app = EyeRestApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
