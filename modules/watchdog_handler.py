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

        self.date_time_format = str(monitoring['date-time-format']).strip() if 'date-time-format' in monitoring else ''

        self.initial_complete_flag = False
        self.name = config['name'] if 'name' in config else ''
        self.tempname = self.name + '.txt'
        self.mode = config['mode'] if 'mode' in config else 'training'
        self.initial_training = config['initial-training'] if 'initial-training' in config else False
        self.file_fullpath = os.path.dirname(os.path.abspath(__file__))
        self.drain_handler = DrainHandler(config)

        self.report = config['report'] if 'report' in config else False
        self.duplicate_allow_count = config['duplicate-allow-count'] if 'duplicate-allow-count' in config else 500
        self.tempname = self.name + '.txt'
        
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

                if not old_file:
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
        else:
            pattern_sub_regex = re.sub('[:._\-\sT]','-', self.monitoring_pattern)                                       # yyyy-mm-dd-HHMMSS
            pattern_sub_regex = re.sub('[A-Za-z]', '0', pattern_sub_regex)                                              # 0000-00-00-000000            
            sub_regex_arr = pattern_sub_regex.split('-')
            sub_regex_str = str()
            for sub_regex in sub_regex_arr:
                sub_regex_str += '(\d{' + str(len(sub_regex)) + '})' + '-' if sub_regex != '' else ''                   # (\d{4})-(\d{2})-(\d{2})-(\d{6})

            prefix_sub_regex = re.sub('[:._\-\s]','-', self.monitoring_file)                                            # postgresql-
            regex_str = r"{}{}{}".format(prefix_sub_regex, sub_regex_str, self.monitoring_extension)                    # postgresql-(\d{4})-(\d{2})-(\d{2})-(\d{6})-log

            regex_file = re.sub('[:._\-\sT]','-', file)                                                                 # postgresql-2023-03-01-123123-log
            return True if re.match(regex_str, regex_file) else False

    def get_lastdata(self):
        try:
            with open(f'{self.file_fullpath}\\..\\temp\\{self.tempname}', 'r') as f:
                string_val = f.readline()
                if string_val != '':
                    val_list = string_val.split('*')
                    self.last_filename = os.path.basename(val_list[0])
                    self.last_offset = int(val_list[1])
                else:
                    self.last_filename = ''
                    self.last_offset = 0
        except:
            self.last_filename = ''
            self.last_offset = 0

    def removeTimestamp(self, line, date_time_format):
        date_format_regex = re.sub('[:._\-\sT]','-', date_time_format)      # yyyy-MM-dd-HH-mm-ss-fff
        date_format_regex = re.sub('[A-Za-z]', '0', date_format_regex)      # 0000-00-00-00-00-00-000

        line_data_regex = re.sub('[:._\-\sT]','-', line)                    # 2023-03-02-10-34-55.980-abcdefg-blah-blah
        line_data_regex = re.sub('[0-9]', '0', line_data_regex)             # 0000-00-00-00-00-00-000-abcdefg-blah-blah
        line_data_regex = re.sub('[A-Za-z]', '9', line_data_regex)          # 0000-00-00-00-00-00-000-9999999-999-999

        m = re.match(date_format_regex, line_data_regex)
        if m:
            start = m.start()
            end = m.end()
            return (line[:start]+line[end:]).strip()                        # abcdefg blah blah
        else:
            return line

    def drainTraining(self):
        self.drain_handler.set_init_offset(0)
        if os.path.basename(self.monitoring_filename) != self.last_filename:
            self.last_filename = os.path.basename(self.monitoring_filename)
            self.last_offset = 0
        else:
            self.get_lastdata()

        self.drain_handler.set_init_offset(self.last_offset)
        try:
            with open(self.monitoring_filename, 'rt', encoding='UTF8') as f:
                for line in f.readlines()[self.last_offset:]:
                    if self.last_offset % self.duplicate_allow_count == 0:
                        try:
                            with open(f'{self.file_fullpath}\\..\\temp\\{self.tempname}', 'a') as f2:
                                f2.seek(0,0)
                                f2.truncate(0)
                                f2.write(self.monitoring_filename + '*' + str(self.last_offset))
                        except:
                            pass
                                            
                    line_data = self.removeTimestamp(line, self.date_time_format)
                    self.last_offset = self.drain_handler.training(line_data, self.monitoring_filename, self.last_offset)                    
        except:
            # ANSI 인코딩으로 인한 에러 발생시
            with open(self.monitoring_filename, 'rt', encoding='ANSI') as f:
                for line in f.readlines()[self.last_offset:]:
                    if self.last_offset % self.duplicate_allow_count == 0:
                        try:
                            with open(f'{self.file_fullpath}\\..\\temp\\{self.tempname}', 'a') as f2:
                                f2.seek(0,0)
                                f2.truncate(0)
                                f2.write(self.monitoring_filename + '*' + str(self.last_offset))
                        except:
                            pass

                    line_data = self.removeTimestamp(line, self.date_time_format)
                    self.last_offset = self.drain_handler.training(line_data, self.monitoring_filename, self.last_offset)

    def drainInference(self):
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
                self.last_offset = 0
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

