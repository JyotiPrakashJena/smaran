import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

LOG_PATH = Path(__file__).parent / "logs" / "smaran.log"
LOG_PATH.parent.mkdir(exist_ok=True)

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")
    fh = TimedRotatingFileHandler(LOG_PATH, when="midnight", backupCount=7, encoding="utf-8")
    fh.setFormatter(fmt)
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger
