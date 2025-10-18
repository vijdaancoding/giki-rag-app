import logging


def create_logger(logger_name: str, file_name : str = "crawl.log"):

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler(file_name)
    file_handler.setLevel(logging.INFO)
    
    logger.addHandler(file_handler)

    return logger 
