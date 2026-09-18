import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logger(name: str = "neteasedaily2am", log_dir: str = "logs") -> logging.Logger:
    """
    配置并返回文件日志记录器，支持自动创建目录与文件轮转
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        log_file = Path(log_dir) / "sync.log"

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,  # 单个日志文件最大 5MB
            backupCount=5,              # 最多保留 5 个历史备份
            encoding="utf-8",
        )
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
