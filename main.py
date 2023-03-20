import platform
import threading
import os 
from dotenv import load_dotenv
from modules.watchdog_handler import logCheck
from modules.windows_event_handler import windows_event_log_check

def main():
    load_dotenv()
    logPath = os.environ.get('CheckPath')
    viewerPath = os.environ.get('ViewerPath')
    managerPath = os.environ.get('ManagerPath')

    if logPath:
        filecheckThread = threading.Thread(target=logCheck, args=(logPath,))
        filecheckThread.start()

    if viewerPath:
        viewerCheckThread = threading.Thread(target=logCheck, args=(logPath,))
        viewerCheckThread.start()

    if managerPath:
        managerCheckThread = threading.Thread(target=logCheck, args=(logPath,))
        managerCheckThread.start()

    if platform.system() == 'Windows':
        winEventLogThread = threading.Thread(target=windows_event_log_check)
        winEventLogThread.start()

if __name__ == "__main__":
    main()
