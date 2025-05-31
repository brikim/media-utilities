""" Service Manager """

from apscheduler.schedulers.blocking import BlockingScheduler

from api.api_manager import ApiManager
from common.log_manager import LogManager

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
        log_manager: LogManager,
        scheduler: BlockingScheduler
    ):
        """ Initializes the Service Manager """

        # Available Services
        self.services: list[ServiceBase] = []
        self.api_manager = api_manager
        self.log_manager = log_manager
        self.scheduler = scheduler

        # Create the Media Server Sync Service
        if (
            "media_server_sync" in config
            and "enabled" in config["media_server_sync"]
            and config["media_server_sync"]["enabled"] == "True"
        ):
            self.services.append(
                MediaServerSync(
                    api_manager,
                    config["media_server_sync"],
                    self.log_manager,
                    scheduler
                )
            )

        if (
            "delete_watched" in config
            and "enabled" in config["delete_watched"]
            and config["delete_watched"]["enabled"] == "True"
        ):
            self.services.append(
                DeleteWatched(
                    api_manager,
                    config["delete_watched"],
                    self.log_manager,
                    scheduler
                )
            )

        if (
            "dvr_maintainer" in config
            and "enabled" in config["dvr_maintainer"]
            and config["dvr_maintainer"]["enabled"] == "True"
        ):
            self.services.append(
                DvrMaintainer(
                    api_manager,
                    config["dvr_maintainer"],
                    self.log_manager,
                    scheduler
                )
            )

        if (
            "folder_cleanup" in config
            and "enabled" in config["folder_cleanup"]
            and config["folder_cleanup"]["enabled"] == "True"
        ):
            self.services.append(
                FolderCleanup(
                    api_manager,
                    config["folder_cleanup"],
                    self.log_manager,
                    scheduler
                )
            )

        if (
            "playlist_sync" in config
            and "enabled" in config["playlist_sync"]
            and config["playlist_sync"]["enabled"] == "True"
        ):
            self.services.append(
                PlaylistSync(
                    api_manager,
                    config["playlist_sync"],
                    self.log_manager,
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
