from logging import Logger
from apscheduler.schedulers.blocking import BlockingScheduler
from dataclasses import dataclass, field
from common import utils

from service.ServiceBase import ServiceBase

from api.plex import PlexAPI, PlexCollection
from api.emby import EmbyAPI, EmbyPlaylist

@dataclass
class PlexCollectionConfig:
    library_name: str
    collection_name: str
    target_servers: list[str] = field(default_factory=list)

class PlaylistSync(ServiceBase):
    def __init__(self, ansi_code: str, plex_api: PlexAPI, emby_api: EmbyAPI, config, logger: Logger, scheduler: BlockingScheduler):
        super().__init__(ansi_code, self.__module__, config, logger, scheduler)
        
        self.plex_api = plex_api
        self.emby_api = emby_api
        self.plex_collection_configs: list[PlexCollectionConfig] = []
        
        try:
            for plex_collection in config['plex_collection_sync']:
                if 'library' in plex_collection and 'collection_name' in plex_collection and 'target_servers' in plex_collection:
                    library_name = plex_collection['library']
                    collection_name = plex_collection['collection_name']
                    target_servers: list[str] = []
                    
                    target_server_names = plex_collection['target_servers'].split(',')
                    for target_server_name in target_server_names:
                        supported_target_server_name = self.__server_supported(target_server_name)
                        if supported_target_server_name != '':
                            target_servers.append(supported_target_server_name)
                    
                    if library_name != '' and collection_name != '' and len(target_servers) > 0:
                        if plex_api.get_valid() is True and plex_api.get_collection_valid(library_name, collection_name) is False:
                            self.log_warning('{} {} {} not found on server'.format(utils.get_formatted_plex(), utils.get_tag('library', library_name), utils.get_tag('collection', collection_name)))
                        
                        self.plex_collection_configs.append(PlexCollectionConfig(library_name, collection_name, target_servers))
            
        except Exception as e:
            self.log_error('Read config {}'.format(utils.get_tag('error', e)))

    def __server_supported(self, server_type: str) -> str:
        lower_name = server_type.lower()
        if (lower_name == 'plex' or lower_name == 'emby'):
            return lower_name
        return ''
    
    def __sync_emby_playlist(self, emby_item_ids: list[str], emby_playlist: EmbyPlaylist):
        # Check if any items were added to the playlist
        added_items: list[str] = []
        for emby_item_id in emby_item_ids:
            item_id_found = False
            for item in emby_playlist.items:
                if emby_item_id == item.id:
                    item_id_found = True
                    break
            if item_id_found is False:
                added_items.append(emby_item_id)
        
        # Check if any items were deleted out of the playlist
        deleted_items: list[str] = []
        for item in emby_playlist.items:
            if item.id not in emby_item_ids:
                deleted_items.append(item.id)
                
        # Check if the order of the playlist items changed
        playlist_changed = False
        if len(emby_item_ids) == len(emby_playlist.items):
            playlist_index = 0
            for item_id in emby_item_ids:
                if item_id != emby_playlist.items[playlist_index].id:
                    playlist_changed = True
                    break
                playlist_index += 1
        else:
            playlist_changed = True
            
        if playlist_changed is True or len(added_items) > 0 or len(deleted_items) > 0:
            self.log_info('Syncing {} {} to {}'.format(utils.get_formatted_plex(), utils.get_tag('collection', emby_playlist.name), utils.get_formatted_emby()))
        
            if len(added_items) > 0:
                self.emby_api.add_playlist_items(emby_playlist.id, added_items)
            
            if len(deleted_items) > 0:
                self.emby_api.remove_playlist_items(emby_playlist.id, deleted_items)
            
            current_index = 1
            for item_id in emby_item_ids:
                self.emby_api.set_move_playlist_item_to_index(emby_playlist.id, item_id, current_index)
                current_index += 1
    
    def __sync_emby_playlist_with_plex_collection(self, plex_collection: PlexCollection):
        emby_item_ids: list[str] = []
        for plex_item in plex_collection.items:
            emby_item_id = self.emby_api.get_item_id_from_path(plex_item.path)
            if emby_item_id != self.emby_api.get_invalid_item_id():
                emby_item_ids.append(emby_item_id)
            else:
                self.log_warning('{} sync {} {} item not found {}'.format(utils.get_emby_ansi_code(), utils.get_plex_ansi_code(), utils.get_tag('collection', plex_collection.name), utils.get_tag('item', plex_item.title)))
        
        emby_playlist_id = self.emby_api.get_playlist_id(plex_collection.name)
        if emby_playlist_id == self.emby_api.get_invalid_item_id():
            self.emby_api.create_playlist(plex_collection.name, emby_item_ids)
            self.log_info('Syncing {} {} to {}'.format(utils.get_formatted_plex(), utils.get_tag('collection', plex_collection.name), utils.get_formatted_emby()))
        else:
            emby_playlist:EmbyPlaylist = self.emby_api.get_playlist_items(emby_playlist_id)
            if emby_playlist is not None:
                self.__sync_emby_playlist(emby_item_ids, emby_playlist)
    
    def __sync_plex_collection(self, collection_config: PlexCollectionConfig):
        collection: PlexCollection = self.plex_api.get_collection(collection_config.library_name, collection_config.collection_name)
        if collection != self.plex_api.get_invalid_type():
            for target_server in collection_config.target_servers:
                if target_server == 'emby' and self.emby_api.get_valid() is True:
                    self.__sync_emby_playlist_with_plex_collection(collection)
    
    def __sync_playlists(self):
        if len(self.plex_collection_configs) > 0:
            plex_valid = self.plex_api.get_valid()
            emby_valid = self.emby_api.get_valid()
            if plex_valid is True and emby_valid is True:
                for plex_collection_config in self.plex_collection_configs:
                    self.__sync_plex_collection(plex_collection_config)
            else:
                if plex_valid is False:
                    self.log_warning(self.plex_api.get_connection_error_log())
                if emby_valid is False:
                    self.log_warning(self.emby_api.get_connection_error_log())
    
    def init_scheduler_jobs(self):
        if self.cron is not None:
            self.log_service_enabled()
            self.scheduler.add_job(self.__sync_playlists, trigger='cron', hour=self.cron.hours, minute=self.cron.minutes)
        else:
            self.log_warning('Enabled but will not Run. Cron is not valid!')
