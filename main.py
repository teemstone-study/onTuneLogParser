import win32evtlog as wevt
import win32event
import time
import datetime
import locale
import threading
import logging
import os 
import sys
import json
from os.path import dirname
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dotenv import load_dotenv
from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig

word = "한글"
if word.encode().isalpha():
    print("It is an alphabet")
else:
    print("It is not an alphabet")

word = "test"
if word.encode().isalpha():
    print("It is an alphabet")
else:
    print("It is not an alphabet")

word = "tet한글도"
if word.encode().isalpha():
    print("It is an alphabet")
else:
    print("It is not an alphabet")

load_dotenv()
logPath = os.environ.get('CheckPath')

class Handler(FileSystemEventHandler):
    def on_created(self, event): # 파일 생성시
        print (f'event type : {event.event_type}\n'
               f'event src_path : {event.src_path}')
        if event.is_directory:
            print ("디렉토리 생성")
        else: # not event.is_directory
            """
            Fname : 파일 이름
            Extension : 파일 확장자 
            """
            Fname, Extension = os.path.splitext(os.path.basename(event.src_path))

            if Extension == '.txt':
                print (".txt 파일 입니다.")
            elif Extension == '.log':
                print (".log 파일 입니다.")
    def on_deleted(self, event):
        print ("삭제 이벤트 발생")

    def on_moved(self, event): # 파일 이동시
        print (f'event type : {event.event_type}\n')

    def on_modified(self, event):
        print (f'event type : {event.event_type}\n')
        print (f'event scr path : {event.src_path}\n')
        print (f'event  : {event}\n')
        

class Watcher:
    # 생성자
    def __init__(self, path):
        print ("감시 중 ...")
        self.event_handler = None      # Handler
        self.observer = Observer()     # Observer 객체 생성
        self.target_directory = path   # 감시대상 경로
        self.currentDirectorySetting() # instance method 호출 func(1)

    # func (1) 현재 작업 디렉토리
    def currentDirectorySetting(self):
        print ("====================================")
        print ("현재 작업 디렉토리:  ", end=" ")
        os.chdir(self.target_directory)
        print ("{cwd}".format(cwd = os.getcwd()))
        print ("====================================")

    # func (2)
    def run(self):
        self.event_handler = Handler() # 이벤트 핸들러 객체 생성
        self.observer.schedule(
            self.event_handler,
            self.target_directory,
            recursive=False
        )
        self.observer.start() # 감시 시작
        try:
            while True: # 무한 루프
                time.sleep(1) # 1초 마다 대상 디렉토리 감시
        except KeyboardInterrupt as e: # 사용자에 의해 "ctrl + z" 발생시
            print ("감시 중지...")
            self.observer.stop() # 감시 중단

def logCheck():
    myWatcher = Watcher(logPath)
    myWatcher.run()

def makeDrain3(filename):
    config = TemplateMinerConfig()
    config.load(dirname(__file__) + "/drain3.ini")
    config.profiling_enabled = True
    template_miner = TemplateMiner(config=config)

    line_count = 0

    with open(filename, 'rt', encoding='UTF8') as f:
        lines = f.readlines()

    start_time = time.time()
    batch_start_time = start_time
    batch_size = 10000
    logger = logging.getLogger(__name__)
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(message)s')

    for line in lines:
        line = line.rstrip()
        #line = line[17:]
        result = template_miner.add_log_message(line)
        line_count += 1
        if line_count % batch_size == 0:
            time_took = time.time() - batch_start_time
            rate = batch_size / time_took
            logger.info(f"Processing line: {line_count}, rate {rate:.1f} lines/sec, "
                        f"{len(template_miner.drain.clusters)} clusters so far.")
            batch_start_time = time.time()
        if result["change_type"] != "none":
            result_json = json.dumps(result)
            logger.info(f"Input ({line_count}): " + line)
            logger.info("Result: " + result_json)

    time_took = time.time() - start_time
    rate = line_count / time_took
    logger.info(f"--- Done processing file in {time_took:.2f} sec. Total of {line_count} lines, rate {rate:.1f} lines/sec, "
                f"{len(template_miner.drain.clusters)} clusters")

    sorted_clusters = sorted(template_miner.drain.clusters, key=lambda it: it.size, reverse=True)
    for cluster in sorted_clusters:
        logger.info(cluster)

    print("Prefix Tree:")
    template_miner.drain.print_tree()
    template_miner.profiler.report(0)        


filecheckThread = threading.Thread(target=logCheck)
filecheckThread.start()

#current_locale = os.popen('systeminfo | findstr /B /C:"System Locale"').read()
current_locale = locale.getlocale(locale.LC_CTYPE)

today = datetime.datetime.now().date()
day_ago = today - datetime.timedelta(days=1)

server = 'localhost'
logtype = 'System'
hand = wevt.OpenEventLog(server,logtype)
flags = wevt.EVENTLOG_FORWARDS_READ|wevt.EVENTLOG_SEQUENTIAL_READ
total = wevt.GetNumberOfEventLogRecords(hand)
file_fullpath = os.path.dirname(os.path.abspath(__file__))
#parent_directory = os.path.dirname(file_fullpath)

while True:
    events = wevt.ReadEventLog(hand, flags, 0)
    if len(events) == 0:
        break
    if events:
        filename = file_fullpath + "\\eventlog.txt"
        f = open(filename, 'a', encoding='UTF8')
        for evt in events:
            if str(evt.TimeGenerated)[:10] == str(today):
                print('Event Category:', evt.EventCategory)
                print('Time Generated:', evt.TimeGenerated)
                print('Source Name:', evt.SourceName)
                idResult = evt.EventID & 0x0000FFFF
                print('Event ID:', idResult)
                # 1 : 오류 2: 경고 4 : 정보
                wevt.EVENTLOG_ERROR_TYPE
                print('Event Type:', evt.EventType) 
                data = evt.StringInserts
                eventdata = ""
                if data != None:
                    for msg in data:
                            eventdata += msg
                        
                logstring = f"[{evt.EventCategory}][{evt.TimeGenerated}] [{evt.SourceName}] [{idResult}] [{evt.EventType}]  [{eventdata}]"  
                f.write(logstring + "\n")
                    
                if data:
                    print('Event Data:')

                    for msg in data:
                        print(msg)

                print('*' * 100)
            elif str(evt.TimeGenerated)[:10] == str(day_ago):
                break
        f.close()


flags = wevt.EVENTLOG_BACKWARDS_READ|wevt.EVENTLOG_SEQUENTIAL_READ
Oldtotal = wevt.GetNumberOfEventLogRecords(hand)

#Apply Drain3 Algorithm?
makeDrain3(filename)

while True:
     hand = wevt.OpenEventLog(server,logtype)
     flags = wevt.EVENTLOG_BACKWARDS_READ|wevt.EVENTLOG_SEQUENTIAL_READ
     NewTotal = wevt.GetNumberOfEventLogRecords(hand)

     if Oldtotal != NewTotal:
        events = wevt.ReadEventLog(hand, flags, 0, NewTotal - Oldtotal)
        if events:
            filename = file_fullpath + "\\eventlog.txt"
            f = open(filename, 'a', encoding='UTF8')
            for evt in events:
                if str(evt.TimeGenerated)[:10] == str(today):
                    print('Event Category:', evt.EventCategory)
                    print('Time Generated:', evt.TimeGenerated)
                    print('Source Name:', evt.SourceName)
                    idResult = evt.EventID & 0x0000FFFF
                    print('Event ID:', idResult)
                    # 1 : 오류 2: 경고 4 : 정보
                    wevt.EVENTLOG_ERROR_TYPE
                    print('Event Type:', evt.EventType) 
                    data = evt.StringInserts
                    eventdata = ""
                    for msg in data:
                            eventdata += msg
                        
                    logstring = f"[{evt.EventCategory}][{evt.TimeGenerated}] [{evt.SourceName}] [{idResult}] [{evt.EventType}]  [{eventdata}]"  
                        
                    f.write(logstring + "\n")
                        
                    if data:
                        print('Event Data:')

                        for msg in data:
                            print(msg)

                    print('*' * 100)
                elif str(evt.TimeGenerated)[:10] == str(day_ago):
                    break
            f.close()

            Oldtotal += len(events)

