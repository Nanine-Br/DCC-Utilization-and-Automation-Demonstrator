import logging
import os

class myLogger:
    @staticmethod
    def getLogger(name="logger", path=None):
        if path is None:
            path = os.path.join(os.path.dirname(__file__), "Demonstrator_file.log")
        logger = logging.getLogger(name)
        f_handler = logging.FileHandler(path, encoding="utf-8")
        logger.addHandler(f_handler)
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(filename)s -  %(levelname)s - %(message)s ')
        f_handler.setFormatter(formatter)
        return logger
