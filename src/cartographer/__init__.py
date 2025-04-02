import logging

logger = logging.getLogger(__name__)

formatter = logging.Formatter("[%(levelname)s:%(name)s] %(msg)s")
handler = logging.NullHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)
