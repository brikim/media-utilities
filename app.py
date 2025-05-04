"""
Media Utilities
"""

import sys
import os
import json
import signal
from apscheduler.schedulers.blocking import BlockingScheduler

from api.api_manager import ApiManager
from common import utils
from common.log_manager import LogManager
from service.service_manager import ServiceManager

MEDIA_UTILITIES_VERSION: str = "v3.5.0"

log_manager = LogManager(__name__)
api_manager: ApiManager = None
service_manager: ServiceManager = None
scheduler = BlockingScheduler()


def _exit_application(_sig_num, _frame):
    log_manager.log_info("Shutting down ...")
    service_manager.shutdown()
    scheduler.shutdown(wait=True)
    sys.exit(0)


def _keep_alive():
    """ Do nothing """


if "CONFIG_PATH" in os.environ:
    conf_loc_path_file = os.environ["CONFIG_PATH"].rstrip("/")
    if os.path.exists(conf_loc_path_file):
        try:
            # Opening JSON file
            with open(conf_loc_path_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            log_manager.log_info(
                f"Starting Media Utilities {MEDIA_UTILITIES_VERSION}"
            )

            # Set up signal termination handle
            signal.signal(signal.SIGTERM, _exit_application)
            signal.signal(signal.SIGINT, _exit_application)

            # Configure the gotify logging
            log_manager.configure_gotify(data)

            # Create the API Manager
            api_manager = ApiManager(data, log_manager)

            # Create the service manager
            service_manager = ServiceManager(
                api_manager, data, log_manager, scheduler
            )

            # Initialize service jobs
            service_manager.init_jobs()

            # Add a job to do nothing to keep the script alive
            scheduler.add_job(
                _keep_alive,
                trigger="interval",
                hours=24
            )

            # Start the scheduler for all jobs
            scheduler.start()

        except FileNotFoundError as e:
            log_manager.log_error(
                f"Config file not found: {utils.get_tag('error', e)}"
            )
        except json.JSONDecodeError as e:
            log_manager.log_error(
                f"Error decoding JSON in config file: {utils.get_tag('error', e)}"
            )
        except KeyError as e:
            log_manager.log_error(
                f"Missing key in config file: {utils.get_tag('error', e)}"
            )
        except Exception as e:
            log_manager.log_error(
                f"An unexpected error occurred: {utils.get_tag('error', e)}"
            )
    else:
        log_manager.log_error(
            f"Config file not found: {conf_loc_path_file}",
        )
else:
    log_manager.log_error("Environment variable CONFIG_PATH not found")

# END Main script run ####################################################
