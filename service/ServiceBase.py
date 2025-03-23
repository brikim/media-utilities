from logging import Logger
from apscheduler.schedulers.blocking import BlockingScheduler
from common import utils
from common.types import CronInfo
from typing import Optional


class ServiceBase:
    def __init__(
        self,
        ansi_code: str,
        service_name: str,
        config: dict,
        logger: Logger,
        scheduler: BlockingScheduler
    ):
        self.logger = logger
        self.scheduler = scheduler
        self.cron: Optional[CronInfo] = None
        self.log_header = utils.get_log_header(ansi_code, service_name)
        
        if "cron_run_rate" in config:
            self.cron = utils.get_cron_from_string(
                config["cron_run_rate"],
                self.logger,
                self.__module__
            )
    
    def log_info(self, message: str):
        self.logger.info(f"{self.log_header} {message}")

    def log_warning(self, message: str):
        self.logger.warning(f"{self.log_header} {message}")
        
    def log_error(self, message: str):
        self.logger.error(f"{self.log_header} {message}")
    
    def log_service_enabled(self):
        if self.cron is not None:
            self.log_info(
                f"Enabled - Running every {utils.get_tag("hour", self.cron.hours)} {utils.get_tag("minute", self.cron.minutes)}"
            )
        else:
            self.log_info("Enabled")
        
    def init_scheduler_jobs(self):
        pass
    
    def shutdown(self):
        pass
