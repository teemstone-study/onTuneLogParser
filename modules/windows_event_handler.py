import os
import win32evtlog as wevt
import datetime
from modules.drain_handler import DrainHandler

class WindowsEventHandler():
    def __init__(self, config):
        self.server = 'localhost'
        self.logtype = 'System'

        monitoring = config['monitoring']       # monitoring 변수 여부는 main에서 check하므로 if 문 생략
        self.monitoring_directory = monitoring['directory'] if 'directory' in monitoring else '.\\'
        self.monitoring_pattern = monitoring['pattern'] if 'pattern' in monitoring else 'none'
        self.monitoring_file = monitoring['file']   # file 변수 여부믐 main에서 check하므로 if 문 생략
        self.monitoring_extension = monitoring['extension'] if 'extension' in monitoring else 'log'

        self.name = config['name'] if 'name' in config else ''
        self.mode = config['mode'] if 'mode' in config else 'training'
        self.snapshot_file = config['snapshot-file'] if 'snapshot-file' in config else self.monitoring_file
        self.initial_training = config['initial-training'] if 'initial-training' in config else False

        self.drain_handler = DrainHandler(config)
        self.setEventfilename()
        self.initGetEvent()

        #current_locale = os.popen('systeminfo | findstr /B /C:"System Locale"').read()
        #current_locale = locale.getlocale(locale.LC_CTYPE)
        #total = wevt.GetNumberOfEventLogRecords(hand)
        #parent_directory = os.path.dirname(file_fullpath)

    def setEventfilename(self):
        self.file_fullpath = os.path.dirname(os.path.abspath(__file__))
        filename = self.monitoring_file        
        if self.monitoring_pattern == 'day':
            filename = self.monitoring_file + '_' + datetime.datetime.now().strftime('%Y%m%d')
        elif self.monitoring_pattern == 'hour':
            filename = self.monitoring_file + '_' + datetime.datetime.now().strftime('%Y%m%d%H')
        elif self.monitoring_pattern == 'minute':
            filename = self.monitoring_file + '_' + datetime.datetime.now().strftime('%Y%m%d%H%M')

        self.eventfilename = f"{self.file_fullpath}\\..\\output\\{self.monitoring_directory}\\{filename}.{self.monitoring_extension}"

    def initGetEvent(self):
        today = datetime.datetime.now().date()
        day_ago = today - datetime.timedelta(days=1)
        hand = wevt.OpenEventLog(self.server,self.logtype)
        flags = wevt.EVENTLOG_FORWARDS_READ|wevt.EVENTLOG_SEQUENTIAL_READ

        while True:
            events = wevt.ReadEventLog(hand, flags, 0)
            if len(events) == 0:
                break
            if events:
                f = open(self.eventfilename, 'a', encoding='UTF8')
                for evt in events:
                    if str(evt.TimeGenerated)[:10] == str(today):
                        idResult = evt.EventID & 0x0000FFFF
                        wevt.EVENTLOG_ERROR_TYPE
                        data = evt.StringInserts
                        eventdata = ""
                        if data != None:
                            for msg in data:
                                eventdata += msg
                                
                        logstring = f"[{evt.TimeGenerated}] [{evt.EventCategory}][{evt.SourceName}] [{idResult}] [{evt.EventType}]  [{eventdata}]"  
                        f.write(logstring + "\n")

                        if self.initial_training:
                            self.drain_handler.training(logstring)

                    elif str(evt.TimeGenerated)[:10] == str(day_ago):
                        break
                f.close()

        flags = wevt.EVENTLOG_BACKWARDS_READ|wevt.EVENTLOG_SEQUENTIAL_READ
        self.current_total = wevt.GetNumberOfEventLogRecords(hand)

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
                            idResult = evt.EventID & 0x0000FFFF
                            wevt.EVENTLOG_ERROR_TYPE
                            data = evt.StringInserts
                            eventdata = ""
                            for msg in data:
                                    eventdata += msg
                                
                            logstring = f"[{evt.TimeGenerated}] [{evt.EventCategory}][{evt.SourceName}] [{idResult}] [{evt.EventType}]  [{eventdata}]"  
                                
                            f.write(logstring + "\n")
                            
                            if self.mode == 'training':
                                self.drain_handler.training(logstring)
                            elif self.mode == 'inference':
                                self.drain_handler.inference(logstring)
                                
                        elif str(evt.TimeGenerated)[:10] == str(day_ago):
                            break
                    f.close()

                    self.current_total += len(events)
    
def windows_event_log_check(config):
    myWatcher = WindowsEventHandler(config)
    myWatcher.run()
