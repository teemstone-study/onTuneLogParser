import platform
import threading
import os 
import yaml
from dotenv import load_dotenv
from modules.watchdog_handler import logCheck
from modules.windows_event_handler import windows_event_log_check


def load_Yaml():
    with open('.\config\Setting.yaml', encoding='UTF-8') as f:
        _config = yaml.load(f, Loader=yaml.FullLoader)

    return _config

def createDirectory(directory):
    try:
        if not os.path.exists(directory):
            os.makedirs(directory)
    except OSError:
        print("Error: Failed to create the directory.")

def create_Dir():
    file_fullpath = os.path.dirname(os.path.abspath(__file__))
    createDirectory(file_fullpath + "\\output\\windows_event_log")
    createDirectory(file_fullpath + "\\output\\result")

def main():
    create_Dir()
    _config = load_Yaml()

    # Dir Check Thread Create
    checkThreads = [] # 추후 헬스체크등을 위해 좀 관리해둘 필요가 있을 것으로 생각됨...방식은 아직 미정...
    for item in _config['data']:
        if "monitoring" in item and "file" in item["monitoring"]:
            if "type" not in item or item["type"] == "normal":
                filecheckThread = threading.Thread(target=logCheck, args=(item,))
                filecheckThread.start()
                checkThreads.append(filecheckThread)
            elif item["type"] == "windows-event" and platform.system() == 'Windows':
                winEventLogThread = threading.Thread(target=windows_event_log_check, args=(item,))
                winEventLogThread.start()
                checkThreads.append(winEventLogThread)

if __name__ == "__main__":
    main()
