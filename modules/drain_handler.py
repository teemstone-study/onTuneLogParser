import time
import sys
import json
from os.path import dirname
from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig

class DrainHandler:
    def __init__(self, drainfilename):
        self.config_file_name = dirname(__file__) + "\\..\\drain3.ini"
        self.drain_file_name = drainfilename

        config = TemplateMinerConfig()
        config.load(self.config_file_name)
        config.profiling_enabled = True
        self.template_miner = TemplateMiner(config=config)
        self.line_count = 0

        self.start_time = time.time()
        self.batch_start_time = time.time()
        self.batch_size = 10000

    def handle(self, line):
        line = line.rstrip()
        result = self.template_miner.add_log_message(line)
        self.line_count += 1

        with open(self.drain_file_name, 'a', encoding='UTF8') as f:
            if self.line_count % self.batch_size == 0:
                time_took = time.time() - self.batch_start_time
                rate = self.batch_size / time_took
                f.writelines(f"Processing line: {self.line_count}, rate {rate:.1f} lines/sec, "
                    f"{len(self.template_miner.drain.clusters)} clusters so far.")
                self.batch_start_time = time.time()
            if result["change_type"] != "none":
                result_json = json.dumps(result)
                f.writelines(f"Input ({self.line_count}): {line}")
                f.writelines(f"Result: {result_json}")

            f.close()

    def report(self):
        time_took = time.time() - self.start_time
        rate = self.line_count / time_took

        sys.stdout = open(self.drain_file_name, 'a', encoding='UTF8')
        print(f"--- Done processing file in {time_took:.2f} sec. Total of {self.line_count} lines, rate {rate:.1f} lines/sec, "
                    f"{len(self.template_miner.drain.clusters)} clusters")

        sorted_clusters = sorted(self.template_miner.drain.clusters, key=lambda it: it.size, reverse=True)
        for cluster in sorted_clusters:
            print(str(cluster))

        print("\n")
        print("--- Prefix Tree:")
        self.template_miner.drain.print_tree()

        print("\n")
        print("--- Profiler Report:\n")
        self.template_miner.profiler.report(0)
        sys.stdout.close()