
from datetime import datetime, timezone
from dataclasses import dataclass
from logging import Logger
from typing import Any, List
from apscheduler.schedulers.blocking import BlockingScheduler

from common.types import UserInfo
from common import utils

from service.ServiceBase import ServiceBase

from api.plex import PlexAPI
from api.tautulli import TautulliAPI
from api.emby import EmbyAPI
from api.jellystat import JellystatAPI

@dataclass
class ConfigUserInfo:
    plex_user_name: str
    can_sync_plex_watch: bool
    emby_user_name: str

@dataclass
class ConnectionInfo:
    plex_valid: bool
    tautulli_valid: bool
    emby_valid: bool
    jellystat_valid: bool

class SyncWatched(ServiceBase):
    def __init__(self, ansi_code: str, plex_api: PlexAPI, tautulli_api: TautulliAPI, emby_api: EmbyAPI, jellystat_api: JellystatAPI, config: Any, logger: Logger, scheduler: BlockingScheduler):
        super().__init__(ansi_code, self.__module__, config, logger, scheduler)
        
        self.plex_api = plex_api
        self.tautulli_api = tautulli_api
        self.emby_api = emby_api
        self.jellystat_api = jellystat_api
        
        self.config_plex_used = False
        self.config_emby_used = False
        self.config_user_list: list[ConfigUserInfo] = []
        
        try:
            for user in config['users']:
                total_user_groups = 0
                
                plex_user_name = ''
                can_sync_plex_watch = False
                if "plex_name" in user:
                    plex_user_name = user['plex_name']
                    if 'can_sync_plex_watch' in user:
                        can_sync_plex_watch = user['can_sync_plex_watch'] == 'True'
                    total_user_groups += 1
                    self.config_plex_used = True
                    
                    
                emby_user_name = ''
                if 'emby_name' in user:
                    emby_user_name = user['emby_name']
                    total_user_groups += 1
                    self.config_emby_used = True
                
                if total_user_groups >= 2:
                    self.config_user_list.append(ConfigUserInfo(plex_user_name, can_sync_plex_watch, emby_user_name))
                else:
                    self.log_warning('Only 1 user found in user field must have at least 2 to sync')

        except Exception as e:
            self.log_error('Read config {}'.format(utils.get_tag('error', e)))
    
    def __check_connections_valid(self) -> ConnectionInfo:
        plex_api_valid = False
        tautulli_api_valid = False
        if self.config_plex_used is True:
            plex_api_valid = self.plex_api.get_valid()
            tautulli_api_valid = self.tautulli_api.get_valid()

        emby_api_valid = False
        jellystat_api_valid = False      
        if self.config_emby_used is True:
            emby_api_valid = self.emby_api.get_valid()
            jellystat_api_valid = self.jellystat_api.get_valid()
        
        return ConnectionInfo(plex_api_valid, tautulli_api_valid, emby_api_valid, jellystat_api_valid)
        
    def __get_user_data(self) -> List[UserInfo]:
        connection_info = self.__check_connections_valid()
        
        connections_valid = True
        if self.config_plex_used is True and (connection_info.plex_valid is False or connection_info.tautulli_valid is False):
            if connection_info.plex_valid is False:
                self.log_warning(self.plex_api.get_connection_error_log())
            if connection_info.tautulli_valid is False:
                self.log_warning(self.tautulli_api.get_connection_error_log())
            connections_valid = False
        
        if self.config_emby_used is True and (connection_info.emby_valid is False or connection_info.jellystat_valid is False):
            if connection_info.emby_valid is False:
                self.log_warning(self.emby_api.get_connection_error_log())
            if connection_info.jellystat_valid is False:
                self.log_warning(self.jellystat_api.get_connection_error_log())
            connections_valid = False
        
        user_list: list[UserInfo] = []
        if connections_valid is True:
            for config_user in self.config_user_list:
                valid_user_ids: bool = True
                
                plex_user_id: str = ''
                plex_friendly_name: str = ''
                if config_user.plex_user_name != '':
                    plex_user_info = self.tautulli_api.get_user_info(config_user.plex_user_name)
                    if plex_user_info != self.tautulli_api.get_invalid_item():
                        plex_user_id = plex_user_info['user_id']
                        if 'friendly_name' in plex_user_info and plex_user_info['friendly_name'] is not None and plex_user_info['friendly_name'] != '':
                            plex_friendly_name = plex_user_info['friendly_name']
                        else:
                            plex_friendly_name = config_user.plex_user_name
                    else:
                        valid_user_ids = False
                        self.log_warning('No {} user found for {} ... Skipping User'.format(utils.get_formatted_plex(), config_user.plex_user_name))
                
                emby_user_id: str = ''
                if config_user.emby_user_name != '':
                    emby_user_id = self.emby_api.get_user_id(config_user.emby_user_name)
                    if emby_user_id == self.emby_api.get_invalid_item_id():
                        valid_user_ids = False
                        self.log_warning('No {} user found for {} ... Skipping User'.format(utils.get_formatted_emby(), config_user.emby_user_name))
                
                if valid_user_ids is True:
                    user_list.append(UserInfo(config_user.plex_user_name, plex_friendly_name, plex_user_id, config_user.can_sync_plex_watch, config_user.emby_user_name, emby_user_id))
        else:
            self.log_info('Will try connections again on next run')
            
        return user_list
        
    def __get_hours_since_play(self, use_utc_time: bool, play_date_time: datetime) -> int:
        current_date_time = datetime.now(timezone.utc) if use_utc_time is True else datetime.now()
        time_difference = current_date_time - play_date_time
        return (time_difference.days * 24) + (time_difference.seconds / 3600)

    def __set_emby_watched_item(self, user: UserInfo, item_id: str, full_title: str):
        try:
            self.emby_api.set_watched_item(user.emby_user_id, item_id)
            self.log_info('{} watched {} on {} sync {} watch status'.format(user.plex_friendly_name, full_title, utils.get_formatted_plex(), utils.get_formatted_emby()))
        except Exception as e:
            self.log_error('Set {} watched {}'.format(utils.get_formatted_emby(), utils.get_tag('error', e)))
    
    def __get_emby_path_from_plex_path(self, plex_path: str) -> str:
        return plex_path.replace(self.plex_api.get_media_path(), self.emby_api.get_media_path(), 1)
        
    def __get_plex_path(self, emby_path: str) -> str:
        return emby_path.replace(self.emby_api.get_media_path(), self.plex_api.get_media_path(), 1)
        
    def __get_emby_item_id(self, tautulli_item: Any) -> str:
        plex_item = self.plex_api.fetchItem(tautulli_item['rating_key'])
        if plex_item is not self.plex_api.get_invalid_type():
            if plex_item.locations[0] != None:
                return self.emby_api.get_item_id_from_path(self.__get_emby_path_from_plex_path(plex_item.locations[0]))
        
        return self.emby_api.get_invalid_item_id()
    
    def __sync_emby_with_plex_watch_status(self, tautulli_item: Any, user: UserInfo):
        emby_item_id = self.__get_emby_item_id(tautulli_item)
        
        # If the item id is valid and the user has not already watched the item
        if emby_item_id != self.emby_api.get_invalid_item_id():
            emby_watched_status = self.emby_api.get_watched_status(user.emby_user_id, emby_item_id)
            if emby_watched_status is not None and emby_watched_status is False:
                self.__set_emby_watched_item(user, emby_item_id, tautulli_item['full_title'])
        
    def __sync_plex_watch_status(self, user: UserInfo, date_time_for_history: str):
        try:
            watch_history_data = self.tautulli_api.get_watch_history_for_user(user.plex_user_id, date_time_for_history)
            for history_item in watch_history_data:
                if history_item['watched_status'] == 1 and user.emby_user_name != '':
                    self.__sync_emby_with_plex_watch_status(history_item, user)
        except Exception as e:
            self.log_error('Get {} history {}'.format(utils.get_formatted_plex(), utils.get_tag('error', e)))
    
    def __set_plex_show_watched(self, emby_series_path: str, emby_episode_item: Any, user: UserInfo):
        try:
            cleaned_show_name = utils.remove_year_from_name(emby_episode_item['SeriesName']).lower()
            results = self.plex_api.search(cleaned_show_name, self.plex_api.get_media_type_show_name())
            for item in results:
                plex_show_path = self.__get_plex_path(emby_series_path)
                if plex_show_path == item.locations[0]:
                    # Search for the show
                    show = self.plex_api.get_library_item(item.librarySectionTitle, item.title)
                    if show is not self.plex_api.get_invalid_type():
                        episode = show.episode(season=emby_episode_item['ParentIndexNumber'], episode=emby_episode_item['IndexNumber'])
                        plex_episode_location = self.__get_plex_path(emby_episode_item['Path'])
                        if episode is not None and episode.isWatched is False and episode.locations[0] == plex_episode_location:
                            episode.markWatched()
                            self.log_info('{} watched {} on {} sync {} watch status'.format(user.emby_user_name, episode.grandparentTitle + ' - ' + episode.title, utils.get_formatted_emby(), utils.get_formatted_plex()))
                        break
        except Exception as e:
            self.log_error('Error with {} movie watched {}'.format(utils.get_formatted_plex(), utils.get_tag('error', e)))

    def __set_plex_movie_watched(self, emby_item: Any, user: UserInfo):
        try:
            lower_title = emby_item['Name'].lower()
            result_items = self.plex_api.search(lower_title, self.plex_api.get_media_type_movie_name())
            for item in result_items:
                plex_movie_location = self.__get_plex_path(emby_item['Path'])
                if plex_movie_location == item.locations[0]:
                    if item.isWatched is False:
                        media_item = self.plex_api.get_library_item(item.librarySectionTitle, item.title)
                        if media_item is not self.plex_api.get_invalid_type():
                            media_item.markWatched()
                            self.log_info('{} watched {} on {} sync {} watch status'.format(user.emby_user_name, emby_item['Name'], utils.get_formatted_emby(), utils.get_formatted_plex()))
                    break
        except Exception as e:
            self.log_error('Error with {} movie watched {}'.format(utils.get_formatted_plex(), utils.get_tag('error', e)))
    
    def __sync_plex_with_emby_watch_status(self, jellystat_item: Any, user: UserInfo):
        if self.__get_hours_since_play(True, datetime.fromisoformat(jellystat_item['ActivityDateInserted'])) < 24:
            if jellystat_item['SeriesName'] is not None and self.emby_api.get_watched_status(user.emby_user_id, jellystat_item['EpisodeId']) is True:
                emby_series_item = self.emby_api.search_item(jellystat_item['NowPlayingItemId'])
                emby_episode_item = self.emby_api.search_item(jellystat_item['EpisodeId'])
                if emby_series_item is not None and emby_episode_item is not None:
                    self.__set_plex_show_watched(emby_series_item['Path'], emby_episode_item, user)
            else:
                # Check that the item has been marked as watched by emby
                if self.emby_api.get_watched_status(user.emby_user_id, jellystat_item['NowPlayingItemId']) is True:
                    emby_item = self.emby_api.search_item(jellystat_item['NowPlayingItemId'])
                    if emby_item is not None and emby_item['Type'] == self.emby_api.get_media_type_movie_name():
                        self.__set_plex_movie_watched(emby_item, user)
        
    def __sync_emby_watch_status(self, user: UserInfo):
        try:
            history_items = self.jellystat_api.get_user_watch_history(user.emby_user_id)
            if history_items != self.jellystat_api.get_invalid_type() and len(history_items) > 0 and user.plex_user_name != '':
                self.plex_api.switch_plex_account(user.plex_user_name)
                # Search through the list and find items to sync
                for item in history_items:
                    self.__sync_plex_with_emby_watch_status(item, user)
                
        except Exception as e:
            self.log_error('{} watch status {}'.format(utils.get_formatted_emby(), utils.get_tag('error', e)))
    
    
    def __sync_watch_status(self):
        date_time_for_history = utils.get_datetime_for_history_plex_string(1)
        user_list = self.__get_user_data()
        for user in user_list:
            if user.plex_user_name != '':
                self.__sync_plex_watch_status(user, date_time_for_history)
            if user.can_sync_plex_watch is True:
                if user.emby_user_name != '':
                    self.__sync_emby_watch_status(user)
        
    def init_scheduler_jobs(self):
        if len(self.config_user_list) > 0:
            if self.cron is not None:
                self.log_service_enabled()
                self.scheduler.add_job(self.__sync_watch_status, trigger='cron', hour=self.cron.hours, minute=self.cron.minutes)
            else:
                self.log_warning('Enabled but will not Run. Cron is not valid!')
        else:
            self.log_warning('Enabled but no valid users to sync!')
