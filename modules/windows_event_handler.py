import re
import os
import win32evtlog as wevt
import datetime
from modules.monitoring_handler import MonitoringHandler
from modules.drain_handler import DrainHandler

class WindowsEventHandler(MonitoringHandler):
    def __init__(self, config):
        self.initConfig(config)

        self.server = 'localhost'
        self.logtype = 'System'
        self.current_total = 0

        self.getLastdata()
        self.initialCheck()

        if self.initial_check:
            self.initGetEvent()

        if self.report:
            self.drain_handler.report(self.name)

        self.initial_complete_flag = True

    def setMonitoringFilename(self):
        self.file_fullpath = os.path.dirname(os.path.abspath(__file__))
        filename = self.monitoring_file        
        if self.monitoring_pattern == 'day':
            filename = self.monitoring_file + '_' + datetime.datetime.now().strftime('%Y%m%d')
        elif self.monitoring_pattern == 'hour':
            filename = self.monitoring_file + '_' + datetime.datetime.now().strftime('%Y%m%d%H')
        elif self.monitoring_pattern == 'minute':
            filename = self.monitoring_file + '_' + datetime.datetime.now().strftime('%Y%m%d%H%M')

        self.monitoring_filename = f"{self.monitoring_directory}\\{filename}.{self.monitoring_extension}"

    def initGetEvent(self):
        hand = wevt.OpenEventLog(self.server,self.logtype)
        flags = wevt.EVENTLOG_FORWARDS_READ|wevt.EVENTLOG_SEQUENTIAL_READ
        last_offset_date = str()
        lines = list()
        event_time_length_format = "2000-01-01 00:00:00"
        # event_time_format = "%Y-%m-%d %H:%M:%S"        

        try:
            with open(self.monitoring_filename, 'r', encoding='UTF8') as f:
                lines = f.readlines()
                for i in reversed(list(range(len(lines)-1))):
                    if len(lines[i]) > len(event_time_length_format):
                        last_offset_date = lines[i][1:len(event_time_length_format)+1]
                        break
        except:
            pass


        def writeEventLog(evt, f):
            idResult = evt.EventID & 0x0000FFFF
            wevt.EVENTLOG_ERROR_TYPE
            data = evt.StringInserts
            eventdata = ""
            if data != None:
                for msg in data:
                    eventdata += msg
                    
            logstring = f"[{evt.TimeGenerated}] [{evt.EventCategory}][{evt.SourceName}] [{idResult}] [{evt.EventType}]  [{eventdata}]"  
            f.write(logstring + "\n")

        while True:
            events = wevt.ReadEventLog(hand, flags, 0)
            if len(events) == 0:
                break
            if events:
                try:
                    if last_offset_date == "" or str(events[0].TimeGenerated)[:len(event_time_length_format)] >= last_offset_date:
                        self.setMonitoringFilename() 
                        with open(self.monitoring_filename, 'a', encoding='UTF8') as f:
                            for evt in events:
                                writeEventLog(evt, f)

                        self.check()
                except:
                    pass

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
                    self.setMonitoringFilename() 
                    f = open(self.monitoring_filename, 'a', encoding='UTF8')
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
                            
                                
                        elif str(evt.TimeGenerated)[:10] == str(day_ago):
                            break
                    f.close()

                    self.intervalCheck()
                    self.current_total += len(events)
    
def windows_event_log_check(config):
    myWatcher = WindowsEventHandler(config)
    myWatcher.run()
