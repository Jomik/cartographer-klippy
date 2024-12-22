from configfile import ConfigWrapper
from cartographer import PrinterCartographer


def load_config(config: ConfigWrapper):
    return PrinterCartographer(config)
