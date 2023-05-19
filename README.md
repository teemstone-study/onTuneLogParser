# onTuneLogParser

## drain3.ini File Configuration

Drain3 is configured using [configparser](https://docs.python.org/3.4/library/configparser.html). By default, config
filename is `drain3.ini` in working directory. It can also be configured passing
a [TemplateMinerConfig](drain3/template_miner_config.py) object to the [TemplateMiner](drain3/template_miner.py)
constructor.

Primary configuration parameters:

- `[DRAIN]/sim_th` - similarity threshold. if percentage of similar tokens for a log message is below this number, a new log cluster will be created (default 0.4)
- `[DRAIN]/depth` - max depth levels of log clusters. Minimum is 2. (default 4)
- `[DRAIN]/max_children` - max number of children of an internal node (default 100)
- `[DRAIN]/max_clusters` - max number of tracked clusters (unlimited by default). When this number is reached, model
  starts replacing old clusters with a new ones according to the LRU cache eviction policy.
- `[DRAIN]/extra_delimiters` - delimiters to apply when splitting log message into words (in addition to whitespace) (
  default none). Format is a Python list e.g. `['_', ':']`.
- `[MASKING]/masking` - parameters masking - in json format (default "")
- `[MASKING]/mask_prefix` & `[MASKING]/mask_suffix` - the wrapping of identified parameters in templates. By default, it
  is `<` and `>` respectively.
- `[SNAPSHOT]/snapshot_interval_minutes` - time interval for new snapshots (default 1)
- `[SNAPSHOT]/compress_state` - whether to compress the state before saving it. This can be useful when using Kafka
  persistence.

## Setting.yaml File Configuration

The Setting.yaml file takes precedence over the drain3.ini file.

This file is configured for monitoring targets and allows for directories, Windows system monitoring, and Linux system monitoring.

### Common configuration parameters:

- `interval` - Specifies the monitoring target interval in seconds.
- `minimum-length` - Determines the minimum length of the target log to train and infer.
- `mode` - Sets the mode to either `training` or `inference` (default: `training`).
- `report` - Specifies whether to show a training report (true or false, default: false).
- `initial-check`
  * `directory`: Checks all files in the directory initially.
  * `Windows Event`: Checks all events for the current day, saves the event_log file, and performs an initial check on the event_log file.
- `similarity-threshold` - Sets the similarity threshold for Drain3 (sim_th value, default: 0.4).
- `match-rate` 
  * Used only in `inference` mode.
  * Matches logs with training data except for logs containing specific words.
  * The value should be between 0 and 1 (default: 0).
  * If the value is 0, the variable is unused.
  * If the value is 1, all logs are matched.
  * If the value is 0.01, only clusters with less than 1 percent match.
  * This parameter is exclusively used with the `match-max-count` parameter.
- `match-max-count`
  * Used only in `inference` mode.
  * Matches logs with training data except for logs containing specific words.
  * The value can be 0 or a natural number.
  * If the value is 0, the variable is unused.
  * If the value is 1, only clusters of size 1 are matched.
  * If the value is 10, only clusters of size less than 10 are matched.
  * This parameter is exclusively used with the `match-rate` parameter.
- `compress-state` - Specifies the Drain3 compress_state value (default: true).
- `parametrize-numeric-tokens` - Specifies the Drain3 parametrize_numeric_tokens value (default: True).

### Monitoring Configuration Parameters:
- All common parameters can be used in monitoring parameters, and monitoring parameters take precedence over common parameters.
- `type` - Specifies either `normal` or `windows-event` (default: `normal`).
- `name` - Specifies the log parsing monitoring name, used to create reports, offsets, and inference files (default: "").
- `snapshot-file` - Specifies the log parsing training file name (must be declared).
- `words` 
  * Array of specific words.
  * If a log contains these words, the log must be matched regardless of the match-rate or match-max-count.
  * Default: [].
- `ignore-words`
  * Array of words to ignore.
  * These words are removed during training.
  * Default: [].
- `custom-masking-words`
  * Array of custom masking words.
  * `custom-masking-words/source` - Specifies the source regular expression (e.g., `([A-Za-z]+)_(\d+)`).
  * `custom-masking-words/target` - Specifies the target regular expression (e.g., `\1-<:DATETIME:>`).
  * warning - Do not use `<:*:>` in the source and target because it is Drain3's custom masking pattern. Using this pattern will render the training data invalid.
  * Default: [].
- `no-datetime-log`
  * Used only when `monitoring/date-time-format` is used.
  * Can be set to either `streaming` or `separate` (default: `separate`).
  * `streaming`: If a log doesn't contain `monitoring/date-time-format`, the log is considered to follow the previous log.
  * `separate`: Regardless of `monitoring/date-time-format`, each log is considered independent.
- `monitoring/directory`
  * Specifies the directory to monitor.
  * `normal`: For monitoring a specific directory.
  * `windows-event`: For monitoring a directory to save Windows events.
  * Must be declared.
- `monitoring/pattern`
  * Can be used with `none`, `day`, `hour`, `minute`, or a customized date-time format (default: `none`).
  * `none`: No postfix for the file.
  * `day`: The file's postfix follows the `yyMMDD` or `yyMMDD00` date format.
  * `hour`: The file's postfix follows the `yyMMDDHH` date-time format.
  * `minute`: The file's postfix follows the `yyMMDDHHmm` date-time format.
  * Customized date-time format: Can be a customized format (e.g., `yyyy-MM-dd_HHmmss`).
- `monitoring/extension`: Specifies the file extension for monitoring files (default: `txt`).
- `monitoring/file`
  * Specifies the monitoring file name and must be declared.
  * If `monitoring/pattern` is not set to `none`, the file name can use the file's prefix.
  * The monitoring file name follows the format: `{monitoring/file}_{monitoring/pattern}.{monitoring/extension}`
- `monitoring/date-time-format`
  * Different from `monitoring/pattern`
  * If a log has the format `yyyy-MM-DD HH:mm:ss blah blah ...`:
    * During training execution, the log's date-time-format (`yyyy-MM-DD HH:mm:ss`) is removed, and the remaining data is used as training data.
    * The training data will be `blah blah ...`
  * If used, it can also be used by `no-datetime-log`

  