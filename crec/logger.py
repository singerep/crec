import queue
import logging
from logging.handlers import QueueHandler, QueueListener
import datetime
from typing import Union

logging.getLogger("httpx").setLevel(logging.WARNING)


class DuplicateFilter(logging.Filter):
    """
    A custom class that inherits from :class:`.logging.Filter` to filter out duplicate
    rate limit logs.

    Parameters
    ----------
    rate_limit_wait : Union[bool, int]
        Determines how long the filter should wait before outputting another rate limit
        error message.
    """
    def __init__(self, rate_limit_wait: Union[bool, int]) -> None:
        super().__init__()

        self.rate_limit_wait = rate_limit_wait if type(rate_limit_wait) == int else None

    def filter(self, record):
        """
        Determines whether or not to output the current record. First, this function
        checks to see whether the last two messages in a row were both rate limit
        exceptions. Then, it checks whether less than ``rate_limit_wait`` time has 
        passed. If all conditions are ``True`` then the record is skipped. 
        Otherwise, the record is outputted.
        """
        current_message = record.msg
        current_message_time = datetime.datetime.now()
        last_message = getattr(self, "last_message", '')
        last_message_time = getattr(self, "last_message_time", datetime.datetime.min)
        if 'rate limit' in current_message:
            if 'rate limit' in last_message:
                if self.rate_limit_wait is not None and current_message_time < last_message_time + datetime.timedelta(seconds=self.rate_limit_wait):
                    return False
        
        self.last_message = current_message
        self.last_message_time = current_message_time
        return True


class Logger:
    """
    A custom logger to handle the logging of status updates. Maintains a logging queue
    so that logs which are sent during an asynchronous event loop are non-blocking.

    Parameters
    ----------
    rate_limit_wait : Union[bool, int]
        Determines how long the logger should wait before outputting another rate limit
        error message.
    print_logs : bool
        A boolean that determines whether or not logs are printed to stdout.
    write_logs : bool
        A boolean that determines whether or not logs are written to disk.
    write_path : str = None
        A filename to write logs to. Must be provided if ``write_logs`` is ``True``.
    """
    def __init__(self, rate_limit_wait: Union[bool, int], print_logs: bool, write_logs: bool, write_path: str) -> None:
        self.print_logs = print_logs
        self.write_logs = write_logs
        self.write_path = write_path

        self.log_queue = queue.Queue(-1)
        self.queue_handler = QueueHandler(self.log_queue)

        self.logger = logging.getLogger()
        self.logger.addHandler(self.queue_handler)
        self.logger.setLevel(logging.INFO)
        self.logger.addFilter(DuplicateFilter(rate_limit_wait=rate_limit_wait))

        self.formatter = logging.Formatter(fmt='%(levelname)s:%(asctime)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

        handlers = []

        if self.print_logs:
            self.stream_handler = logging.StreamHandler()
            self.stream_handler.setFormatter(self.formatter)
            handlers.append(self.stream_handler)
        
        if self.write_logs:
            if self.write_path is None:
                raise Exception('If writing logs, write_path must be specified')
            
            self.file_handler = logging.FileHandler(filename=self.write_path)
            self.file_handler.setFormatter(self.formatter)
            handlers.append(self.file_handler)

        self.listener = QueueListener(self.log_queue, *handlers)
        
        self.listener.start()

    def log(self, message: str, level: str = 'info') -> None:
        """
        Outputs a log.

        Parameters
        ----------
        message : str
            The message to be logged.
        level : str
            The level for the message to be logged.
        """
        if level == 'info':
            self.logger.info(msg=message)
        elif level == 'warning':
            self.logger.warning(msg=message)