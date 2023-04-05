import time
import os
import re
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from modules.drain_handler import DrainHandler

class Handler(FileSystemEventHandler):
    def __init__(self, config):
        monitoring = config['monitoring']       # monitoring 변수 여부는 main에서 check하므로 if 문 생략
        self.monitoring_directory = monitoring['directory'] if 'directory' in monitoring else '.\\'
        self.monitoring_pattern = monitoring['pattern'] if 'pattern' in monitoring else 'none'
        self.monitoring_file = monitoring['file']   # file 변수 여부는 main에서 check하므로 if 문 생략
        self.monitoring_extension = monitoring['extension'] if 'extension' in monitoring else 'log'
        self.monitoring_filename = None

        self.initial_complete_flag = False
        self.name = config['name'] if 'name' in config else ''
        self.tempname = self.name + '.txt'
        self.mode = config['mode'] if 'mode' in config else 'training'
        self.snapshot_file = config['snapshot-file'] if 'snapshot-file' in config else self.monitoring_file
        self.initial_training = config['initial-training'] if 'initial-training' in config else False
        self.file_fullpath = os.path.dirname(os.path.abspath(__file__))
        self.drain_handler = DrainHandler(self.snapshot_file, self.name, self.monitoring_filename, similarity_threshold)

        # self.report = config['report'] if 'report' in config else 'none'
        
        self.last_filename = ''
        self.last_offset = 0
        self.get_lastdata()
        
        self.initialCheck()
        self.initial_complete_flag = True

    def initialCheck(self):
        filelists = os.listdir(self.monitoring_directory)
        filelists.sort()
        old_file = True
        if self.last_filename != '':  
            for i in range(0,len(filelists)):
                if filelists[i] == self.last_filename:
                    old_file = False

                if old_file == False:
                    if self.logFileTypeCheck(filelists[i]):
                        self.monitoring_filename = f"{self.monitoring_directory}\\{filelists[i]}"    

                        if self.initial_training:
                            self.drainTraining()
        else:        
            for file in filelists:
                if self.logFileTypeCheck(file):
                    self.monitoring_filename = f"{self.monitoring_directory}\\{file}"

                    if self.initial_training:
                        self.drainTraining()

        if self.report:
            self.drain_handler.report(self.name)

    def intervalCheck(self):
        if self.monitoring_filename and self.initial_complete_flag:
            if self.mode == 'training':
                self.drainTraining()
            elif self.mode == 'inference':
                self.drainInference()

    def logFileTypeCheck(self, file):
        if self.monitoring_pattern == 'none':
            return True if file == f"{self.monitoring_file}.{self.monitoring_extension}" else False
        elif self.monitoring_pattern == 'day':
            regex = r"{}_(\d{{6}})[0]*[.]{}".format(self.monitoring_file, self.monitoring_extension)
            return True if re.match(regex, file) else False
        elif self.monitoring_pattern == 'hour':
            regex = r"{}_(\d{{8}})[0]*[.]{}".format(self.monitoring_file, self.monitoring_extension)
            return True if re.match(regex, file) else False
        elif self.monitoring_pattern == 'minute':
            regex = r"{}_(\d{{10}})[0]*[.]{}".format(self.monitoring_file, self.monitoring_extension)
            return True if re.match(regex, file) else False

    def get_lastdata(self):
        with open(f'{self.file_fullpath}\\..\\temp\\{self.tempname}', 'r', encoding='UTF8') as f:
            string_val = f.readline()
            if string_val != '':
                val_list = string_val.split('*')
                path_list = val_list[0].split('\\')
                self.last_filename = path_list[len(path_list) - 1]
                self.last_offset = int(val_list[1])
            else:
                self.last_filename = ''
                self.last_offset = 0

    def drainTraining(self):
        self.drain_handler = DrainHandler(self.snapshot_file, self.name, self.monitoring_filename)
        self.drain_handler.set_init_offset(0)
        if self.last_filename == '':
            try:
                with open(self.monitoring_filename, 'rt', encoding='UTF8') as f:
                    for line in f:
                        self.drain_handler.training(line)
            except:
                # ANSI 인코딩으로 인한 에러 발생시
                with open(self.monitoring_filename, 'rt', encoding='ANSI') as f:
                    for line in f:
                        self.drain_handler.training(line)    
        else:
            try:
                path_list = self.monitoring_filename.split('\\')
                self.get_lastdata()
                if path_list[len(path_list) - 1] == self.last_filename:
                    self.drain_handler.set_init_offset(self.last_offset)
                    with open(self.monitoring_filename, 'rt', encoding='UTF8') as f:
                        for line in f.readlines()[self.last_offset:]:
                            self.get_lastdata()
                            self.drain_handler.training(line, self.last_offset)
            except:
                # ANSI 인코딩으로 인한 에러 발생시
                with open(self.monitoring_filename, 'rt', encoding='ANSI') as f:
                    path_list = self.monitoring_filename.split('\\')
                    self.get_lastdata()
                    if path_list[len(path_list) - 1] == self.last_filename:
                        self.drain_handler.set_init_offset(self.last_offset)
                        for line in f.readlines()[self.last_offset:]:
                            self.get_lastdata()
                            self.drain_handler.training(line, self.last_offset)

    def drainInference(self):
        self.drain_handler = DrainHandler(self.snapshot_file, self.name, self.monitoring_filename)

        try:
            with open(self.monitoring_filename, 'rt', encoding='UTF8') as f:
                for line in f:
                    self.drain_handler.inference(line)
        except:
            # ANSI 인코딩으로 인한 에러 발생시
            with open(self.monitoring_filename, 'rt', encoding='ANSI') as f:
                for line in f:
                    self.drain_handler.inference(line)

    def on_created(self, event): # 파일 생성시
        print(f'event type : {event.event_type}')
        if event.is_directory:
            print(f"디렉토리 생성 : {event.src_path}")
        else:
            print(f"파일 생성 : {event.src_path}")
            if self.logFileTypeCheck(os.path.basename(event.src_path)):
                self.last_filename = ''
                self.monitoring_filename = event.src_path
                self.drain_handler.set_init_offset(0)

    def on_modified(self, event):
        print(f'event type : {event.event_type}')
        if event.is_directory:
            print(f"디렉토리 수정 : {event.src_path}")
        else:
            print(f"파일 수정 : {event.src_path}")            

class Watcher:
    # 생성자
    def __init__(self, config):
        self.event_handler = None      # Handler
        self.observer = Observer()     # Observer 객체 생성
        self.interval = config['interval'] if 'interval' in config else 1
        self.event_handler = Handler(config) # 이벤트 핸들러 객체 생성

        monitoring = config['monitoring']       # monitoring 변수 여부는 main에서 check하므로 if 문 생략
        self.monitoring_directory = monitoring['directory'] if 'directory' in monitoring else '.\\'

    # func (2)
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

