import logging
import sys

logger = logging.getLogger("arrest")
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.INFO)
