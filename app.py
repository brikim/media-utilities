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

from service.ServiceBase import ServiceBase
from service.DeleteWatched import DeleteWatched
from service.DvrMaintainer import DvrMaintainer
from service.FolderCleanup import FolderCleanup
from service.PlaylistSync import PlaylistSync
from service.SyncWatched import SyncWatched

MEDIA_UTILITIES_VERSION: str = "v3.0.0"

log_manager = LogManager(__name__)
api_manager: ApiManager = None
scheduler = BlockingScheduler()

# Available Services
services: list[ServiceBase] = []
##########################

def _handle_sigterm(_sig_num, _frame):
    log_manager.get_logger().info("SIGTERM received, shutting down ...")
    for service_base in services:
        service_base.shutdown()
    scheduler.shutdown(wait=True)
    sys.exit(0)

def _do_nothing():
    """ Do nothing """

config_path_valid: bool = "CONFIG_PATH" in os.environ
if config_path_valid:
    conf_loc_path_file = os.environ["CONFIG_PATH"].rstrip("/")
    if os.path.exists(conf_loc_path_file):
        try:
            # Opening JSON file
            with open(os.environ["CONFIG_PATH"].rstrip("/"), "r", encoding="utf-8") as f:
                data = json.load(f)

            # Main script run ####################################################

            # Set up signal termination handle
            signal.signal(signal.SIGTERM, _handle_sigterm)

            # Configure the gotify logging
            log_manager.configure_gotify(data)

            log_manager.get_logger().info("Starting Media Utilities %s", MEDIA_UTILITIES_VERSION)

            # Create the API Manager
            api_manager = ApiManager(data, log_manager.get_logger())

            # Create the services ####################################

            # Create the Sync Watched Status Service
            if "sync_watched" in data and data["sync_watched"]["enabled"] == "True":
                services.append(
                    SyncWatched(
                        f"{utils.ANSI_CODE_START}45{utils.ANSI_CODE_END}",
                        api_manager,
                        data["sync_watched"],
                        log_manager.get_logger(),
                        scheduler
                    )
                )
            if "delete_watched" in data and data["delete_watched"]["enabled"] == "True":
                services.append(
                    DeleteWatched(
                        f"{utils.ANSI_CODE_START}142{utils.ANSI_CODE_END}",
                        api_manager,
                        data["delete_watched"],
                        log_manager.get_logger(),
                        scheduler
                    )
                )
            if "dvr_maintainer" in data and data["dvr_maintainer"]["enabled"] == "True":
                services.append(
                    DvrMaintainer(
                        f"{utils.ANSI_CODE_START}210{utils.ANSI_CODE_END}",
                        api_manager,
                        data["dvr_maintainer"],
                        log_manager.get_logger(),
                        scheduler
                    )
                )
            if "folder_cleanup" in data and data["folder_cleanup"]["enabled"] == "True":
                services.append(
                    FolderCleanup(
                        f"{utils.ANSI_CODE_START}70{utils.ANSI_CODE_END}",
                        api_manager,
                        data["folder_cleanup"],
                        log_manager.get_logger(),
                        scheduler
                    )
                )
            if "playlist_sync" in data and data["playlist_sync"]["enabled"] == "True":
                services.append(
                    PlaylistSync(
                        f"{utils.ANSI_CODE_START}171{utils.ANSI_CODE_END}",
                        api_manager,
                        data["playlist_sync"],
                        log_manager.get_logger(),
                        scheduler
                    )
                )
#
            # ########################################################

            # Init the services ######################################
            for service in services:
                service.init_scheduler_jobs()
            # ########################################################

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