
import os
import glob
from datetime import datetime
from dataclasses import dataclass
from common.types import CronInfo
from common.utils import get_cron_from_string, get_log_ansi_code, get_tag_ansi_code

@dataclass
class ShowConfig:
    name: str
    action_type: str
    action_value: int
    plex_library_name: str
    utility_path: str
    
@dataclass
class FileInfo:
    path: str
    ageDays: float

class DvrMaintainer:
    def __init__(self, ansi_code, plex_api, emby_api, config, logger, scheduler):
        self.service_ansi_code = ansi_code
        self.plex_api = plex_api
        self.emby_api = emby_api
        self.logger = logger
        self.scheduler = scheduler
        self.cron = None
        self.show_configurations = []
        self.run_test = False
        
        try:
            self.cron = get_cron_from_string(config['cron_run_rate'], self.logger, self.__module__)
            
            for show in config['show_details']:
                action = ''
                actionValue = 0
                if show['action'].find('KEEP_LAST_') != -1:
                    action = 'KEEP_LAST'
                    actionValue = int(show['action'].replace('KEEP_LAST_', ''))
                elif show['action'].find('KEEP_LENGTH_DAYS_') != -1:
                    action = 'KEEP_LENGTH_DAYS'
                    actionValue = int(show['action'].replace('KEEP_LENGTH_DAYS_', ''))
                
                if action != '':
                    self.show_configurations.append(ShowConfig(show['name'], action, actionValue, show['plex_library_name'], show['utilities_path'].rstrip('/')))
                else:
                    self.logger.error('{}{}{}: Unknown show action {}. Skipping show detail'.format(self.service_ansi_code, self.__module__, get_log_ansi_code(), show['action']))
        
        except Exception as e:
            self.logger.error("{}{}{}: Read config {}error={}{}".format(self.service_ansi_code, self.__module__, get_log_ansi_code(), get_tag_ansi_code(), get_log_ansi_code(), e))
    
    def get_files_in_path(self, path):
        fileInfo = []
        for file in glob.glob(path + "/**/*", recursive=True):
            if file.endswith(".ts") or file.endswith(".mkv"):
                fileAge = datetime.now() - datetime.fromtimestamp(os.path.getmtime(file))
                fileInfo.append(FileInfo(file, fileAge.days + (fileAge.seconds / 86400)))
        return fileInfo

    def delete_file(self, pathFileName):
        if self.run_test == True:
            self.logger.info("{}{}{}: Running Test! Would delete {}".format(self.service_ansi_code, self.__module__, get_log_ansi_code(), pathFileName))
        else:
            try:
                os.remove(pathFileName)
            except Exception as e:
                self.logger.error("{}{}{}: Problem deleting file {} {}error={}{}".format(self.service_ansi_code, self.__module__, get_log_ansi_code(), pathFileName, get_tag_ansi_code(), get_log_ansi_code(), e))
    
    def keep_last_delete(self, path, keepLast):
        showsDeleted = False
        fileInfo = self.get_files_in_path(path)
        if len(fileInfo) > keepLast:
            self.logger.info("{}{}{}: KEEP_LAST_{} {}show={}{} has {}episodes={}".format(self.service_ansi_code, self.__module__, get_log_ansi_code(), keepLast, get_tag_ansi_code(), get_log_ansi_code(), path, get_tag_ansi_code(), get_log_ansi_code(), len(fileInfo)))
            try:
                sortedFileInfo = sorted(fileInfo, key=lambda item: item.ageDays, reverse=True)

                showsToDelete = len(fileInfo) - keepLast
                deletedShows = 0
                for file in sortedFileInfo:
                    self.logger.info("{}{}{}: KEEP_LAST_{} deleting oldest {}file={}{}".format(self.service_ansi_code, self.__module__, get_log_ansi_code(), keepLast, get_tag_ansi_code(), get_log_ansi_code(), file.path))
                    self.delete_file(file.path)
                    showsDeleted = True

                    deletedShows += 1
                    if deletedShows >= showsToDelete:
                        break
            
            except Exception as e:
                self.logger.error("{}{}{}: KEEP_LAST_{} error sorting files {}error={}{}".format(self.service_ansi_code, self.__module__, get_log_ansi_code(), keepLast, get_tag_ansi_code(), get_log_ansi_code(), e))

        return showsDeleted

    def keep_show_days(self, path, keepDays):
        showsDeleted = False
        fileInfo = self.get_files_in_path(path)
        for file in fileInfo:
            if file.ageDays >= keepDays:
                self.logger.info("{}{}{}: KEEP_DAYS_{} deleting {}age days={}{:.1f} {}file={}{}".format(self.service_ansi_code, self.__module__, get_log_ansi_code(), keepDays, get_tag_ansi_code(), get_log_ansi_code(), file.ageDays, get_tag_ansi_code(), get_log_ansi_code(), file.path))
                self.delete_file(file.path)
                showsDeleted = True
        return showsDeleted

    def check_show_delete(self, config):
        deletedShowPlexLibraries = []
        libraryFilePath = config.utility_path + '/' + config.name
        if os.path.exists(libraryFilePath) == True:
            if config.action_type == 'KEEP_LAST':
                try:
                    showsDeleted = self.keep_last_delete(libraryFilePath, config.action_value)
                    if showsDeleted == True:
                        deletedShowPlexLibraries.append(config.plex_library_name)
                except Exception as e:
                    self.logger.error("{}{}{}: Check show delete keep last {}error={}{}".format(self.service_ansi_code, self.__module__, get_log_ansi_code(), get_tag_ansi_code(), get_log_ansi_code(), e))
            elif config.action_type == 'KEEP_LENGTH_DAYS':
                try:
                    showsDeleted = self.keep_show_days(libraryFilePath, config.action_value)
                    if showsDeleted == True:
                        deletedShowPlexLibraries.append(config.plex_library_name)
                except Exception as e:
                    self.logger.error("{}{}{}: Check show delete keep length {}error={}{}".format(self.service_ansi_code, self.__module__, get_log_ansi_code(), get_tag_ansi_code(), get_log_ansi_code(), e))

        return deletedShowPlexLibraries
    
    def notify_plex_refresh(self, library_list):
        self.plex_api.switch_plex_account_admin()
        for library in library_list:
            self.plex_api.set_library_scan(library)

    def do_maintenance(self):
        physicalPathsToCheckForDelete = []
        plexLibrariesToRefresh = []
        
        for show_config in self.show_configurations:
            deletedShows = self.check_show_delete(show_config)
            if len(deletedShows) > 0:
                physicalPathsToCheckForDelete.append(show_config.utility_path)
            for show in deletedShows:
                plexLibrariesToRefresh.append(show)
        
        # Notify media servers of a refresh
        if len(plexLibrariesToRefresh) > 0:
            self.notify_plex_refresh(list(set(plexLibrariesToRefresh)))
            self.emby_api.set_library_scan()
            self.logger.info("{}{}{}: Notifying Media Servers to Refresh".format(self.service_ansi_code, self.__module__, get_log_ansi_code()))
                
                
    def init_scheduler_jobs(self):
        if self.cron is not None:
            self.logger.info('{}{}{}: Enabled. Running every {}hour={}{} {}minute={}{}'.format(self.service_ansi_code, self.__module__, get_log_ansi_code(), get_tag_ansi_code(), get_log_ansi_code(), self.cron.hours, get_tag_ansi_code(), get_log_ansi_code(), self.cron.minutes))
            self.scheduler.add_job(self.do_maintenance, trigger='cron', hour=self.cron.hours, minute=self.cron.minutes)
        else:
            self.logger.warning('{}{}{}: Enabled but will not Run. Cron is not valid!'.format(self.service_ansi_code, self.__module__, get_log_ansi_code()))
