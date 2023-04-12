import time
import re
import json
import os
import yaml
import configparser
import logging
from os.path import dirname
from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig
from drain3.file_persistence import FilePersistence
from drain3.masking import MaskingInstruction

persistence_type = "FILE"

class DrainHandler:
    def load_Yaml(self):
        with open('{self.file_fullpath}\..\config\Setting.yaml', 'rw', encoding='UTF-8') as f:
            _config = yaml.load(f, Loader=yaml.FullLoader)

        return _config

    def save_Yaml(self, config):
        with open('{self.file_fullpath}\..\config\Setting.yaml', 'w', encoding='UTF-8') as f:
            yaml.dump(config, f)

    def set_lastdata(self):
        #config = self.load_Yaml()
       
        with open('{self.file_fullpath}\..\config\Setting.yaml', 'r', encoding='UTF-8') as f:
            config = yaml.load(f, Loader=yaml.FullLoader)

        for item in config['data']:
            if "monitoring" in item and "file" in item["monitoring"]:
                if "type" not in item or item["type"] == "normal":
                    if item["name"] == self.name:
                        item["lastfile"] = self.monitoring_file_name
                        item["offset"] = self.line_count
                        with open('{self.file_fullpath}\..\config\Setting.yaml', 'w', encoding='UTF-8') as fs:
                            yaml.dump(item, fs)
                        break
        
        #with open('{self.file_fullpath}\..\config\Setting.yaml', 'rU', encoding='UTF-8') as f:
        #   yaml.dump(config, f)
        #self.save_Yaml(config)

    def __init__(self, config):
        self.name = config['name'] if 'name' in config else ''
        self.drain_file_name = config['snapshot-file'] if 'snapshot-file' in config else self.monitoring_file
        self.duplicate_allow_count = config['duplicate-allow-count'] if 'duplicate-allow-count' in config else 1000
        self.words = config['words'] if 'words' in config else []

        self.config_file_name = dirname(__file__) + "\\..\\drain3.ini"
        self.tempname = self.name + '.txt'
        self.file_fullpath = os.path.dirname(os.path.abspath(__file__))
        persistence = FilePersistence(f"{self.file_fullpath}\\..\\output\\result\\{self.drain_file_name}")

        parser = configparser.ConfigParser()
        logger = logging.getLogger(__name__)
        section_drain = 'DRAIN'
        section_masking = 'MASKING'

        read_files = parser.read(self.config_file_name, encoding='utf-8')
        if len(read_files) == 0:
            logger.warning(f"config file not found: {self.config_file_name}")
        
        default_sim_th = parser.getfloat(section_drain, 'sim_th')
        self.similarity_threshold = config['similarity-threshold'] if 'similarity-threshold' in config else default_sim_th

        config = TemplateMinerConfig()
        config.load(self.config_file_name)
        config.drain_sim_th = self.similarity_threshold  # Override
        config.profiling_enabled = True                  # Override

        masking_instructions_str = parser.get(section_masking, 'masking').replace("\n", "")
        additional_words_prefix = '{"regex_pattern":"(?i)((?<=[^A-Z0-9가-힣])|^)(?!'
        additional_words_postfix= ').*((?=.*[^A-Z0-9가-힣])|$)", "mask_with": "WORD"}'
        additional_words = additional_words_prefix + '|'.join([f".*{i}" for i in self.words]) + additional_words_postfix
        
        masking_instructions_str = f"{masking_instructions_str[:-1]},{additional_words}]"

        masking_instructions = []
        masking_list = json.loads(masking_instructions_str)
        for mi in masking_list:
            instruction = MaskingInstruction(mi['regex_pattern'], mi['mask_with'])
            masking_instructions.append(instruction)
        config.masking_instructions = masking_instructions

        self.template_miner = TemplateMiner(persistence, config)
        self.line_count = 0

        self.start_time = time.time()
        self.batch_start_time = time.time()
        self.batch_size = 10000

    def set_init_offset(self, offset):
        self.line_count = offset

    def training(self, line, monitoringfilename="", offset=0):
        self.monitoring_file_name = monitoringfilename
        line = line.rstrip()
        self.line_count = offset
        filtered_line = re.sub(u'\u0000', '', line)
        if filtered_line == "":
            return self.line_count
        
        #matchCluster = self.template_miner.match(line)
        if True:
            result = self.template_miner.add_log_message(filtered_line)

            if self.line_count % self.duplicate_allow_count == 0:
                try:
                    with open(f'{self.file_fullpath}\\..\\temp\\{self.tempname}', 'w') as f:
                        f.write(self.monitoring_file_name + '*' + str(self.line_count))
                except:
                    pass

            self.line_count += 1
            
            if self.line_count % self.batch_size == 0:
                time_took = time.time() - self.batch_start_time
                rate = self.batch_size / time_took
                print(f"{self.name} {self.monitoring_file_name}- Processing line: {self.line_count}, rate {rate:.1f} lines/sec, "
                    f"{len(self.template_miner.drain.clusters)} clusters so far.")
                self.batch_start_time = time.time()
            if result["change_type"] != "none":
                result_json = json.dumps(result)
                print(f"{self.name} {self.monitoring_file_name}- Input ({self.line_count}): {line}")
                print(f"{self.name} {self.monitoring_file_name}- Result: {result_json}")

        else:
            #match의 결과가 있을 경우 parameter를 체크해보자.
            param_list = self.template_miner.get_log_reg_parameter(line)
            param_list = param_list.sort()

            template = matchCluster.get_template()
            #matchCluster.get_template().
            paramList = self.template_miner.get_parameter_list(template, line)
            paramList = paramList.sort()
            print(param_list)
            print(paramList)

        return self.line_count

    def inference(self, line, monitoringfilename=""):
        self.monitoring_file_name = monitoringfilename
        print(line)
        line = line.rstrip()
        cluster = self.template_miner.match(line)
        if cluster != None:
            template = cluster.get_template()
            print(f"Matched template #{cluster.cluster_id}: {template}")
            print("Cluster Size : " + str(cluster.size))
            paramList = self.template_miner.get_parameter_list(template, line)
            for param in paramList:
                print("Param Data : " + param)
        else:
            print("Cluster is None  Log : " + line)

    def report(self, name=""):
        self.name = name

        with open(f"{self.name}.log", 'a', encoding='UTF8') as f:
            f.write(f"{self.name} {self.name} --- {len(self.template_miner.drain.clusters)} clusters")

            sorted_clusters = sorted(self.template_miner.drain.clusters, key=lambda it: it.size, reverse=True)
            for cluster in sorted_clusters:
                f.write(str(cluster))

            f.write("\n")
            f.write(f"{self.name} {self.name} --- Prefix Tree:")
            self.template_miner.drain.print_tree(file=f)

            f.write("\n")
            f.write(f"{self.name} {self.name} - --- Profiler Report:\n")
