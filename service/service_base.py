""" Service Base class for all services"""

from logging import Logger
from typing import Optional
from apscheduler.schedulers.blocking import BlockingScheduler

from common import utils
from common.types import CronInfo

from api.api_manager import ApiManager


class ServiceBase:
    """ Base class for services """

    def __init__(
        self,
        ansi_code: str,
        service_name: str,
        config: dict,
        api_manager: ApiManager,
        logger: Logger,
        scheduler: BlockingScheduler
    ):
        self.api_manager = api_manager
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
        """ Log an info message """
        self.logger.info(f"{self.log_header} {message}")

    def log_warning(self, message: str):
        """ Log a warning message """
        self.logger.warning(f"{self.log_header} {message}")

    def log_error(self, message: str):
        """ Log an error message """
        self.logger.error(f"{self.log_header} {message}")

    def log_service_enabled(self):
        """ Log that the service is enabled """
        if self.cron is not None:
            self.log_info(
                f"Enabled - Running every {utils.get_tag("hour", self.cron.hours)} "
                f"{utils.get_tag("minute", self.cron.minutes)}"
            )
        else:
            self.log_info("Enabled")

    def init_scheduler_jobs(self):
        """ Initialize the scheduler jobs. Children can override """

    def shutdown(self):
        """ Shutdown the service. Children can override """
