""" 
Playlist Sync Service
    Synchronize plex collections to emby playlists
"""

from dataclasses import dataclass, field
import time

from apscheduler.schedulers.blocking import BlockingScheduler

from api.api_manager import ApiManager
from api.plex import PlexAPI, PlexCollection
from api.emby import EmbyAPI, EmbyPlaylist
from common import utils
from common.log_manager import LogManager
from service.service_base import ServiceBase


@dataclass
class PlexCollectionConfig:
    """ Class representing a Plex collection configuration """
    server_name: str
    library_name: str
    collection_name: str
    target_emby_servers: list[str] = field(default_factory=list)


@dataclass
class AddDeleteInfo:
    """ Class representing the number of items added and deleted """
    added_items: int
    deleted_items: int


class PlaylistSync(ServiceBase):
    """ Playlist Sync service """

    def __init__(
        self,
        api_manager: ApiManager,
        config: dict,
        log_manager: LogManager,
        scheduler: BlockingScheduler
    ):
        super().__init__(
            utils.get_service_playlist_sync_ansi_code(),
            "Playlist Sync",
            config,
            api_manager,
            log_manager,
            scheduler
        )

        self.plex_collection_configs: list[PlexCollectionConfig] = []

        self.time_for_emby_to_update_seconds: float = 5.0
        if "time_for_emby_to_update_seconds" in config:
            self.time_for_emby_to_update_seconds = float(
                config["time_for_emby_to_update_seconds"]
            )

        self.time_between_syncs_seconds: float = 1.0
        if "time_between_syncs_seconds" in config:
            self.time_between_syncs_seconds = float(
                config["time_between_syncs_seconds"]
            )

        try:
            for plex_collection in config["plex_collection_sync"]:
                if (
                    "server" in plex_collection
                    and "library" in plex_collection
                    and "collection_name" in plex_collection
                    and "target_emby_servers" in plex_collection
                ):
                    server_name = plex_collection["server"]
                    plex_api = self.api_manager.get_plex_api(server_name)
                    if plex_api is not None:
                        library_name = plex_collection["library"]
                        collection_name = plex_collection["collection_name"]
                        target_emby_servers: list[str] = []

                        for emby_server in plex_collection["target_emby_servers"]:
                            if "server" in emby_server and self.api_manager.get_emby_api(emby_server["server"]) is not None:
                                target_emby_servers.append(
                                    emby_server["server"])

                        if (
                            library_name != ""
                            and collection_name != ""
                            and len(target_emby_servers) > 0
                        ):
                            if (
                                plex_api.get_valid()
                                and not plex_api.get_collection_valid(library_name, collection_name)
                            ):
                                library_tag = utils.get_tag(
                                    "library", library_name)
                                collection_tag = utils.get_tag(
                                    "collection", collection_name)
                                self.log_warning(
                                    f"{utils.get_formatted_plex()}({server_name}) {library_tag} {collection_tag} not found on server"
                                )

                            self.plex_collection_configs.append(
                                PlexCollectionConfig(
                                    server_name, library_name, collection_name, target_emby_servers
                                )
                            )
                    else:
                        self.log_warning(
                            f"No {utils.get_formatted_plex()} server found for {server_name} ... Skipping"
                        )

        except Exception as e:
            self.log_error(f"Read config {utils.get_tag("error", e)}")

    def __emby_add_remove_items_to_playlist(
        self,
        emby_api: EmbyAPI,
        emby_item_ids: list[str],
        emby_playlist: EmbyPlaylist
    ) -> AddDeleteInfo:
        # Check if any items were added to the playlist
        added_items: list[str] = []
        for emby_item_id in emby_item_ids:
            item_id_found = False
            for item in emby_playlist.items:
                if emby_item_id == item.id:
                    item_id_found = True
                    break
            if not item_id_found:
                added_items.append(emby_item_id)

        # Check if any items were deleted out of the playlist
        deleted_playlist_items: list[str] = []
        for item in emby_playlist.items:
            if item.id not in emby_item_ids:
                deleted_playlist_items.append(item.playlist_item_id)

        if len(added_items) > 0 or len(deleted_playlist_items) > 0:
            if len(added_items) > 0:
                if not emby_api.add_playlist_items(emby_playlist.id, added_items):
                    playlist_tag = utils.get_tag(
                        "playlist", emby_playlist.name)
                    items_tag = utils.get_tag("items", added_items)
                    self.log_warning(
                        f"{utils.get_formatted_emby()}({emby_api.get_server_name()}) failed {playlist_tag} adding {items_tag}"
                    )

            if len(deleted_playlist_items) > 0:
                if not emby_api.remove_playlist_items(
                    emby_playlist.id,
                    deleted_playlist_items
                ):
                    playlist_tag = utils.get_tag(
                        "playlist", emby_playlist.name)
                    items_tag = utils.get_tag("items", deleted_playlist_items)
                    self.log_warning(
                        f"{utils.get_formatted_emby()}({emby_api.get_server_name()}) failed {playlist_tag} removing {items_tag}"
                    )

            # Give Emby time to update the playlist
            time.sleep(self.time_for_emby_to_update_seconds)

            return AddDeleteInfo(len(added_items), len(deleted_playlist_items))
        return AddDeleteInfo(0, 0)

    def __emby_update_playlist(
        self,
        emby_api: EmbyAPI,
        plex_api: PlexAPI,
        emby_item_ids: list[str],
        original_emby_playlist: EmbyPlaylist
    ):
        add_delete_info = self.__emby_add_remove_items_to_playlist(
            emby_api, emby_item_ids, original_emby_playlist
        )

        # Get the latest playlist
        edited_emby_playlist: EmbyPlaylist = emby_api.get_playlist_items(
            original_emby_playlist.id)

        if edited_emby_playlist is not None:
            # Should be the correct length before this call but make sure
            if len(edited_emby_playlist.items) == len(emby_item_ids):
                playlist_changed = False
                playlist_index = 0
                for item_id in emby_item_ids:
                    if item_id != edited_emby_playlist.items[playlist_index].id:
                        playlist_changed = True
                        break
                    playlist_index += 1

                if playlist_changed:
                    # The order changed now iterate through the correct item order and find the playlist id to use in moving items
                    current_index = 0
                    for correct_item_id in emby_item_ids:
                        for current_playlist_item in edited_emby_playlist.items:
                            if correct_item_id == current_playlist_item.id:
                                if emby_api.set_move_playlist_item_to_index(
                                    edited_emby_playlist.id,
                                    current_playlist_item.playlist_item_id,
                                    current_index
                                ):
                                    time.sleep(self.time_between_syncs_seconds)
                                else:
                                    playlist_tag = utils.get_tag(
                                        "playlist", original_emby_playlist.name)
                                    item_tag = utils.get_tag(
                                        "item", current_playlist_item.playlist_item_id)
                                    index_tag = utils.get_tag(
                                        "index", current_index)
                                    self.log_warning(
                                        f"{utils.get_formatted_emby()}({emby_api.get_server_name()}) failed {playlist_tag} moving {item_tag} to {index_tag}"
                                    )
                                current_index += 1
                                break

                    if playlist_changed or add_delete_info.added_items > 0 or add_delete_info.deleted_items > 0:
                        collection_tag = utils.get_tag(
                            "collection",
                            utils.get_standout_text(
                                original_emby_playlist.name
                            )
                        )
                        added_tag = utils.get_tag(
                            "added", add_delete_info.added_items
                        )
                        deleted_tag = utils.get_tag(
                            "deleted", add_delete_info.deleted_items
                        )
                        reordered_tag = utils.get_tag(
                            "reordered", playlist_changed
                        )
                        self.log_info(
                            f"Syncing {utils.get_formatted_plex()}({plex_api.get_server_name()}) {collection_tag} to {utils.get_formatted_emby()}({emby_api.get_server_name()}) {added_tag} {deleted_tag} {reordered_tag}"
                        )
            else:
                collection_tag = utils.get_tag(
                    "collection", original_emby_playlist.name)
                length_tag = utils.get_tag("length", len(emby_item_ids))
                reported_length_tag = utils.get_tag(
                    "reported_length", len(edited_emby_playlist.items))
                self.log_warning(
                    f"{utils.get_formatted_emby()}({emby_api.get_server_name()}) sync {utils.get_formatted_plex()}({plex_api.get_server_name()}) {collection_tag} playlist update failed. Playlist length should be {length_tag} {reported_length_tag}!"
                )

    def __sync_emby_playlist_with_plex_collection(
        self,
        emby_api: EmbyAPI,
        plex_api: PlexAPI,
        plex_collection: PlexCollection
    ):
        emby_item_ids: list[str] = []
        for plex_item in plex_collection.items:
            emby_item_id = emby_api.get_item_id_from_path(plex_item.path)
            if emby_item_id != emby_api.get_invalid_item_id():
                emby_item_ids.append(emby_item_id)
            else:
                collection_tag = utils.get_tag(
                    "collection", plex_collection.name)
                item_tag = utils.get_tag("item", plex_item.title)
                self.log_warning(
                    f"{utils.get_formatted_emby()}({emby_api.get_server_name()}) sync {utils.get_formatted_plex()}({plex_api.get_server_name()}) {collection_tag} item not found {item_tag}"
                )

        emby_playlist_id = emby_api.get_playlist_id(plex_collection.name)
        if emby_playlist_id == emby_api.get_invalid_item_id():
            emby_api.create_playlist(plex_collection.name, emby_item_ids)

            collection_tag = utils.get_tag("collection", plex_collection.name)
            self.log_info(
                f"Creating {utils.get_formatted_plex()}({plex_api.get_server_name()}) {collection_tag} on {utils.get_formatted_emby()}({emby_api.get_server_name()})"
            )
        else:
            emby_playlist: EmbyPlaylist = emby_api.get_playlist_items(
                emby_playlist_id)
            if emby_playlist is not None:
                self.__emby_update_playlist(
                    emby_api, plex_api, emby_item_ids, emby_playlist)

                # Give emby time to process
                time.sleep(self.time_between_syncs_seconds)

    def __sync_plex_collection(
        self,
        plex_api: PlexAPI,
        emby_api: EmbyAPI,
        plex_library_name: str,
        plex_collection_name: str
    ):
        collection: PlexCollection = plex_api.get_collection(
            plex_library_name,
            plex_collection_name
        )

        if collection != plex_api.get_invalid_type():
            self.__sync_emby_playlist_with_plex_collection(
                emby_api, plex_api, collection)

    def __sync_playlists(self):
        for plex_collection_config in self.plex_collection_configs:
            plex_api = self.api_manager.get_plex_api(
                plex_collection_config.server_name)
            if plex_api.get_valid():
                for emby_server_name in plex_collection_config.target_emby_servers:
                    emby_api = self.api_manager.get_emby_api(emby_server_name)
                    if emby_api.get_valid():
                        self.__sync_plex_collection(
                            plex_api,
                            emby_api,
                            plex_collection_config.library_name,
                            plex_collection_config.collection_name
                        )
                    else:
                        self.log_warning(emby_api.get_connection_error_log())
            else:
                self.log_warning(plex_api.get_connection_error_log())

    def init_scheduler_jobs(self):
        if self.cron is not None:
            self.log_service_enabled()
            self.scheduler.add_job(
                self.__sync_playlists,
                trigger="cron",
                hour=self.cron.hours,
                minute=self.cron.minutes
            )
        else:
            self.log_warning("Enabled but will not Run. Cron is not valid!")
