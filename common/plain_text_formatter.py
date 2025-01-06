import logging
from datetime import datetime

# Plain text formatter removes ansi codes for logging
class PlainTextFormatter(logging.Formatter):
    def format(self, record):
        date_time = datetime.fromtimestamp(record.created)
        date_string = date_time.strftime('%Y-%m-%d %H:%M:%S')
        
        plain_text = record.msg
        while True:
            index = plain_text.find('\33[')
            if (index < 0):
                break
            else:
                end_index = plain_text.find('m', index)
                if end_index < 0:
                    break
                else:
                    end_index += 1
                    plain_text = plain_text[:index] + plain_text[end_index:]
        
        return '{} - {} - {}'.format(date_string, record.levelname, plain_text)
