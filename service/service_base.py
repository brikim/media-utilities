""" Service Base class for all services"""

from typing import Optional
from apscheduler.schedulers.blocking import BlockingScheduler

from common import utils
from common.log_manager import LogManager
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
        log_manager: LogManager,
        scheduler: BlockingScheduler
    ):
        self.api_manager = api_manager
        self.log_manager = log_manager
        self.scheduler = scheduler
        self.cron: Optional[CronInfo] = None
        self.log_header = utils.get_log_header(ansi_code, service_name)

        if "cron_run_rate" in config:
            self.cron = utils.get_cron_from_string(config["cron_run_rate"])
            if self.cron is None:
                self.log_warning(
                    f"Invalid cron expression {utils.get_tag("cron_run_rate", config["cron_run_rate"])}"
                )

    def log_info(self, message: str):
        """ Log an info message """
        self.log_manager.log_info(f"{self.log_header} {message}")

    def log_warning(self, message: str):
        """ Log a warning message """
        self.log_manager.log_warning(f"{self.log_header} {message}")

    def log_error(self, message: str):
        """ Log an error message """
        self.log_manager.log_error(f"{self.log_header} {message}")

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
