import time
import re
import json
import os
import zlib
import base64
import configparser
import logging
import jsonpickle
from drain3.drain import Drain
from os.path import dirname
from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig
from drain3.file_persistence import FilePersistence
from drain3.masking import MaskingInstruction

PERSISTENCE_TYPE = "FILE"
NORMAL_WORDS = "<:WORD:>"
SPECIFIC_WORDS = "Specific_Words"
SPECIFIC_WORDS_PATTERN = f"---{SPECIFIC_WORDS}---"
MAX_CLUSTER_SIZE = 1000000
MAX_CHILDREN = 1000000

class DrainHandler:
    def __init__(self, config):
        self.name = config['name'] if 'name' in config else ''
        self.minimum_length = config['minimum-length']
        self.drain_file_name = config['snapshot-file'] if 'snapshot-file' in config else self.monitoring_file
        self.words = config['words'] if 'words' in config else []
        self.ignore_words = config['ignore-words'] if 'ignore-words' in config else []
        self.custom_masking_words = config['custom-masking-words'] if 'custom-masking-words' in config else []
        self.match_rate = config['match-rate'] if 'match-rate' in config else 0
        self.match_max_count = config['match-max-count'] if 'match-max-count' in config else 0
        self.mode = config['mode'] if 'mode' in config else 'training'

        self.config_file_name = dirname(__file__) + "\\..\\drain3.ini"
        self.file_fullpath = os.path.dirname(os.path.abspath(__file__))
        persistence = FilePersistence(f"{self.file_fullpath}\\..\\output\\training\\{self.drain_file_name}")

        parser = configparser.ConfigParser()
        logger = logging.getLogger(__name__)
        section_drain = 'DRAIN'
        section_snapshot = 'SNAPSHOT'

        read_files = parser.read(self.config_file_name, encoding='utf-8')
        if len(read_files) == 0:
            logger.warning(f"config file not found: {self.config_file_name}")
        
        default_sim_th = parser.getfloat(section_drain, 'sim_th')
        default_depth = parser.getint(section_drain, 'depth')
        default_compress_state = parser.getboolean(section_snapshot, 'compress_state')
        default_parametrize_numeric_tokens = parser.getboolean(section_drain, 'parametrize_numeric_tokens')

        self.similarity_threshold = config['similarity-threshold'] if 'similarity-threshold' in config else default_sim_th
        self.depth = config['depth'] if 'depth' in config else default_depth
        self.compress_state = config['compress-state'] if 'compress-state' in config else default_compress_state
        self.parametrize_numeric_tokens = config['parametrize-numeric-tokens'] if 'parametrize-numeric-tokens' in config else default_parametrize_numeric_tokens

        cfg = TemplateMinerConfig()
        cfg.load(self.config_file_name)
        cfg.drain_sim_th = self.similarity_threshold        # Override
        cfg.drain_depth = self.depth                        # Override
        cfg.snapshot_compress_state = self.compress_state   # Override
        cfg.parametrize_numeric_tokens = self.parametrize_numeric_tokens    # Override
        cfg.profiling_enabled = True                        # Override
        cfg.drain_max_children = MAX_CHILDREN               # Override
        cfg.drain_max_clusters = MAX_CLUSTER_SIZE           # Override

        self.template_miner = TemplateMiner(persistence, cfg)

        self.start_time = time.time()
        self.batch_start_time = time.time()
        self.batch_size = 10000

        state = self.template_miner.persistence_handler.load_state()
       
        if state and self.template_miner.config.snapshot_compress_state:
            state = zlib.decompress(base64.b64decode(state))

        if state is None:
            self.total_cluster_size = 0
            self.specific_words_cluster_size = 0
            self.normal_words_cluster_size = 0
        else:
            def get_specific_words_cluster_size(loaded_drain):
                size = 0
                for c in loaded_drain.id_to_cluster.values():
                    applied_delimiter_swp = SPECIFIC_WORDS_PATTERN.replace("_", " ")
                    applied_delimiter_swp_size = len(applied_delimiter_swp.split())
                    cluster_token_prefix = ' '.join(c.log_template_tokens[:applied_delimiter_swp_size])
                    if cluster_token_prefix == applied_delimiter_swp:
                        size += c.size
                return size
            
            loaded_drain: Drain = jsonpickle.loads(state, keys=True)
            self.total_cluster_size = loaded_drain.get_total_cluster_size()
            self.specific_words_cluster_size = get_specific_words_cluster_size(loaded_drain)
            self.normal_words_cluster_size = self.total_cluster_size - self.specific_words_cluster_size

    def remove_unused_data(self, line):
        return re.sub(u'\u0000', '', line)

    def get_training_data(self, line):
        line = line.rstrip()
        filtered_line = self.remove_unused_data(line)

        if len(filtered_line) < self.minimum_length:
            return ""
        
        def insert_space(match_obj):
            if match_obj.group(1) is not None and match_obj.group(2) is not None:
                return f"{match_obj.group(1)} {match_obj.group(2)}"
            
        filtered_line = re.sub("([\]|\}|\)])([\[|\{|\(])",insert_space, filtered_line)

        # 검출 대상 단어는 Specific words pattern 적용 후 종료
        input_line = filtered_line
        for word in self.words:
            if word.upper() in filtered_line.upper():
                underbar_word = word.replace(" ","_")
                input_line = f"{SPECIFIC_WORDS_PATTERN} {filtered_line.replace(word, underbar_word)}"
                break

        # 무시 대상 단어는 제거 적용 후 반복
        for iword in self.ignore_words:
            input_line = re.sub(iword, "", input_line, flags=re.IGNORECASE)

        # Custom Masking Words 단어는 마스킹 적용 후 반복
        for cword in self.custom_masking_words:
            input_line = re.sub(cword['source'], cword['target'], input_line, flags=re.IGNORECASE)

        return input_line

    def showProcessingLine(self, offset):
        if offset % self.batch_size == 0:
            time_took = time.time() - self.batch_start_time
            rate = self.batch_size / time_took
            print(f"{self.name} - Processing line: {offset}, rate {rate:.1f} lines/sec, "
                f"{len(self.template_miner.drain.clusters)} clusters so far.")
            self.batch_start_time = time.time()

    def training(self, line, monitoringfilename="", offset=0):
        self.monitoring_file_name = monitoringfilename
        input_line = self.get_training_data(line)
        if input_line == "":
            return offset
        
        result = self.template_miner.add_log_message(input_line)

        self.showProcessingLine(offset)
        
        if result["change_type"] != "none":
            result_json = json.dumps(result)
            print(f"{self.name} {self.monitoring_file_name}- Input ({offset}): {line}")
            print(f"{self.name} {self.monitoring_file_name}- Result: {result_json}")

        return offset+1

    def inference(self, line, match_line, offset=0, monitoringfilename=""):
        input_line = self.get_training_data(match_line)
        if input_line == "":
            return offset
        
        cluster = self.template_miner.match(input_line)
        if cluster != None:
            normal_cluster_size_rate = round(cluster.size / self.normal_words_cluster_size * 100, 1) if self.normal_words_cluster_size > 0 else 0
            try:
                # 원문이 입력되더라도 아래와 같이 우측 공백 및 \u0000 제거는 필요
                line = self.remove_unused_data(line)

                with open(f"{self.file_fullpath}\\..\\output\\inference\\{self.name}.txt", 'a', encoding='UTF8') as f:
                    specific_prefix_length = len(SPECIFIC_WORDS_PATTERN)
                    if input_line[:specific_prefix_length] == SPECIFIC_WORDS_PATTERN:
                        f.writelines(f"[#{cluster.cluster_id}][WORD][{monitoringfilename}][{offset}]: {line}\n")
                    elif self.match_rate > 0 and normal_cluster_size_rate < self.match_rate * 100:
                        f.writelines(f"[#{cluster.cluster_id}][{normal_cluster_size_rate}%][{monitoringfilename}][{offset}]: {line}\n")
                    elif self.match_max_count > 0 and cluster.size < self.match_max_count:
                        f.writelines(f"[#{cluster.cluster_id}][{cluster.size}][{monitoringfilename}][{offset}]: {line}\n")

                self.showProcessingLine(offset)

            except Exception as e:
                print("Exception : " + str(e))                
        else:
            try:
                with open(f"{self.file_fullpath}\\..\\output\\inference\\{self.name}.txt", 'a', encoding='UTF8') as f:
                    f.writelines(f"[None Cluster][{monitoringfilename}][{offset}]: {line}\n")
            except Exception as e:
                print("Exception : " + str(e))

        return offset+1

    def report(self, name=""):
        self.name = name

        with open(f"{self.file_fullpath}\\..\\output\\report\\{self.name}.log", 'a', encoding='UTF8') as f:
            f.write(f"{self.name} {self.name} --- {len(self.template_miner.drain.clusters)} clusters")

            f.write("\n")
            f.write(f"{self.name} {self.name} --- Prefix Tree:")
            self.template_miner.drain.print_tree(file=f)

            f.write("\n")
            f.write(f"{self.name} {self.name} - Total: {self.total_cluster_size}, Normal: {self.normal_words_cluster_size}, Specific: {self.specific_words_cluster_size}\n")

    def save_state(self):
        # Periodic snapshot
        if self.template_miner.persistence_handler is not None:
            self.template_miner.profiler.start_section("save_state")
            snapshot_reason = self.template_miner.get_snapshot_reason("none", 0)
            if snapshot_reason:
                self.template_miner.save_state(snapshot_reason)
                self.template_miner.last_save_time = time.time()
            self.template_miner.profiler.end_section()
