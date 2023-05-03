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

class DrainHandler:
    def __init__(self, config):
        self.name = config['name'] if 'name' in config else ''
        self.minimum_length = config['minimum-length']
        self.drain_file_name = config['snapshot-file'] if 'snapshot-file' in config else self.monitoring_file
        self.words = config['words'] if 'words' in config else []
        self.match_rate = config['match-rate'] if 'match-rate' in config else 0.05
        self.mode = config['mode'] if 'mode' in config else 'training'

        self.config_file_name = dirname(__file__) + "\\..\\drain3.ini"
        self.file_fullpath = os.path.dirname(os.path.abspath(__file__))
        persistence = FilePersistence(f"{self.file_fullpath}\\..\\output\\training\\{self.drain_file_name}")

        parser = configparser.ConfigParser()
        logger = logging.getLogger(__name__)
        section_drain = 'DRAIN'
        section_masking = 'MASKING'

        read_files = parser.read(self.config_file_name, encoding='utf-8')
        if len(read_files) == 0:
            logger.warning(f"config file not found: {self.config_file_name}")
        
        default_sim_th = parser.getfloat(section_drain, 'sim_th')
        self.similarity_threshold = config['similarity-threshold'] if 'similarity-threshold' in config else default_sim_th

        cfg = TemplateMinerConfig()
        cfg.load(self.config_file_name)
        cfg.drain_sim_th = self.similarity_threshold  # Override
        cfg.profiling_enabled = True                  # Override

        # PATH Add
#         self.words.append("<:0PATH0:>")
#         self.words.append(SPECIFIC_WORDS)
#         masking_instructions_str = parser.get(section_masking, 'masking')
#         additional_words_prefix = '{"regex_pattern":"(?i)\\\\b(?:(?!'
#         additional_words_postfix= ')[a-z])+\\\\b", "mask_with": "WORD"}'
#         additional_words = additional_words_prefix + '|'.join(list(i.replace(" ","_") for i in self.words)) + additional_words_postfix
        
#         additional_paths = '{"regex_pattern":"<:0PATH0:>", "mask_with": "PATH"}'
#         masking_instructions_str = f"""[
# {{"regex_pattern":"(?i)((?<=[^A-Za-z0-9])|^)([A-Z]:)?(\\\\\\\\[A-Z0-9_\\\\s\\\\-]+)+(.[A-Z]+)?((?=[^A-Za-z0-9])|$)", "mask_with": "0PATH0"}},
# {{"regex_pattern":"(?i)((?<=[^A-Za-z0-9])|^)([A-Z]:)?(/[A-Z0-9_\\\\s\\\\-]+)+(.[A-Z]+)?((?=[^A-Za-z0-9])|$)", "mask_with": "0PATH0"}},
# {additional_words},{additional_paths},{masking_instructions_str[1:]}"""
#         masking_instructions_str = masking_instructions_str.replace("\n", "")

#         masking_instructions = []
#         masking_list = json.loads(masking_instructions_str)
#         for mi in masking_list:
#             instruction = MaskingInstruction(mi['regex_pattern'], mi['mask_with'])
#             masking_instructions.append(instruction)
#         cfg.masking_instructions = masking_instructions

        self.template_miner = TemplateMiner(persistence, cfg)

        self.start_time = time.time()
        self.batch_start_time = time.time()
        self.batch_size = 10000

        if self.mode == 'inference':
            state = self.template_miner.persistence_handler.load_state()
            if state is None:
                print(f"{self.name} - No state found, skipping inference.")
                self.total_cluster_size = 0
            
            if self.template_miner.config.snapshot_compress_state:
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
                print(f"{self.name}, {self.total_cluster_size}, {self.specific_words_cluster_size}, {self.normal_words_cluster_size}")

    def get_training_data(self, line):
        line = line.rstrip()
        filtered_line = re.sub(u'\u0000', '', line)
        if len(filtered_line) < self.minimum_length:
            return ""
        
        # 특정 단어에 대한 필터링 확률을 높이기 위함
        input_line = filtered_line
        for word in self.words:
            if word.upper() in filtered_line.upper():
                underbar_word = word.replace(" ","_")
                input_line = f"{SPECIFIC_WORDS_PATTERN} {filtered_line.replace(word, underbar_word)}"
                break

        return input_line

    def training(self, line, monitoringfilename="", offset=0):
        self.monitoring_file_name = monitoringfilename
        input_line = self.get_training_data(line)
        if input_line == "":
            return offset
        
        result = self.template_miner.add_log_message(input_line)
        
        if offset % self.batch_size == 0:
            time_took = time.time() - self.batch_start_time
            rate = self.batch_size / time_took
            print(f"{self.name} {self.monitoring_file_name}- Processing line: {offset}, rate {rate:.1f} lines/sec, "
                f"{len(self.template_miner.drain.clusters)} clusters so far.")
            self.batch_start_time = time.time()
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
                with open(f"{self.file_fullpath}\\..\\output\\inference\\{self.name}.txt", 'a', encoding='UTF8') as f:
                    specific_prefix_length = len(SPECIFIC_WORDS_PATTERN)
                    if input_line[:specific_prefix_length] == SPECIFIC_WORDS_PATTERN:
                        f.writelines(f"[#{cluster.cluster_id}][WORD][{monitoringfilename}][{offset}]: {line}")
                    elif normal_cluster_size_rate < self.match_rate * 100:
                        f.writelines(f"[#{cluster.cluster_id}][{normal_cluster_size_rate}%][{monitoringfilename}][{offset}]: {line}")
            except Exception as e:
                print("Exception : " + str(e))                
        else:
            try:
                with open(f"{self.file_fullpath}\\..\\output\\inference\\{self.name}.txt", 'a', encoding='UTF8') as f:
                    f.writelines(f"[None Cluster][{monitoringfilename}][{offset}]: {line}")
            except Exception as e:
                print("Exception : " + str(e))

        return offset+1

    def report(self, name=""):
        self.name = name

        with open(f"{self.file_fullpath}\\..\\output\\report\\{self.name}.log", 'a', encoding='UTF8') as f:
            f.write(f"{self.name} {self.name} --- {len(self.template_miner.drain.clusters)} clusters")

            sorted_clusters = sorted(self.template_miner.drain.clusters, key=lambda it: it.size, reverse=True)
            for cluster in sorted_clusters:
                f.write(str(cluster))

            f.write("\n")
            f.write(f"{self.name} {self.name} --- Prefix Tree:")
            self.template_miner.drain.print_tree(file=f)

            f.write("\n")
            f.write(f"{self.name} {self.name} - --- Profiler Report:\n")
