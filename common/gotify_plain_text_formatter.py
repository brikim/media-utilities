""" Gotify Plain Text Formatter """

import logging
from common.utils import remove_ansi_code_from_text


class GotifyPlainTextFormatter(logging.Formatter):
    """ Plain text formatter removes ansi codes for logging"""

    def format(self, record: logging.LogRecord):
        """ Formats the log record """
        return remove_ansi_code_from_text(record.msg)
