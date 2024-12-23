
from dataclasses import dataclass
from datetime import datetime, timezone
from common.user_stats import UserInfo
from common.utils import get_datetime_for_history_plex_string, remove_year_from_name
class SyncWatched:
    def __init__(self, plex_api, tautulli_api, emby_api, jellystat_api, config, logger, scheduler):
        self.plex_api = plex_api
        self.tautulli_api = tautulli_api
        self.emby_api = emby_api
        self.jellystat_api = jellystat_api
        self.logger = logger
        self.scheduler = scheduler
        self.user_list = []
        self.cronHours = ''
        self.cronMinutes = ''
        
        try:
            cronParams = config['cron_run_rate'].split()
            if len(cronParams) >= 2 and len(cronParams) <= 5:
                self.cronMinutes = cronParams[0]
                self.cronHours = cronParams[1]
            else:
                self.logger.error('{}: Invalid Cron Expression {}'.format(self.__module__, config['cron_run_rate']))
            
            for user in config['users']:
                if ('plexName' in user and 'embyName' in user):
                    plexUserName = user['plexName']
                    embyUserName = user['embyName']
                    plexUserId = self.tautulli_api.get_user_id(plexUserName)
                    embyUserId = self.emby_api.get_user_id(embyUserName)
                    if plexUserId != 0 and embyUserId != self.emby_api.get_invalid_item_id():
                        self.user_list.append(UserInfo(plexUserName, plexUserId, embyUserName, embyUserId))
                    else:
                        self.logger.error('{}: No Plex user found for {} ... Skipping User'.format(self.__module__ , plexUserName))

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
    
    def get_emby_tv_show_episode_id(self, plex_history_item):
        plex_item = self.plex_api.fetchItem(plex_history_item['rating_key'])
        if plex_item is not self.plex_api.get_invalid_type():
            series_item = self.plex_api.fetchItem(plex_history_item['grandparent_rating_key'])
            if series_item is not None:
                return self.emby_api.get_series_episode_id(plex_item.grandparentTitle, series_item.locations[0], plex_item.seasonNumber, plex_item.locations[0])
            else:
                return self.emby_api.get_invalid_item_id()
        else:
            return self.emby_api.get_invalid_item_id()
    
    def get_emby_movie_id(self, plex_history_item):
        plex_item = self.plex_api.fetchItem(plex_history_item['rating_key'])
        if plex_item is not self.plex_api.get_invalid_type():
            return self.emby_api.get_movie_item_id(plex_item.title, plex_item.locations[0])
        else:
            return self.emby_api.get_invalid_item_id()
        
    def sync_plex_watch_status(self, user, dateTimeStringForHistory):
        try:
            watchHistoryData = self.tautulli_api.get_watch_history_for_user(user.plex_user_id, dateTimeStringForHistory)
            for historyItem in watchHistoryData:
                if (historyItem['watched_status'] == 1):
                    emby_item_id = self.emby_api.get_invalid_item_id()
                    if historyItem['media_type'] == self.tautulli_api.get_media_type_episode_name():
                        emby_item_id = self.get_emby_tv_show_episode_id(historyItem)
                    elif historyItem['media_type'] == self.tautulli_api.get_media_type_movie_name():
                        emby_item_id = self.get_emby_movie_id(historyItem)
                    
                    # If the item id is valid and the user has not already watched the item
                    if emby_item_id != self.emby_api.get_invalid_item_id() and self.emby_api.get_watched_status(user.emby_user_name, emby_item_id) == False:
                        self.set_emby_watched_item(user, emby_item_id, historyItem['full_title'])
        except Exception as e:
            self.logger.error("{}: Get Plex History ERROR:{}".format(self.__module__, e))
    
    def set_plex_show_watched(self, emby_series_path, emby_episode_item, user):
        try:
            cleaned_show_name = remove_year_from_name(emby_episode_item['SeriesName']).lower()
            results = self.plex_api.search(cleaned_show_name, 'show')
            for item in results:
                if item.locations[0] == emby_series_path:
                    # Search for the show
                    show = self.plex_api.get_library_item(item.librarySectionTitle, item.title)
                    if show is not self.plex_api.get_invalid_type():
                        episode = show.episode(season=emby_episode_item['ParentIndexNumber'], episode=emby_episode_item['IndexNumber'])
                        if episode is not None and episode.isWatched == False and episode.locations[0] == emby_episode_item['Path']:
                            episode.markWatched()
                            self.logger.info('{}: {} watched {} on Emby sync Plex watch status'.format(self.__module__, user.emby_user_name, episode.grandparentTitle + ' - ' + episode.title))
                        break
        except Exception as e:
            self.logger.error("Error with plex movie watched: {}".format(e))

    def set_plex_movie_watched(self, emby_item, user):
        try:
            lower_title = emby_item['Name'].lower()
            result_items = self.plex_api.search(lower_title, 'movie')
            for item in result_items:
                if item.locations[0] == emby_item['Path']:
                    if item.isWatched == False:
                        media_Item = self.plex_api.get_library_item(item.librarySectionTitle, item.title)
                        if media_Item is not self.plex_api.get_invalid_type():
                            media_Item.markWatched()
                            self.logger.info('{}: {} watched {} on Emby Sync Plex Watch Status'.format(self.__module__, user.emby_user_name, emby_item['Name']))
                    break
        except Exception as e:
            self.logger.error("{}: Error with plex movie watched: {}".format(self.__module__, e))
        
    def sync_emby_watch_status(self, user):
        try:
            history_items = self.jellystat_api.get_user_watch_history(user.emby_user_id)
            if len(history_items) > 0:
                self.plex_api.switch_plex_account(user.plex_user_name)
                
                # Search through the list and find items to sync
                for item in history_items:
                    if self.get_hours_since_play(True, datetime.fromisoformat(item['ActivityDateInserted'])) < 24:
                        if item['SeriesName'] is not None:
                            # Check that the episode has been marked as watched by emby
                            if self.emby_api.get_watched_status(user.emby_user_name, item['EpisodeId']) == True:
                                emby_series_item = self.emby_api.search_item(item['NowPlayingItemId'])
                                emby_episode_item = self.emby_api.search_item(item['EpisodeId'])
                                if emby_series_item is not None and emby_episode_item is not None:
                                    self.set_plex_show_watched(emby_series_item['Path'], emby_episode_item, user)
                        else:
                            # Check that the item has been marked as watched by emby
                            if self.emby_api.get_watched_status(user.emby_user_name, item['NowPlayingItemId']) == True:
                                emby_item = self.emby_api.search_item(item['NowPlayingItemId'])
                                if emby_item is not None and emby_item['Type'] == self.emby_api.get_media_type_movie_name():
                                    self.set_plex_movie_watched(emby_item, user)
                            
        except Exception as e:
            self.logger.error("{}: Error in emby watch status: {}".format(self.__module__, e))
    
    
    def sync_watch_status(self):
        dateTimeStringForHistory = get_datetime_for_history_plex_string(1)
        for user in self.user_list:
            self.sync_plex_watch_status(user, dateTimeStringForHistory)
            self.sync_emby_watch_status(user)
        
    def init_scheduler_jobs(self):
        self.logger.info('{} Enabled. Running every hour:{} minute:{}'.format(self.__module__, self.cronHours, self.cronMinutes))
        self.logger.info('{}: Running start up sync'.format(self.__module__))
        self.sync_watch_status()
        self.scheduler.add_job(self.sync_watch_status, trigger='cron', hour=self.cronHours, minute=self.cronMinutes)
