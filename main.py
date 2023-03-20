import win32evtlog as wevt
import win32event
import datetime
import locale
import threading
import os 
from dotenv import load_dotenv
from modules.watchdog_handler import logCheck
from modules.drain_handler import DrainHandler

# Global variables
server = 'localhost'
logtype = 'System'
file_fullpath = os.path.dirname(os.path.abspath(__file__))
filename = file_fullpath + "\\eventlog.txt"

def init_make_eventlog_file():
    #current_locale = os.popen('systeminfo | findstr /B /C:"System Locale"').read()
    #current_locale = locale.getlocale(locale.LC_CTYPE)

    today = datetime.datetime.now().date()
    day_ago = today - datetime.timedelta(days=1)

    hand = wevt.OpenEventLog(server,logtype)
    flags = wevt.EVENTLOG_FORWARDS_READ|wevt.EVENTLOG_SEQUENTIAL_READ
    #total = wevt.GetNumberOfEventLogRecords(hand)
    #parent_directory = os.path.dirname(file_fullpath)

    while True:
        events = wevt.ReadEventLog(hand, flags, 0)
        if len(events) == 0:
            break
        if events:
            f = open(filename, 'a', encoding='UTF8')
            for evt in events:
                if str(evt.TimeGenerated)[:10] == str(today):
                    # print('Event Category:', evt.EventCategory)
                    # print('Time Generated:', evt.TimeGenerated)
                    # print('Source Name:', evt.SourceName)
                    # print('Event ID:', idResult)
                    # print('Event Type:', evt.EventType) 
                    # 1 : 오류 2: 경고 4 : 정보

                    idResult = evt.EventID & 0x0000FFFF
                    wevt.EVENTLOG_ERROR_TYPE
                    data = evt.StringInserts
                    eventdata = ""
                    if data != None:
                        for msg in data:
                            eventdata += msg
                            
                    logstring = f"[{evt.TimeGenerated}] [{evt.EventCategory}][{evt.SourceName}] [{idResult}] [{evt.EventType}]  [{eventdata}]"  
                    f.write(logstring + "\n")
                        
                    # if data:
                    #     print('Event Data:')
                    #     for msg in data:
                    #         print(msg)
                    # print('*' * 100)
                elif str(evt.TimeGenerated)[:10] == str(day_ago):
                    break
            f.close()

    flags = wevt.EVENTLOG_BACKWARDS_READ|wevt.EVENTLOG_SEQUENTIAL_READ
    return wevt.GetNumberOfEventLogRecords(hand)

def refresh_eventlog(inittotal, drain_handler):
    oldtotal = inittotal
    while True:
        hand = wevt.OpenEventLog(server,logtype)
        flags = wevt.EVENTLOG_BACKWARDS_READ|wevt.EVENTLOG_SEQUENTIAL_READ
        newtotal = wevt.GetNumberOfEventLogRecords(hand)

        if oldtotal != newtotal:
            today = datetime.datetime.now().date()
            day_ago = today - datetime.timedelta(days=1)

            events = wevt.ReadEventLog(hand, flags, 0, newtotal - oldtotal)
            if events:
                filename = file_fullpath + "\\eventlog.txt"
                f = open(filename, 'a', encoding='UTF8')
                for evt in events:
                    if str(evt.TimeGenerated)[:10] == str(today):
                        # print('Event Category:', evt.EventCategory)
                        # print('Time Generated:', evt.TimeGenerated)
                        # print('Source Name:', evt.SourceName)
                        # print('Event ID:', idResult)
                        # print('Event Type:', evt.EventType) 
                        # 1 : 오류 2: 경고 4 : 정보
                        idResult = evt.EventID & 0x0000FFFF
                        wevt.EVENTLOG_ERROR_TYPE
                        data = evt.StringInserts
                        eventdata = ""
                        for msg in data:
                                eventdata += msg
                            
                        logstring = f"[{evt.TimeGenerated}] [{evt.EventCategory}][{evt.SourceName}] [{idResult}] [{evt.EventType}]  [{eventdata}]"  
                            
                        f.write(logstring + "\n")
                        
                        drain_handler.handle(logstring)
                        # if data:
                        #     print('Event Data:')
                        #     for msg in data:
                        #         print(msg)
                        # print('*' * 100)
                    elif str(evt.TimeGenerated)[:10] == str(day_ago):
                        break
                f.close()

                drain_handler.report()

                oldtotal += len(events)

def main():
    load_dotenv()
    logPath = os.environ.get('CheckPath')

    filecheckThread = threading.Thread(target=logCheck, args=(logPath,))
    filecheckThread.start()

    init_total = init_make_eventlog_file()
    drain_handler = DrainHandler(filename)

    refresh_eventlog(init_total, drain_handler)


if __name__ == "__main__":
    main()
