from configfile import ConfigWrapper
from cartographer.scanner import PrinterScanner


def load_config(config: ConfigWrapper):
    return PrinterScanner(config)
