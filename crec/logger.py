import queue
import logging
from logging.handlers import QueueHandler, QueueListener


class DuplicateFilter(logging.Filter):
    def filter(self, record):
        current_message = record.msg
        last_message = getattr(self, "last_message", '')
        if 'rate limit' in current_message and 'rate limit' in last_message:
            return False
        else:
            self.last_message = current_message
            return True


class Logger:
    def __init__(self, verbose: bool, logger_outpath: str) -> None:
        self.verbose = verbose

        self.log_queue = queue.Queue(-1)
        self.queue_handler = QueueHandler(self.log_queue)

        self.logger = logging.getLogger()
        self.logger.addHandler(self.queue_handler)
        self.logger.setLevel(logging.INFO)
        self.logger.addFilter(DuplicateFilter())

        self.formatter = logging.Formatter(fmt='%(asctime)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        
        self.stream_handler = logging.StreamHandler()
        self.stream_handler.setFormatter(self.formatter)

        if logger_outpath is not None:
            self.file_handler = logging.FileHandler(filename=logger_outpath)
            self.file_handler.setFormatter(self.formatter)
            self.listener = QueueListener(self.log_queue, self.stream_handler, self.file_handler)
        else:
            self.listener = QueueListener(self.log_queue, self.stream_handler)
        
        self.listener.start()

    def stop(self):
        self.listener.stop()

    def log(self, message):
        if self.verbose:
            self.logger.info(msg=message)