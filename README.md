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

Setting.yaml File is prior to drain3.ini File.

This is configured by some monitoring targets. It allows directories, Windows system monitoring and will apply Linux system monitoring.

### Common configuration parameters:

- `interval` - monitoring target interval (secs)
- `minimum-length` - allows to train and infer the target log's length
- `mode` - either `training` or `inference`(default `training`)
- `report` - want to show a training report, true or false(default false)
- `initial-check`
  * directory: check all files in the directory initially 
  * Windows Event: check today's all events and save the event_log file, and check the event_log file initially
- `similarity-threshold` - Drain3 `sim_th` value, refer to drain3-sim_th(default 0.4)
- `match-rate` 
  * used only when mode is `inference`
  * except logs that contains specific words, match logs with the training data in the others 
  * between 0 and 1(default 0)
  * if a value is 0 then the variable is unused 
  * if a value is 1 then the all logs are matched
  * if a value is 0.01, that means lower than 1 percent clusters are only matched
  * exclusively using the parameter `match-max-count`
- `match-max-count`
  * used only when mode is `inference`
  * except logs that contains specific words, match logs with the training data in the others
  * values are allowed to 0 or natural numbers.
  * if a value is 0 then the variable is unused
  * if a value is 1 then only 1 size clusters are matched
  * if a value is 10 then lower than 10 size clusters are matched
  * execlusively using the parameter `match-rate`
- `compress-state` - Drain3 `compress_state` values, refer to drain3-compress_state(default true)
- `parametrize-numeric-tokens` - Drain3 `parametrize_numeric_tokens` value, refer to drain3-TemplateMinerConfig.parametrize_numeric_tokens(default True)

### Monitoring Configuration Parameters:
- All common parameters can use in the monitoring parameters and monitoring parameters is prior to common parameters.
- `type` - either `normal`, `windows-event`(default `normal`)
- `name` - log parsing monitoring name, it is used to create report, offset, inference files(default ``)
- `snapshot-file` - log parsing training file name, it must be declared
- `words` 
  * array of specific words
  * regardless of `match-rate` or `match-max-count`, if a log contains the words, the log must be matched
  * default []
- `ignore-words`
  * array of ignore words
  * the words are removed when execute training
  * default []
- `custom-masking-words`
  * array of custom masking words
  * `custom-masking-words/source` - source regular expression(e.g `([A-Za-z]+)_(\d+)`)
  * `custom-masking-words/target` - target regular expression(e.g `\1-<:DATETIME:>`)
  * warning - `source` and `target` don't use `<:*:>` because the pattern is drain3's custom masking pattern, if the pattern is used then training data is not valid
  * default []
- `no-datetime-log`
  * used only `monitoring/date-time-format` is used
  * either `streaming` or `separate`(default `separate`)
  * `streaming`: if a log doesn't contain `monitoring/date-time-format` then the log is considered to follow the previous log
  * `separate`: regardless of `monitoring/date-time-format`, a log is consideres to an independent log
- `monitoring/directory`
  * normal: monitor a specific directory
  * windows-event: monitor a directory to save the windows event
  * must be declared
- `monitoring/pattern`
  * can be used in `none`, `day`, `hour`, `minute` and a customized date-time format(default `none`)
  * `none`: no file's postfix
  * `day`: file's postfix is `yyMMDD` or `yyMMDD00` date format
  * `hour`: file's postfix is `yyMMDDHH` date-time format
  * `minute`: file's postfix is `yyMMDDHHmm` date-time format
  * customized date-time format: can be used a cutomized format(e.g `yyyy-MM-dd_HHmmss`)
- `monitoring/extension`: monitoring file's extension(default `txt`)
- `monitoring/file`
  * monitoring file name, it must be declared
  * except `monitoring/pattern` is `none`, the file name is can be used the file's prefix
  * monitor the file's name is `{monitoring/file}_{monitoring/pattern}.{monitoring/extension}`
- `monitoring/date-time-format`
  * it is different to `monitoring/pattern`
  * if a log is `yyyy-MM-DD HH:mm:ss blah blah ...`
    * when to execute training, the log's date-time-format(`yyyy-MM-DD HH:mm:ss`) is removed and remaining data is used by a training data
    * a training data is `blah blah ...`
  * if it is used, also can be used by `no-datetime-log`

  