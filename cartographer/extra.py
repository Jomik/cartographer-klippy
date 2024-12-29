from configfile import ConfigWrapper
from cartographer import PrinterCartographer
from cartographer.temperature import PrinterTemperatureCoil


def load_config(config: ConfigWrapper):
    pheaters = config.get_printer().load_object(config, "heaters")
    pheaters.add_sensor_factory("cartographer_coil", PrinterTemperatureCoil)
    return PrinterCartographer(config)
