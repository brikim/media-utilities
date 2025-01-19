
from datetime import datetime, timezone
from common.types import UserInfo
from common.utils import get_datetime_for_history_plex_string, remove_year_from_name, get_tag, get_formatted_emby, get_formatted_plex, get_log_ansi_code, get_tag_ansi_code
from service.ServiceBase import ServiceBase

class SyncWatched(ServiceBase):
    def __init__(self, ansi_code, plex_api, tautulli_api, emby_api, jellystat_api, config, logger, scheduler):
        super().__init__(ansi_code, self.__module__, config, logger, scheduler)
        
        self.plex_api = plex_api
        self.tautulli_api = tautulli_api
        self.emby_api = emby_api
        self.jellystat_api = jellystat_api
        self.user_list = []
        
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
                    
                    
                emby_user_name = ''
                if 'emby_name' in user:
                    emby_user_name = user['emby_name']
                    total_user_groups += 1
                
                if total_user_groups >= 2:
                    valid_user_ids = True
                    
                    plex_user_id = ''
                    if plex_user_name != '':
                        if self.tautulli_api.get_valid() == True and self.plex_api.get_valid() == True:
                            plex_user_id = self.tautulli_api.get_user_id(plex_user_name)
                            if plex_user_id == self.tautulli_api.get_invalid_user_id():
                                valid_user_ids = False
                                self.log_warning('No {} user found for {} ... Skipping User'.format(get_formatted_plex(), plex_user_name))
                        else:
                            valid_user_ids = False
                            self.log_warning('{} user defined but API not valid {} {} {}'.format(get_formatted_plex(), get_tag('user', plex_user_name), get_tag('plex_valid', self.plex_api.get_valid()), get_tag('tautulli_valid', self.tautulli_api.get_valid())))
                        
                    emby_user_id = ''
                    if emby_user_name != '':
                        if self.emby_api.get_valid() == True and self.jellystat_api.get_valid() == True:
                            emby_user_id = self.emby_api.get_user_id(emby_user_name)
                            if emby_user_id == self.emby_api.get_invalid_item_id():
                                valid_user_ids = False
                                self.log_warning('No {} user found for {} ... Skipping User'.format(get_formatted_emby(), emby_user_name))
                        else:
                            valid_user_ids = False
                            self.log_warning('{} user defined but API not valid {} {} {}'.format(get_formatted_emby(), get_tag('user', emby_user_name), get_tag('emby_valid', self.emby_api.get_valid()), get_tag('jellystat_valid', self.jellystat_api.get_valid())))
                    
                    if valid_user_ids == True:
                        self.user_list.append(UserInfo(plex_user_name, plex_user_id, can_sync_plex_watch, emby_user_name, emby_user_id))
                else:
                    self.log_warning('Only 1 user found in user field must have at least 2 to sync')

        except Exception as e:
            self.log_error('Read config ERROR:{}'.format(e))
    
    def get_hours_since_play(self, useUtcTime, playDateTime):
        currentDateTime = datetime.now(timezone.utc) if useUtcTime == True else datetime.now()
        time_difference = currentDateTime - playDateTime
        return (time_difference.days * 24) + (time_difference.seconds / 3600)

    def set_emby_watched_item(self, user, itemId, fullTitle):
        try:
            self.emby_api.set_watched_item(user.emby_user_id, itemId)
            self.log_info('{} watched {} on {} sync {} watch status'.format(user.plex_user_name, fullTitle, get_formatted_plex(), get_formatted_emby()))
        except Exception as e:
            self.log_error('Set {} watched {}'.format(get_formatted_emby(), get_tag_ansi_code(), get_log_ansi_code(), get_tag('error', e)))
    
    def get_emby_path_from_plex_path(self, plex_path):
        return plex_path.replace(self.plex_api.get_media_path(), self.emby_api.get_media_path(), 1)
        
    def get_plex_path(self, emby_path):
        return emby_path.replace(self.emby_api.get_media_path(), self.plex_api.get_media_path(), 1)
        
    def get_emby_item_id(self, tautulli_item):
        plex_item = self.plex_api.fetchItem(tautulli_item['rating_key'])
        if plex_item is not self.plex_api.get_invalid_type():
            if plex_item.locations[0] != None:
                return self.emby_api.get_item_id_from_path(self.get_emby_path_from_plex_path(plex_item.locations[0]))
        
        return self.emby_api.get_invalid_item_id()
    
    def sync_emby_with_plex_watch_status(self, tautulli_item, user):
        emby_item_id = self.get_emby_item_id(tautulli_item)
        
        # If the item id is valid and the user has not already watched the item
        if emby_item_id != self.emby_api.get_invalid_item_id():
            emby_watched_status = self.emby_api.get_watched_status(user.emby_user_id, emby_item_id)
            if emby_watched_status is not None and emby_watched_status == False:
                self.set_emby_watched_item(user, emby_item_id, tautulli_item['full_title'])
        
    def sync_plex_watch_status(self, user, dateTimeStringForHistory):
        try:
            watchHistoryData = self.tautulli_api.get_watch_history_for_user(user.plex_user_id, dateTimeStringForHistory)
            for historyItem in watchHistoryData:
                if historyItem['watched_status'] == 1 and user.emby_user_name != '':
                    self.sync_emby_with_plex_watch_status(historyItem, user)
        except Exception as e:
            self.log_error('Get {} history {}error={}{}'.format(get_formatted_plex(), get_tag_ansi_code(), get_log_ansi_code(), e))
    
    def set_plex_show_watched(self, emby_series_path, emby_episode_item, user):
        try:
            cleaned_show_name = remove_year_from_name(emby_episode_item['SeriesName']).lower()
            results = self.plex_api.search(cleaned_show_name, self.plex_api.get_media_type_show_name())
            for item in results:
                plex_show_path = self.get_plex_path(emby_series_path)
                if plex_show_path == item.locations[0]:
                    # Search for the show
                    show = self.plex_api.get_library_item(item.librarySectionTitle, item.title)
                    if show is not self.plex_api.get_invalid_type():
                        episode = show.episode(season=emby_episode_item['ParentIndexNumber'], episode=emby_episode_item['IndexNumber'])
                        plex_episode_location = self.get_plex_path(emby_episode_item['Path'])
                        if episode is not None and episode.isWatched == False and episode.locations[0] == plex_episode_location:
                            episode.markWatched()
                            self.log_info('{} watched {} on {} sync {} watch status'.format(user.emby_user_name, episode.grandparentTitle + ' - ' + episode.title, get_formatted_emby(), get_formatted_plex()))
                        break
        except Exception as e:
            self.log_error('Error with {} movie watched {}'.format(get_formatted_plex(), get_tag_ansi_code(), get_log_ansi_code(), get_tag('error', e)))

    def set_plex_movie_watched(self, emby_item, user):
        try:
            lower_title = emby_item['Name'].lower()
            result_items = self.plex_api.search(lower_title, self.plex_api.get_media_type_movie_name())
            for item in result_items:
                plex_movie_location = self.get_plex_path(emby_item['Path'])
                if plex_movie_location == item.locations[0]:
                    if item.isWatched == False:
                        media_Item = self.plex_api.get_library_item(item.librarySectionTitle, item.title)
                        if media_Item is not self.plex_api.get_invalid_type():
                            media_Item.markWatched()
                            self.log_info('{} watched {} on {} sync {} watch status'.format(user.emby_user_name, emby_item['Name'], get_formatted_emby(), get_formatted_plex()))
                    break
        except Exception as e:
            self.log_error('Error with {} movie watched {}'.format(get_formatted_plex(), get_tag_ansi_code(), get_log_ansi_code(), get_tag('error', e)))
    
    def sync_plex_with_emby_watch_status(self, jellystat_item, user):
        if self.get_hours_since_play(True, datetime.fromisoformat(jellystat_item['ActivityDateInserted'])) < 24:
            if jellystat_item['SeriesName'] is not None:
                # Check that the episode has been marked as watched by emby
                if self.emby_api.get_watched_status(user.emby_user_id, jellystat_item['EpisodeId']) == True:
                    emby_series_item = self.emby_api.search_item(jellystat_item['NowPlayingItemId'])
                    emby_episode_item = self.emby_api.search_item(jellystat_item['EpisodeId'])
                    if emby_series_item is not None and emby_episode_item is not None:
                        self.set_plex_show_watched(emby_series_item['Path'], emby_episode_item, user)
            else:
                # Check that the item has been marked as watched by emby
                if self.emby_api.get_watched_status(user.emby_user_id, jellystat_item['NowPlayingItemId']) == True:
                    emby_item = self.emby_api.search_item(jellystat_item['NowPlayingItemId'])
                    if emby_item is not None and emby_item['Type'] == self.emby_api.get_media_type_movie_name():
                        self.set_plex_movie_watched(emby_item, user)
        
    def sync_emby_watch_status(self, user):
        try:
            history_items = self.jellystat_api.get_user_watch_history(user.emby_user_id)
            if len(history_items) > 0:
                if user.plex_user_name != '':
                    self.plex_api.switch_plex_account(user.plex_user_name)
                
                    # Search through the list and find items to sync
                    for item in history_items:
                        self.sync_plex_with_emby_watch_status(item, user)
                
        except Exception as e:
            self.log_error('{} watch status {}'.format(get_formatted_emby(), get_tag('error', e)))
    
    
    def sync_watch_status(self):
        dateTimeStringForHistory = get_datetime_for_history_plex_string(1)
        for user in self.user_list:
            if user.plex_user_name != '':
                self.sync_plex_watch_status(user, dateTimeStringForHistory)
            if user.can_sync_plex_watch == True:
                if user.emby_user_name != '':
                    self.sync_emby_watch_status(user)
        
    def init_scheduler_jobs(self):
        if len(self.user_list) > 0:
            self.log_info('Running start up sync')
            self.sync_watch_status()
            
            if self.cron is not None:
                self.log_service_enabled()
                self.scheduler.add_job(self.sync_watch_status, trigger='cron', hour=self.cron.hours, minute=self.cron.minutes)
            else:
                self.log_warning('Enabled but will not Run. Cron is not valid!')
        else:
            self.log_warning('Enabled but no valid users to sync!')
