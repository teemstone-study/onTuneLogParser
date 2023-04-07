import time
import re
import json
import os
import yaml
from os.path import dirname
from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig
from drain3.file_persistence import FilePersistence

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

    def __init__(self, drainfilename, name, similarity_threshold=0.4):
        self.config_file_name = dirname(__file__) + "\\..\\drain3.ini"
        self.drain_file_name = drainfilename
        self.name = name
        self.tempname = name + '.txt'
        self.file_fullpath = os.path.dirname(os.path.abspath(__file__))
        persistence = FilePersistence(f"{self.file_fullpath}\\..\\output\\result\\{self.drain_file_name}")

        config = TemplateMinerConfig()
        config.load(self.config_file_name)
        config.drain_sim_th = similarity_threshold  # Override
        config.profiling_enabled = True

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
        #matchCluster = self.template_miner.match(line)
        if True:
            result = self.template_miner.add_log_message(re.sub(u'\u0000', '', line))
            self.line_count += 1

            try:
                with open(f'{self.file_fullpath}\\..\\temp\\{self.tempname}', 'r+', encoding='UTF8') as f:
                    f.seek(0)
                    #f.truncate()                    
                    f.write(self.monitoring_file_name + '*' + str(self.line_count))

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
            except:
                pass
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
