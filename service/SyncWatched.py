#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Sync media server watch status
"""
import requests
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

@dataclass
class UserInfo:
    plex_user_name: str
    plex_user_id: int
    emby_user_name: str
    emby_user_id: str

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
                    if plexUserId != 0 and embyUserId != '0':
                        self.user_list.append(UserInfo(plexUserName, plexUserId, embyUserName, embyUserId))
                    else:
                        self.logger.error('{}: No Plex user found for {} ... Skipping User'.format(self.__module__ , plexUserName))

            self.logger.info('{} Enabled. Running every hour:{} minute:{}'.format(self.__module__, self.cronHours, self.cronMinutes))
        except Exception as e:
            self.logger.error("{}: Read config ERROR:{}".format(self.__module__ , e))
    
    def get_hours_since_play(self, useUtcTime, playDateTime):
        currentDateTime = datetime.now(timezone.utc) if useUtcTime == True else datetime.now()
        time_difference = currentDateTime - playDateTime
        return (time_difference.days * 24) + (time_difference.seconds / 3600)
    
    def get_datetime_for_history(self):
        return datetime.now() - timedelta(1)

    def set_emby_watched_item(self, user, itemId, fullTitle):
        try:
            self.emby_api.set_watched_item(user.emby_user_id, itemId)
            self.logger.info('{}: {} watched {} on Plex sync Emby watch status'.format(self.__module__, user.plex_user_name, fullTitle))
        except Exception as e:
            self.logger.error("{}: Set Emby watched ERROR:{}".format(self.__module__, e))
            
    def sync_plex_watch_status(self, user, dateTimeStringForHistory):
        try:
            watchHistoryData = self.tautulli_api.get_watch_history_for_user(user.plex_user_id, dateTimeStringForHistory)
            for historyItem in watchHistoryData:
                if (historyItem['watched_status'] == 1):
                    if historyItem['media_type'] == 'episode':
                        embyItemId = self.emby_api.get_episode_item_id(historyItem['grandparent_title'], historyItem['title'])
                    else:
                        embyItemId = self.emby_api.get_movie_item_id(historyItem['full_title'])
                    
                    # If the item id is valid and the user has not already watched the item
                    if embyItemId != '0' and self.emby_api.get_watched_status(user.emby_user_name, embyItemId) == False:
                        self.set_emby_watched_item(user, embyItemId, historyItem['full_title'])
        except Exception as e:
            self.logger.error("{}: Get Plex History ERROR:{}".format(self.__module__, e))
    
    def set_plex_show_watched(self, showName, seasonNum, episodeNum, user):
        try:
            results = self.plex_api.search(showName)
            for item in results:
                if item.title == showName:
                    # Search for the show
                    show = self.plex_api.library.section(item.librarySectionTitle).get(item.title)
                    episode = show.episode(season=seasonNum, episode=episodeNum)
                    if episode and episode.isWatched == False:
                        episode.markWatched()
                        self.logger.info('{}: {} watched {} on Emby sync Plex watch status'.format(self.__module__, user.emby_user_name, showName + ' - ' + episode.title))
                    break
        except Exception as e:
            self.logger.error("Error with plex movie watched: {}".format(e))

    def set_plex_movie_watched(self, title, user):
        try:
            results = self.plex_api.search(title)
            for item in results:
                if item.title == title:
                    mediaItem = self.plex_api.library.section(item.librarySectionTitle).get(item.title)
                    if mediaItem and mediaItem.isWatched == False:
                        mediaItem.markWatched()
                        self.logger.info('{}: {} watched {} on Emby Sync Plex Watch Status'.format(self.__module__, user.emby_user_name, title))
                    break
        except Exception as e:
            self.logger.error("{}: Error with plex movie watched: {}".format(self.__module__, e))
        
    def sync_emby_watch_status(self, user):
        try:
            historyItems = self.jellystat_api.get_user_watch_history(user.emby_user_id)
            if len(historyItems) > 0:
                current_user = self.plex_api.myPlexAccount()
                if current_user.username != user.plex_user_name:
                    self.plex_api.switchUser(user.plex_user_name)

                # Search through the list and find items to sync
                for item in historyItems:
                    if self.get_hours_since_play(True, datetime.fromisoformat(item['ActivityDateInserted'])) < 24:
                        if item['SeriesName'] is None:
                            self.set_plex_movie_watched(item['NowPlayingItemName'], user)
                        else:
                            self.set_plex_show_watched(item['SeriesName'], item['SeasonNumber'], item['EpisodeNumber'], user)
        except Exception as e:
            self.logger.error("{}: Error in emby watch status: {}".format(self.__module__, e))
    
    
    def sync_watch_status(self):
        self.logger.info('{}: Sync Watch Status Running'.format(self.__module__))

        dateTimeStringForHistory = self.get_datetime_for_history().strftime('%Y-%m-%d')

        for user in self.user_list:
            self.sync_plex_watch_status(user, dateTimeStringForHistory)
            self.sync_emby_watch_status(user)

        self.logger.info('{}: Sync Watch Status Completed'.format(self.__module__))
        
    def init_scheduler_jobs(self):
        self.logger.info('{}: Running start up sync'.format(self.__module__))
        self.sync_watch_status()
        self.scheduler.add_job(self.sync_watch_status, trigger='cron', hour=self.cronHours, minute=self.cronMinutes)
