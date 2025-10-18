import logging


def create_logger(logger_name: str):

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler("crawl.log")
    file_handler.setLevel(logging.INFO)
    
    logger.addHandler(file_handler)

    return logger 
