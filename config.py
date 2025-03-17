import json
import os
from enum import Enum
import logging

if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(filename)s - %(message)s')


class OnComputerSleepOption(Enum):
    STOP_TIMER = "Stop timer"
    RESET_TIMER = "Reset timer"

config_dir = os.path.join(os.getenv('APPDATA'), 'EyeRest', 'config')
config_file_path = os.path.join(config_dir, 'config.json')

def load_config():
    try:
        os.makedirs(config_dir, exist_ok=True)

        with open(config_file_path, "r") as f:
            config_data = json.load(f)
            loaded_option = config_data.get("on_computer_sleep_option")

            if loaded_option:
                logging.debug(f"Loaded on_computer_sleep_option from config: {loaded_option}")
                return OnComputerSleepOption(loaded_option)
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        logging.debug("Failed to load config from file, using default option.")

    return OnComputerSleepOption.RESET_TIMER


def save_config(on_computer_sleep_option):
    logging.debug(f"Saving on_computer_sleep_option to config: {on_computer_sleep_option.value}")

    try:
        os.makedirs(config_dir, exist_ok=True)

        with open(config_file_path, "w") as f:
            json.dump({"on_computer_sleep_option": on_computer_sleep_option.value}, f)
    except IOError:
        logging.error("Failed to save config to file.")
