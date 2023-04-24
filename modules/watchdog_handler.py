import time
import os
from modules.monitoring_handler import MonitoringHandler
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class Handler(FileSystemEventHandler, MonitoringHandler):
    def __init__(self, config):
        self.initConfig(config)

        self.getLastdata()
        self.initialCheck()

        if self.report:
            self.drain_handler.report(self.name)

        self.initial_complete_flag = True

    def on_created(self, event): # 파일 생성시
        print(f'event type : {event.event_type}')
        if event.is_directory:
            print(f"디렉토리 생성 : {event.src_path}")
        else:
            print(f"파일 생성 : {event.src_path}")
            if self.logFileTypeCheck(os.path.basename(event.src_path)):
                self.last_filename = ''
                self.last_offset = 0
                self.monitoring_filename = event.src_path
                self.check()

    def on_modified(self, event):
        print(f'event type : {event.event_type}')
        if event.is_directory:
            print(f"디렉토리 수정 : {event.src_path}")
        else:
            print(f"파일 수정 : {event.src_path}")
            self.check()

class Watcher:
    def __init__(self, config):
        self.event_handler = None      # Handler
        self.observer = Observer()     # Observer 객체 생성
        self.interval = config['interval']
        self.event_handler = Handler(config) # 이벤트 핸들러 객체 생성

        monitoring = config['monitoring']       # monitoring 변수 여부는 main에서 check하므로 if 문 생략
        self.monitoring_directory = monitoring['directory'] if 'directory' in monitoring else '.\\'

    def run(self):
        self.observer.schedule(
            self.event_handler,
            self.monitoring_directory,
            recursive=False
        )
        self.observer.start() # 감시 시작
        try:
            while True: # 무한 루프
                self.event_handler.intervalCheck()
                time.sleep(self.interval) # 1초 마다 대상 디렉토리 감시
        except KeyboardInterrupt as e: # 사용자에 의해 "ctrl + z" 발생시
            print ("감시 중지...\n")
            self.observer.stop() # 감시 중단

def logCheck(config):
    myWatcher = Watcher(config)
    myWatcher.run()

