import winreg

def _is_device_busy(device_key):
    """Checks if a specific device (microphone or webcam) is in use."""
    try:
        i = 0
        while True:
            try:
                sub_key_name = winreg.EnumKey(device_key, i)
                sub_key = winreg.OpenKey(device_key, sub_key_name)
                last_used_time_stop = winreg.QueryValueEx(sub_key, "LastUsedTimeStop")[0]

                if last_used_time_stop == 0:
                    winreg.CloseKey(sub_key)
                    winreg.CloseKey(device_key)
                    return True

                winreg.CloseKey(sub_key)
                i += 1
            except OSError:
                break  # No more subkeys
        winreg.CloseKey(device_key)

    except FileNotFoundError:
        pass  # Key doesn't exist, assume not in use
    return False

def are_peripherals_in_use():
    """Checks if microphone or webcam are in use by querying the Windows registry.

    Returns:
        bool: True if either device is in use, False otherwise.
    """

    microphone_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone\NonPackaged")
    webcam_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\webcam\NonPackaged")

    return _is_device_busy(microphone_key) or _is_device_busy(webcam_key)
