""" Service Manager """

from logging import Logger
from apscheduler.schedulers.blocking import BlockingScheduler

from common import utils
from api.api_manager import ApiManager

from service.service_base import ServiceBase
from service.delete_watched import DeleteWatched
from service.dvr_maintainer import DvrMaintainer
from service.folder_cleanup import FolderCleanup
from service.playlist_sync import PlaylistSync
from service.media_server_sync import MediaServerSync


class ServiceManager:
    """
    Manages the services to be run.
    """

    def __init__(
        self,
        api_manager: ApiManager,
        config: dict,
        logger: Logger,
        scheduler: BlockingScheduler
    ):
        """ Initializes the Service Manager """

        # Available Services
        self.services: list[ServiceBase] = []
        self.api_manager = api_manager
        self.logger = logger
        self.scheduler = scheduler

        # Create the Media Server Sync Service
        if "media_server_sync" in config and config["media_server_sync"]["enabled"] == "True":
            self.services.append(
                MediaServerSync(
                    f"{utils.ANSI_CODE_START}45{utils.ANSI_CODE_END}",
                    api_manager,
                    config["media_server_sync"],
                    self.logger,
                    scheduler
                )
            )

        if "delete_watched" in config and config["delete_watched"]["enabled"] == "True":
            self.services.append(
                DeleteWatched(
                    f"{utils.ANSI_CODE_START}142{utils.ANSI_CODE_END}",
                    api_manager,
                    config["delete_watched"],
                    self.logger,
                    scheduler
                )
            )

        if "dvr_maintainer" in config and config["dvr_maintainer"]["enabled"] == "True":
            self.services.append(
                DvrMaintainer(
                    f"{utils.ANSI_CODE_START}210{utils.ANSI_CODE_END}",
                    api_manager,
                    config["dvr_maintainer"],
                    self.logger,
                    scheduler
                )
            )

        if "folder_cleanup" in config and config["folder_cleanup"]["enabled"] == "True":
            self.services.append(
                FolderCleanup(
                    f"{utils.ANSI_CODE_START}70{utils.ANSI_CODE_END}",
                    api_manager,
                    config["folder_cleanup"],
                    self.logger,
                    scheduler
                )
            )

        if "playlist_sync" in config and config["playlist_sync"]["enabled"] == "True":
            self.services.append(
                PlaylistSync(
                    f"{utils.ANSI_CODE_START}171{utils.ANSI_CODE_END}",
                    api_manager,
                    config["playlist_sync"],
                    self.logger,
                    scheduler
                )
            )

    def init_jobs(self) -> None:
        """ Initialize all service jobs """
        for service in self.services:
            service.init_scheduler_jobs()

    def shutdown(self) -> None:
        """ Shutdown the services. """
        for service_base in self.services:
            service_base.shutdown()
