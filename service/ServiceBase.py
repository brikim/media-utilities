
from common.utils import get_cron_from_string, get_log_ansi_code, get_tag_ansi_code, get_plex_ansi_code, get_emby_ansi_code

class ServiceBase:
    def __init__(self, ansi_code, service_name, config, logger, scheduler):
        self.service_ansi_code = ansi_code
        self.service_name = service_name
        self.logger = logger
        self.scheduler = scheduler
        self.cron = None
        self.formatted_plex = '{}Plex{}'.format(get_plex_ansi_code(), get_log_ansi_code())
        self.formatted_emby = '{}Emby{}'.format(get_emby_ansi_code(), get_log_ansi_code())
        
        if 'cron_run_rate' in config:
            self.cron = get_cron_from_string(config['cron_run_rate'], self.logger, self.__module__)
    
    def get_log_header(self):
        return '{}{}{}:'.format(self.service_ansi_code, self.service_name, get_log_ansi_code())
    
    def _log_msg(self, type, message):
        if type == 'warning':
            self.logger.warning('{} {}'.format(self.get_log_header(), message))
        elif type == 'error':
            self.logger.error('{} {}'.format(self.get_log_header(), message))
        else:
            self.logger.info('{} {}'.format(self.get_log_header(), message))

    def log_info(self, message):
        self._log_msg('info', message)
    
    def log_info(self, message):
        self._log_msg('info', message)
        
    def log_warning(self, message):
        self._log_msg('warning', message)
        
    def log_error(self, message):
        self._log_msg('error', message)
    
    def log_service_enabled(self):
        if self.cron is not None:
            self.log_info('Enabled - Running every {}hour={}{} {}minute={}{}'.format(get_tag_ansi_code(), get_log_ansi_code(), self.cron.hours, get_tag_ansi_code(), get_log_ansi_code(), self.cron.minutes))
        else:
            self.log_info('Enabled')
    
    def get_tag(self, tag_name, tag_value):
        return '{}{}={}{}'.format(get_tag_ansi_code(), tag_name, get_log_ansi_code(), tag_value)
        
    def init_scheduler_jobs(self):
        pass
    
    def shutdown(self):
        pass
