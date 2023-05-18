import re
import os
from modules.drain_handler import DrainHandler

class MonitoringHandler():
    def initConfig(self, config):
        monitoring = config['monitoring']       # monitoring 변수 여부는 main에서 check하므로 if 문 생략
        self.monitoring_directory = monitoring['directory'] if 'directory' in monitoring else '.\\'
        self.monitoring_pattern = monitoring['pattern'] if 'pattern' in monitoring else 'none'
        self.monitoring_file = monitoring['file']   # file 변수 여부믐 main에서 check하므로 if 문 생략
        self.monitoring_extension = monitoring['extension'] if 'extension' in monitoring else 'log'
        self.monitoring_filename = None

        self.date_time_format = str(monitoring['date-time-format']).strip() if 'date-time-format' in monitoring else ''
        self.no_datetime_log = config['no-datetime-log'] if 'no-datetime-log' in config else "separate"

        self.initial_complete_flag = False
        self.name = config['name'] if 'name' in config else ''
        self.offsetfile = self.name + '.txt'
        self.mode = config['mode']
        self.initial_check = config['initial-check']
        self.file_fullpath = os.path.dirname(os.path.abspath(__file__))
        self.drain_handler = DrainHandler(config)

        self.report = config['report']
        self.offsetfile = self.name + '.txt'

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

                        if self.initial_check:
                            self.check()
        else:        
            for file in filelists:
                if self.logFileTypeCheck(file):
                    self.monitoring_filename = f"{self.monitoring_directory}\\{file}"

                    if self.initial_check:
                        self.check()

    def intervalCheck(self):
        if self.monitoring_filename and self.initial_complete_flag:
            self.check()
            self.drain_handler.save_state()

    def check(self):
        if os.path.basename(self.monitoring_filename) != self.last_filename:
            self.last_filename = os.path.basename(self.monitoring_filename)
            self.last_offset = 0
        else:
            self.getLastdata()

        if self.mode == 'training':
            self.drainTraining()
        elif self.mode == 'inference':
            self.drainInference()

        try:
            with open(f'{self.file_fullpath}\\..\\output\\offset\\{self.offsetfile}', 'a', buffering=1) as f2:
                f2.seek(0,0)
                f2.truncate(0)
                f2.write(self.monitoring_filename + '*' + str(self.last_offset))
        except:
            pass

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

    def getLastdata(self):
        try:
            with open(f'{self.file_fullpath}\\..\\output\\offset\\{self.offsetfile}', 'r') as f:
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
        date_format_regex = re.sub('[A-Za-z\[\]]', '0', date_format_regex)      # 0000-00-00-00-00-00-000

        line_data_regex = re.sub('[:._\-\sT]','-', line)                    # 2023-03-02-10-34-55.980-abcdefg-blah-blah
        line_data_regex = re.sub('[0-9\[\]]', '0', line_data_regex)             # 0000-00-00-00-00-00-000-abcdefg-blah-blah
        line_data_regex = re.sub('[A-Za-z]', '9', line_data_regex)          # 0000-00-00-00-00-00-000-9999999-999-999

        m = re.match(date_format_regex, line_data_regex)
        if m:
            start = m.start()
            end = m.end()
            return ((line[:start]+line[end:]).strip(), True)                        # abcdefg blah blah
        else:
            return (line, False)

    def drainTraining(self):
        def execute_training(f):
            last_offset = self.last_offset
            if self.no_datetime_log == "separate":
                for line in f.readlines()[last_offset:]:
                    line_data, _ = self.removeTimestamp(line, self.date_time_format)
                    input_line_data = line_data.rstrip()
                    self.last_offset = self.drain_handler.training(input_line_data, self.monitoring_filename, self.last_offset)
            elif self.no_datetime_log == "streaming":
                input_line_data = str()
                for line in f.readlines()[last_offset:]:
                    line_data, datetime_flag = self.removeTimestamp(line, self.date_time_format)

                    if datetime_flag and input_line_data:
                        self.last_offset = self.drain_handler.training(input_line_data, self.monitoring_filename, self.last_offset)
                        input_line_data = str()
                    else:
                        self.last_offset += 1

                    input_line_data = input_line_data + line_data.rstrip()

                if input_line_data:
                    self.last_offset = self.drain_handler.training(input_line_data, self.monitoring_filename, self.last_offset)

        try:
            with open(self.monitoring_filename, 'rt', encoding='UTF8') as f:
                execute_training(f)
        except:
            # ANSI 인코딩으로 인한 에러 발생시
            with open(self.monitoring_filename, 'rt', encoding='ANSI') as f:
                execute_training(f)

    def drainInference(self):
        def execute_inference(f):
            last_offset = self.last_offset
            if self.no_datetime_log == "separate":
                for line in f.readlines()[last_offset:]:
                    line_data, _ = self.removeTimestamp(line, self.date_time_format)
                    input_line_data = line_data.rstrip()
                    input_line = line.rstrip()
                    self.last_offset = self.drain_handler.inference(input_line, line_data, self.last_offset, self.monitoring_filename)
            elif self.no_datetime_log == "streaming":
                input_line_data = str()
                input_line = str()
                for line in f.readlines()[last_offset:]:
                    line_data, datetime_flag = self.removeTimestamp(line, self.date_time_format)

                    if datetime_flag and input_line_data:
                        self.last_offset = self.drain_handler.inference(input_line, input_line_data, self.last_offset, self.monitoring_filename)
                        input_line_data = str()
                        input_line = str()
                    else:
                        self.last_offset += 1

                    input_line_data = input_line_data + line_data.rstrip()
                    input_line = input_line + line.rstrip()

                if input_line_data:
                    self.last_offset = self.drain_handler.inference(input_line, input_line_data, self.last_offset, self.monitoring_filename)

        try:
            with open(self.monitoring_filename, 'rt', encoding='UTF8') as f:
                execute_inference(f)                    
        except:
            # ANSI 인코딩으로 인한 에러 발생시            
            with open(self.monitoring_filename, 'rt', encoding='ANSI') as f:
                execute_inference(f)
