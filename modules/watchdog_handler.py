import time
import os 
import re
import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from modules.drain_handler import DrainHandler

class Handler(FileSystemEventHandler):
    def setInitFileSetting(self, path, prefix):
        self.file_fullpath = os.path.dirname(os.path.abspath(__file__))
        self.file_prefix = prefix
        self.target_directory = path
        self.dir_eventfilename = f"{self.file_fullpath}\\..\\result\\{self.file_prefix}_dir_event.txt"

    def setInitCurrentFiletypes(self):
        self.current_file_types = dict()

        filelists = os.listdir(self.target_directory)
        print(filelists)
        filelists.sort()

        for file in filelists:
            self.setCurrentFiletypes(file)

    def setCurrentFiletypes(self, file):
        Fname, Extension = os.path.splitext(os.path.basename(file))
        if Extension in ('.txt','.log'):
            filekey = self.logFileTypeCheck(Fname, Extension)
            self.current_file_types[filekey] = file if filekey not in self.current_file_types else self.current_file_types[filekey]

    def logFileTypeCheck(self, fname, ext):
        p = re.compile('(\w+)_(\d+)\.(txt|log)')
        m = p.match(f"{fname}{ext}")

        return f"{m.group(1) if m else fname}_{ext[1:]}"

    def getDrainFileNames(self, filekey):
        return f"{self.file_fullpath}\\..\\result\\{self.file_prefix}_{filekey}_drain.txt"
    
    def initGetEvent(self):
        # Init drain file
        for filekey in self.current_file_types:
            drainfilename = self.getDrainFileNames(filekey)                
            f = open(drainfilename, 'w', encoding='UTF8')
            f.close()   

        filelists = os.listdir(self.target_directory)
        filelists.sort()

        self.drain_handler = dict()

        for file in filelists:
            Fname, Extension = os.path.splitext(os.path.basename(file))
            if Extension in ('.txt','.log'):
                filekey = self.logFileTypeCheck(Fname, Extension)
                drainfilename = self.getDrainFileNames(filekey)

                self.drain_handler[filekey] = DrainHandler(drainfilename)
                targetfilename = f"{self.target_directory}\\{file}"

                try:
                    with open(targetfilename, 'rt', encoding='UTF8') as f:
                        for line in f.readlines():
                            self.drain_handler[filekey].handle(line)
                        self.drain_handler[filekey].report()
                except:
                    # ANSI 인코딩으로 인한 에러 발생시
                    with open(targetfilename, 'rt', encoding='ANSI') as f:
                        for line in f.readlines():
                            self.drain_handler[filekey].handle(line)
                        self.drain_handler[filekey].report()


    def on_created(self, event): # 파일 생성시
        with open(self.dir_eventfilename, 'a') as f:
            f.writelines(f'event type : {event.event_type}')
            if event.is_directory:
                f.writelines(f"디렉토리 생성 : {event.src_path}")
            else: 
                f.writelines(f"파일 생성 : {event.src_path}")
                self.setCurrentFiletypes(event.src_path)

    def on_deleted(self, event):
        with open(self.dir_eventfilename, 'a') as f:
            f.writelines(f'event type : {event.event_type}')
            if event.is_directory:
                f.writelines(f"디렉토리 삭제 : {event.src_path}")
            else:
                f.writelines(f"파일 삭제 : {event.src_path}")
                self.setInitCurrentFiletypes()

    def on_moved(self, event): # 파일 이동시
        with open(self.dir_eventfilename, 'a') as f:
            f.writelines(f'event type : {event.event_type}')
            if event.is_directory:
                f.writelines(f"디렉토리 이동 : {event.src_path} -> {event.dest_path}")
            else:
                f.writelines(f"파일 이동 : {event.src_path} -> {event.dest_path}")
                self.setInitCurrentFiletypes()

    def on_modified(self, event):
        with open(self.dir_eventfilename, 'a') as f:
            f.writelines(f'event type : {event.event_type}')
            if event.is_directory:
                f.writelines(f"디렉토리 수정 : {event.src_path}")
            else:
                f.writelines(f"파일 수정 : {event.src_path}")                
                self.setInitCurrentFiletypes()

class Watcher:
    # 생성자
    def __init__(self, path, prefix):
        print ("감시 중 ...\n")
        self.event_handler = None      # Handler
        self.observer = Observer()     # Observer 객체 생성
        self.target_directory = path   # 감시대상 경로
        self.currentDirectorySetting() # instance method 호출 func(1)

        self.event_handler = Handler() # 이벤트 핸들러 객체 생성
        self.event_handler.setInitFileSetting(path, prefix)
        self.event_handler.setInitCurrentFiletypes()
        self.event_handler.initGetEvent()

    # func (1) 현재 작업 디렉토리
    def currentDirectorySetting(self):
        os.chdir(self.target_directory)
        print (f"=== 현재 작업 디렉토리: {os.getcwd()}\n")

    # func (2)
    def run(self):
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
            print ("감시 중지...\n")
            self.observer.stop() # 감시 중단

def logCheck(logPath, prefix):
    myWatcher = Watcher(logPath, prefix)
    myWatcher.run()

