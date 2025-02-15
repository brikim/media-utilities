from logging import Logger
from apscheduler.schedulers.blocking import BlockingScheduler
from common import utils

class ServiceBase:
    def __init__(self, ansi_code: str, service_name: str, config, logger: Logger, scheduler: BlockingScheduler):
        self.logger = logger
        self.scheduler = scheduler
        self.cron = None
        self.log_header = utils.get_log_header(ansi_code, service_name)
        
        if 'cron_run_rate' in config:
            self.cron = utils.get_cron_from_string(config['cron_run_rate'], self.logger, self.__module__)
    
    def __log_msg(self, type: str, message: str):
        if type == 'warning':
            self.logger.warning('{} {}'.format(self.log_header, message))
        elif type == 'error':
            self.logger.error('{} {}'.format(self.log_header, message))
        else:
            self.logger.info('{} {}'.format(self.log_header, message))

    def log_info(self, message: str):
        self.__log_msg('info', message)
    
    def log_info(self, message: str):
        self.__log_msg('info', message)
        
    def log_warning(self, message: str):
        self.__log_msg('warning', message)
        
    def log_error(self, message: str):
        self.__log_msg('error', message)
    
    def log_service_enabled(self):
        if self.cron is not None:
            self.log_info('Enabled - Running every {} {}'.format(utils.get_tag('hour', self.cron.hours), utils.get_tag('minute', self.cron.minutes)))
        else:
            self.log_info('Enabled')
        
    def init_scheduler_jobs(self):
        pass
    
    def shutdown(self):
        pass
