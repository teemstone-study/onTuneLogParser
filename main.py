import platform
import threading
import os 
import yaml
from dotenv import load_dotenv
from multiprocessing.dummy import Pool as ThreadPool
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
    createDirectory(file_fullpath + "\\temp")

def working(work):
    if "monitoring" in work and "file" in work["monitoring"]:
        if "type" not in work or work["type"] == "normal":
            logCheck(work)
        elif work["type"] == "windows-event" and platform.system() == 'Windows':
            windows_event_log_check(work)

def workThread(worklist, threadnum=1):
    pool = ThreadPool(threadnum)
    result = pool.map(working, worklist)
    pool.close()
    pool.join()

    return result

def main():
    create_Dir()
    _config = load_Yaml()

    # Dir Check Thread Create
    data = _config['data']
    result = workThread(data, len(data))
    print(result)

if __name__ == "__main__":
    main()
