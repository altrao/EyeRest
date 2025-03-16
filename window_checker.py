import win32gui
import win32api
import win32con

def is_any_app_fullscreen():
    foreground_window = win32gui.GetForegroundWindow()
    
    if not foreground_window:
        return False
    
    window_rect = win32gui.GetWindowRect(foreground_window)
    window_width = window_rect[2] - window_rect[0]
    window_height = window_rect[3] - window_rect[1]
    
    monitor_info = win32api.GetMonitorInfo(win32api.MonitorFromWindow(foreground_window, win32con.MONITOR_DEFAULTTONEAREST))
    monitor_rect = monitor_info['Monitor']
    
    monitor_width = monitor_rect[2] - monitor_rect[0]
    monitor_height = monitor_rect[3] - monitor_rect[1]
    
    # placement = win32gui.GetWindowPlacement(foreground_window)
    # is_maximized = placement[1] == win32con.SW_SHOWMAXIMIZED
    
    # Check if the foreground window covers the entire monitor
    is_covering_screen = (window_width >= monitor_width and window_height >= monitor_height)

    window_class = win32gui.GetClassName(foreground_window)
    window_text = win32gui.GetWindowText(foreground_window)
    
    # Exclude desktop and shell windows
    is_not_system_ui = (
        window_class.lower() not in ['progman', 'workerw', 'shell_traywnd'] and
        'desktop' not in window_text.lower()
    )
    
    return is_covering_screen and is_not_system_ui
