import time
import logging
import sys
import json
from os.path import dirname
from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig

class DrainHandler:
    def __init__(self, filename):
        self.config_file_name = dirname(__file__) + "/drain3.ini"
        self.log_file_name = filename

        config = TemplateMinerConfig()
        config.load(self.config_file_name)
        config.profiling_enabled = True
        self.template_miner = TemplateMiner(config=config)

        line_count = 0

        with open(self.log_file_name, 'rt', encoding='UTF8') as f:
            lines = f.readlines()

        start_time = time.time()
        batch_start_time = start_time
        self.batch_size = 10000
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(message)s')

        for line in lines:
            line = line.rstrip()
            result = self.template_miner.add_log_message(line)
            line_count += 1
            if line_count % self.batch_size == 0:
                time_took = time.time() - batch_start_time
                rate = self.batch_size / time_took
                self.logger.info(f"Processing line: {line_count}, rate {rate:.1f} lines/sec, "
                            f"{len(self.template_miner.drain.clusters)} clusters so far.")
                batch_start_time = time.time()
            if result["change_type"] != "none":
                result_json = json.dumps(result)
                self.logger.info(f"Input ({line_count}): " + line)
                self.logger.info("Result: " + result_json)

        time_took = time.time() - start_time
        rate = line_count / time_took
        self.logger.info(f"--- Done processing file in {time_took:.2f} sec. Total of {line_count} lines, rate {rate:.1f} lines/sec, "
                    f"{len(self.template_miner.drain.clusters)} clusters")

        sorted_clusters = sorted(self.template_miner.drain.clusters, key=lambda it: it.size, reverse=True)
        for cluster in sorted_clusters:
            self.logger.info(cluster)

        print("Prefix Tree:")
        self.template_miner.drain.print_tree()
        self.template_miner.profiler.report(0)

    def handle(self, logstring):
        result = self.template_miner.add_log_message(logstring)
        if result["change_type"] != "none":
            result_json = json.dumps(result)
            print("Result: " + result_json)

    def report(self):
        sorted_clusters = sorted(self.template_miner.drain.clusters, key=lambda it: it.size, reverse=True)
        for cluster in sorted_clusters:
            self.logger.info(cluster)

        print("Prefix Tree:")
        self.template_miner.drain.print_tree()
        self.template_miner.profiler.report(0)
