import logging


def configure_logger(name = 'server', logfile = 'server.log'):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Checking if the logger has any handlers to avoid duplication
    if not logger.handlers:
        file_handler = logging.FileHandler(logfile)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
