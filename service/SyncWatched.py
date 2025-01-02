
from dataclasses import dataclass
from datetime import datetime, timezone
from common.types import CronInfo, UserInfo
from common.utils import get_cron_from_string, get_datetime_for_history_plex_string, remove_year_from_name

class SyncWatched:
    def __init__(self, plex_api, tautulli_api, emby_api, jellystat_api, config, logger, scheduler):
        self.plex_api = plex_api
        self.tautulli_api = tautulli_api
        self.emby_api = emby_api
        self.jellystat_api = jellystat_api
        self.logger = logger
        self.scheduler = scheduler
        self.cron = None
        self.user_list = []
        
        try:
            self.cron = get_cron_from_string(config['cron_run_rate'], self.logger, self.__module__)
            
            for user in config['users']:
                if ('plex_name' in user and 'emby_name' in user):
                    plex_user_name = user['plex_name']
                    can_sync_plex_watch = ('can_sync_plex_watch' in user and user['can_sync_plex_watch'] == 'True')
                    emby_user_name = user['emby_name']
                    plex_user_id = self.tautulli_api.get_user_id(plex_user_name)
                    emby_user_id = self.emby_api.get_user_id(emby_user_name)
                    if plex_user_id != 0 and emby_user_id != self.emby_api.get_invalid_item_id():
                        self.user_list.append(UserInfo(plex_user_name, plex_user_id, can_sync_plex_watch, emby_user_name, emby_user_id))
                    else:
                        self.logger.error('{}: No Plex user found for {} ... Skipping User'.format(self.__module__ , plex_user_name))

        except Exception as e:
            self.logger.error("{}: Read config ERROR:{}".format(self.__module__ , e))
    
    def get_hours_since_play(self, useUtcTime, playDateTime):
        currentDateTime = datetime.now(timezone.utc) if useUtcTime == True else datetime.now()
        time_difference = currentDateTime - playDateTime
        return (time_difference.days * 24) + (time_difference.seconds / 3600)

    def set_emby_watched_item(self, user, itemId, fullTitle):
        try:
            self.emby_api.set_watched_item(user.emby_user_id, itemId)
            self.logger.info('{}: {} watched {} on Plex sync Emby watch status'.format(self.__module__, user.plex_user_name, fullTitle))
        except Exception as e:
            self.logger.error("{}: Set Emby watched ERROR:{}".format(self.__module__, e))
    
    def get_emby_path(self, plex_path):
        return plex_path.replace(self.plex_api.get_media_path(), self.emby_api.get_media_path(), 1)
        
    def get_plex_path(self, emby_path):
        return emby_path.replace(self.emby_api.get_media_path(), self.plex_api.get_media_path(), 1)
        
    def get_emby_tv_show_episode_id(self, tautulli_item):
        if 'grandparent_rating_key' in tautulli_item and 'rating_key' in tautulli_item and tautulli_item['grandparent_rating_key'] != '' and tautulli_item['rating_key'] != '':
            plex_item = self.plex_api.fetchItem(tautulli_item['rating_key'])
            if plex_item is not self.plex_api.get_invalid_type():
                series_item = self.plex_api.fetchItem(tautulli_item['grandparent_rating_key'])
                if series_item is not None and series_item.id is not None:
                    emby_file_location = self.get_emby_path(plex_item.locations[0])
                    return self.emby_api.get_series_episode_id(plex_item.grandparentTitle, series_item.locations[0], plex_item.seasonNumber, emby_file_location)
        
        return self.emby_api.get_invalid_item_id()
    
    def get_emby_movie_id(self, tautulli_item):
        plex_item = self.plex_api.fetchItem(tautulli_item['rating_key'])
        if plex_item is not self.plex_api.get_invalid_type():
            emby_file_location = self.get_emby_path(plex_item.locations[0])
            return self.emby_api.get_movie_item_id(plex_item.title, emby_file_location)
        else:
            return self.emby_api.get_invalid_item_id()
    
    def sync_emby_with_plex_watch_status(self, tautulli_item, user):
        emby_item_id = self.emby_api.get_invalid_item_id()
        if tautulli_item['media_type'] == self.tautulli_api.get_media_type_episode_name():
            emby_item_id = self.get_emby_tv_show_episode_id(tautulli_item)
        elif tautulli_item['media_type'] == self.tautulli_api.get_media_type_movie_name():
            emby_item_id = self.get_emby_movie_id(tautulli_item)
        
        # If the item id is valid and the user has not already watched the item
        if emby_item_id != self.emby_api.get_invalid_item_id() and self.emby_api.get_watched_status(user.emby_user_name, emby_item_id) == False:
            self.set_emby_watched_item(user, emby_item_id, tautulli_item['full_title'])
        
    def sync_plex_watch_status(self, user, dateTimeStringForHistory):
        try:
            watchHistoryData = self.tautulli_api.get_watch_history_for_user(user.plex_user_id, dateTimeStringForHistory)
            for historyItem in watchHistoryData:
                if (historyItem['watched_status'] == 1):
                    self.sync_emby_with_plex_watch_status(historyItem, user)
        except Exception as e:
            self.logger.error("{}: Get Plex History ERROR:{}".format(self.__module__, e))
    
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
                            self.logger.info('{}: {} watched {} on Emby sync Plex watch status'.format(self.__module__, user.emby_user_name, episode.grandparentTitle + ' - ' + episode.title))
                        break
        except Exception as e:
            self.logger.error("Error with plex movie watched: {}".format(e))

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
                            self.logger.info('{}: {} watched {} on Emby Sync Plex Watch Status'.format(self.__module__, user.emby_user_name, emby_item['Name']))
                    break
        except Exception as e:
            self.logger.error("{}: Error with plex movie watched: {}".format(self.__module__, e))
    
    def sync_plex_with_emby_watch_status(self, jellystat_item, user):
        if self.get_hours_since_play(True, datetime.fromisoformat(jellystat_item['ActivityDateInserted'])) < 24:
            if jellystat_item['SeriesName'] is not None:
                # Check that the episode has been marked as watched by emby
                if self.emby_api.get_watched_status(user.emby_user_name, jellystat_item['EpisodeId']) == True:
                    emby_series_item = self.emby_api.search_item(jellystat_item['NowPlayingItemId'])
                    emby_episode_item = self.emby_api.search_item(jellystat_item['EpisodeId'])
                    if emby_series_item is not None and emby_episode_item is not None:
                        self.set_plex_show_watched(emby_series_item['Path'], emby_episode_item, user)
            else:
                # Check that the item has been marked as watched by emby
                if self.emby_api.get_watched_status(user.emby_user_name, jellystat_item['NowPlayingItemId']) == True:
                    emby_item = self.emby_api.search_item(jellystat_item['NowPlayingItemId'])
                    if emby_item is not None and emby_item['Type'] == self.emby_api.get_media_type_movie_name():
                        self.set_plex_movie_watched(emby_item, user)
        
    def sync_emby_watch_status(self, user):
        try:
            history_items = self.jellystat_api.get_user_watch_history(user.emby_user_id)
            if len(history_items) > 0:
                self.plex_api.switch_plex_account(user.plex_user_name)
                
                # Search through the list and find items to sync
                for item in history_items:
                    self.sync_plex_with_emby_watch_status(item, user)
                
        except Exception as e:
            self.logger.error("{}: Error in emby watch status: {}".format(self.__module__, e))
    
    
    def sync_watch_status(self):
        dateTimeStringForHistory = get_datetime_for_history_plex_string(1)
        for user in self.user_list:
            self.sync_plex_watch_status(user, dateTimeStringForHistory)
            if user.can_sync_plex_watch == True:
                self.sync_emby_watch_status(user)
        
    def init_scheduler_jobs(self):
        self.logger.info('{}: Running start up sync'.format(self.__module__))
        self.sync_watch_status()
        
        if self.cron is not None:
            self.logger.info('{} Enabled. Running every hour:{} minute:{}'.format(self.__module__, self.cron.hours, self.cron.minutes))
            self.scheduler.add_job(self.sync_watch_status, trigger='cron', hour=self.cron.hours, minute=self.cron.minutes)
        else:
            self.logger.warning('{} Enabled but will not Run. Cron is not valid!'.format(self.__module__))
