import os
import win32evtlog as wevt
import datetime
from modules.drain_handler import DrainHandler

class WindowsEventHandler():
    def __init__(self):
        self.server = 'localhost'
        self.logtype = 'System'

        file_fullpath = os.path.dirname(os.path.abspath(__file__))
        self.eventfilename = file_fullpath + "\\..\\output\\windows_event_log\\eventlog.txt"
        self.drainfilename = file_fullpath + "\\..\\output\\result\\eventlog_drain.txt"
        
        #current_locale = os.popen('systeminfo | findstr /B /C:"System Locale"').read()
        #current_locale = locale.getlocale(locale.LC_CTYPE)
        #total = wevt.GetNumberOfEventLogRecords(hand)
        #parent_directory = os.path.dirname(file_fullpath)

        self.initGetEvent()

    def initGetEvent(self):
        today = datetime.datetime.now().date()
        day_ago = today - datetime.timedelta(days=1)
        hand = wevt.OpenEventLog(self.server,self.logtype)
        flags = wevt.EVENTLOG_FORWARDS_READ|wevt.EVENTLOG_SEQUENTIAL_READ

        # Init eventlog file
        f = open(self.eventfilename, 'w', encoding='UTF8')
        f.close()

        # Init drain file
        with open(self.drainfilename, 'w', encoding='UTF8') as f:
            f.close()

        self.drain_handler = DrainHandler(self.drainfilename)
        while True:
            events = wevt.ReadEventLog(hand, flags, 0)
            if len(events) == 0:
                break
            if events:
                f = open(self.eventfilename, 'a', encoding='UTF8')
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
                        self.drain_handler.handle(logstring)    
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
        self.drain_handler.report()
        
       # with open(self.eventfilename, 'rt', encoding='UTF8') as f:
       #     for line in f.readlines():
       #         self.drain_handler.handle(line)
       #     self.drain_handler.report()


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
                    f = open(self.eventfilename, 'a', encoding='UTF8')
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
