from celery.utils.log import get_task_logger
import logging
import json

class LoggerSetup:
    def __init__(self, logger_name, level=logging.INFO):
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(level)
        self._setup_handler()

    def _setup_handler(self):
        # Avoid adding duplicate handlers
        if not self.logger.handlers:
            # Create a console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)

            # Use a custom formatter
            formatter = JsonOrTextFormatter()
            console_handler.setFormatter(formatter)

            # Add the handler to the logger
            self.logger.addHandler(console_handler)

    def get_logger(self):
        return self.logger

    def set_level(self, level):
        """
        Set the logging level for the logger and its handlers.
        """
        self.logger.setLevel(level)
        for handler in self.logger.handlers:
            handler.setLevel(level)

class JsonOrTextFormatter(logging.Formatter):
    FILENAME_WIDTH = 30  # Fixed width for filenames

    def format(self, record):
        # Add timestamp and file name to the log record
        record.time = self.formatTime(record, datefmt="%Y-%m-%d %H:%M:%S")
        filename = record.pathname.split("/")[-1]
        record.filename = filename[: self.FILENAME_WIDTH].center(self.FILENAME_WIDTH)

        try:
            # If the log message is a dictionary or JSON-compatible, format it as pretty JSON
            if isinstance(record.msg, dict):
                record.msg = json.dumps(record.msg, indent=4, sort_keys=True)
            elif isinstance(record.msg, str):
                # Try to parse as JSON string
                record.msg = json.dumps(json.loads(record.msg), indent=4, sort_keys=True)
        except (json.JSONDecodeError, TypeError):
            # If not JSON-compatible, use the standard log message
            pass

        # Format the message with proper alignment
        formatted_msg = record.msg.replace("\n", "\n " + " " * (len(record.time) + len(record.filename) + 6))

        return f"[{record.time}] [{record.filename}] {formatted_msg}"


# Set up your logger
logger = LoggerSetup(__name__).get_logger()

# Configure Celery logger to use the same formatter
celery_logger = get_task_logger(__name__)
celery_logger.setLevel(logging.DEBUG)

# Remove existing handlers to avoid duplicates
celery_logger.handlers.clear()

# Add the custom handler with the custom formatter
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(JsonOrTextFormatter())
celery_logger.addHandler(console_handler)
