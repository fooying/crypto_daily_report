from __future__ import annotations

import logging
from logging import Logger

from .config import ScriptConfig


LOG_FORMAT = '%(asctime)s %(levelname)s %(name)s %(message)s'


def configure_logging(config: ScriptConfig) -> None:
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    root_logger.setLevel(getattr(logging, config.log_level.upper(), logging.INFO))
    formatter = logging.Formatter(LOG_FORMAT)

    file_handler = logging.FileHandler(config.log_file)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)


def get_logger(name: str) -> Logger:
    return logging.getLogger(name)
