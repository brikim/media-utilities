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

MEDIA_UTILITIES_VERSION: str = "v3.2.1"

log_manager = LogManager(__name__)
api_manager: ApiManager = None
service_manager: ServiceManager = None
scheduler = BlockingScheduler()


def _handle_sigterm(_sig_num, _frame):
    log_manager.get_logger().info("SIGTERM received, shutting down ...")
    service_manager.shutdown()
    scheduler.shutdown(wait=True)
    sys.exit(0)


def _do_nothing():
    """ Do nothing """


if "CONFIG_PATH" in os.environ:
    conf_loc_path_file = os.environ["CONFIG_PATH"].rstrip("/")
    if os.path.exists(conf_loc_path_file):
        try:
            # Opening JSON file
            with open(conf_loc_path_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            log_manager.get_logger().info("Starting Media Utilities %s", MEDIA_UTILITIES_VERSION)

            # Main script run ####################################################

            # Set up signal termination handle
            signal.signal(signal.SIGTERM, _handle_sigterm)

            # Configure the gotify logging
            log_manager.configure_gotify(data)

            # Create the API Manager
            api_manager = ApiManager(data, log_manager.get_logger())

            # Create the service manager
            service_manager = ServiceManager(
                api_manager, data, log_manager.get_logger(), scheduler)

            # Initialize service jobs
            service_manager.init_jobs()

            # Add a job to do nothing to keep the script alive
            scheduler.add_job(
                _do_nothing,
                trigger="interval",
                hours=24
            )

            # Start the scheduler for all jobs
            scheduler.start()

        except FileNotFoundError as e:
            log_manager.get_logger().error(
                "Config file not found: %s", utils.get_tag('error', e)
            )
        except json.JSONDecodeError as e:
            log_manager.get_logger().error(
                "Error decoding JSON in config file: %s",
                utils.get_tag('error', e)
            )
        except KeyError as e:
            log_manager.get_logger().error(
                "Missing key in config file: %s", utils.get_tag('error', e)
            )
        except Exception as e:
            log_manager.get_logger().error(
                "An unexpected error occurred: %s", utils.get_tag('error', e)
            )
    else:
        log_manager.get_logger().error(
            "Error finding config file %s", conf_loc_path_file
        )
else:
    log_manager.get_logger().error("Environment variable CONFIG_PATH not found")

# END Main script run ####################################################
