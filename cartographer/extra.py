import logging
from klippy import configfile


def load_config(_config: configfile.ConfigWrapper):
    logging.info("Loaded cartographer extra!")
