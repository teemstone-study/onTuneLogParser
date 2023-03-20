import os
import win32evtlog as wevt
import datetime
from modules.drain_handler import DrainHandler

class WindowsEventHandler():
    def __init__(self):
        self.server = 'localhost'
        self.logtype = 'System'

        file_fullpath = os.path.dirname(os.path.abspath(__file__))
        self.filename = file_fullpath + "\\..\\windows_event_log\\eventlog.txt"
        #current_locale = os.popen('systeminfo | findstr /B /C:"System Locale"').read()
        #current_locale = locale.getlocale(locale.LC_CTYPE)
        #total = wevt.GetNumberOfEventLogRecords(hand)
        #parent_directory = os.path.dirname(file_fullpath)

        self.init_get_event()

    def init_get_event(self):
        today = datetime.datetime.now().date()
        day_ago = today - datetime.timedelta(days=1)
        hand = wevt.OpenEventLog(self.server,self.logtype)
        flags = wevt.EVENTLOG_FORWARDS_READ|wevt.EVENTLOG_SEQUENTIAL_READ

        # Init eventlog file
        f = open(self.filename, 'w', encoding='UTF8')
        f.close()

        while True:
            events = wevt.ReadEventLog(hand, flags, 0)
            if len(events) == 0:
                break
            if events:
                f = open(self.filename, 'a', encoding='UTF8')
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
        self.current_total = wevt.GetNumberOfEventLogRecords(hand)
        self.drain_handler = DrainHandler(self.filename)

    def run(self):
        while True:
            hand = wevt.OpenEventLog(self.server,self.logtype)
            flags = wevt.EVENTLOG_BACKWARDS_READ|wevt.EVENTLOG_SEQUENTIAL_READ
            newtotal = wevt.GetNumberOfEventLogRecords(hand)

            if self.current_total != newtotal:
                today = datetime.datetime.now().date()
                day_ago = today - datetime.timedelta(days=1)

                events = wevt.ReadEventLog(hand, flags, 0, newtotal - self.current_total)
                if events:
                    f = open(self.filename, 'a', encoding='UTF8')
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
                            
                            self.drain_handler.handle(logstring)
                            # if data:
                            #     print('Event Data:')
                            #     for msg in data:
                            #         print(msg)
                            # print('*' * 100)
                        elif str(evt.TimeGenerated)[:10] == str(day_ago):
                            break
                    f.close()

                    self.drain_handler.report()

                    self.current_total += len(events)
    
def windows_event_log_check():
    myWatcher = WindowsEventHandler()
    myWatcher.run()
