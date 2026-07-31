import logging
import os

LOG_DIR = "/opt/pg_sa/backend/logs"

os.makedirs(LOG_DIR, exist_ok=True)


def get_logger(name, logfile):

    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    handler = logging.FileHandler(
        os.path.join(LOG_DIR, logfile)
    )

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    handler.setFormatter(formatter)

    logger.addHandler(handler)

    return logger


backend_logger = get_logger(
    "backend",
    "backend.log"
)

ansible_logger = get_logger(
    "ansible",
    "ansible.log"
)

deployment_logger = get_logger(
    "deployment",
    "deployment.log"
)
