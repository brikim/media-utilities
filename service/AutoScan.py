
import os
import time
from datetime import datetime
import threading
from threading import Thread
from dataclasses import dataclass
import inotify.adapters

from api.plex import PlexAPI
from api.emby import EmbyAPI
from common.utils import get_log_ansi_code
@dataclass
class ScanInfo:
    path: str
    plex_library_valid: bool
    plex_library: str
    emby_library_valid: bool
    emby_library: str
    time: float
    
class AutoScan:
    def __init__(self, plex_api, emby_api, config, logger):
        self.service_ansi_code = '\33[96m'
        self.tag_ansi_code = '\33[36m'
        self.plex_api = plex_api
        self.emby_api = emby_api
        self.logger = logger
        self.ignore_folder_with_name = []
        self.valid_file_extensions = []
        
        self.sleep_time = 1
        
        self.seconds_before_notify = 0
        self.seconds_between_notifies = 0
        self.last_notify_time = 0.0
        
        self.notify_plex = False
        self.notify_emby = False
        
        self.scans = []
        
        self.monitors = []
        self.monitor_lock = threading.Lock()
        self.monitor_thread = None
        
        self.threads = []
        self.lock = threading.Lock()
        self.stop_threads = False
        
        try:
            self.seconds_before_notify = max(config['seconds_before_notify'], 30)
            self.seconds_between_notifies = max(config['seconds_between_notifies'], 10)
            
            if 'notify_plex' in config:
                self.notify_plex = config['notify_plex'] == 'True'
            
            if 'notify_emby' in config:
                self.notify_emby = config['notify_emby'] == 'True'
            
            for scan in config['scans']:
                plex_library = ''
                if self.notify_plex == True and 'plex_path' in scan:
                    plex_library = self.plex_api.get_library_name_from_path(scan['plex_path'])
                
                emby_library = ''
                if self.notify_emby == True and 'emby_path' in scan:
                    emby_library = self.emby_api.get_library_name_from_path(scan['emby_path'])
                
                self.scans.append(ScanInfo(scan['container_path'], plex_library != '', plex_library, emby_library != '', emby_library, 0.0))
            
            for folder in config['ignore_folder_with_name']:
                self.ignore_folder_with_name.append(folder['ignore_folder'])
                
            if config['valid_file_extensions'] != '':
                self.valid_file_extensions = config['valid_file_extensions'].split(',')
                
                
        except Exception as e:
            self.logger.error('{}{}{}: Read config ERROR:{}'.format(self.service_ansi_code, self.__module__, get_log_ansi_code() , e))
    
    def shutdown(self):
        self.stop_threads = True
        
        # Create a temp file to notify the inotify adapters
        for scan in self.scans:
            temp_file = scan.path + '/temp.txt'
            with open(temp_file, 'w') as file:
                file.write('BREAK')
            
        # allow time for the events
        time.sleep(1)
        
        with self.monitor_lock:
            self.monitors.clear()
                            
        # clean up the temp files
        for scan in self.scans:
            temp_file = scan.path + '/temp.txt'
            os.remove(temp_file)
        
        self.logger.info('{}{}{}: Successful shutdown'.format(self.service_ansi_code, self.__module__, get_log_ansi_code()))
    
    def log_moved_to_target(self, path, library, server_name):
        self.logger.info('{}{}{}: Monitor moved to target - {}path={}{} {}library={}{} {}target={}{} '.format(self.service_ansi_code, self.__module__, get_log_ansi_code(), self.tag_ansi_code, get_log_ansi_code(), path, self.tag_ansi_code, get_log_ansi_code(), library, self.tag_ansi_code, get_log_ansi_code(), server_name))
        
    def notify_media_servers(self, monitor):
        if self.notify_plex == True and monitor.plex_library_valid == True:
            self.plex_api.set_library_scan(monitor.plex_library)
            self.log_moved_to_target(monitor.path, monitor.plex_library, 'plex')
        if self.notify_emby == True and monitor.emby_library_valid == True:
            self.emby_api.set_library_scan()
            self.log_moved_to_target(monitor.path, monitor.emby_library, 'emby')
        
    def monitor_in_progress(self):
        while self.stop_threads == False:
            if len(self.monitors) > 0:
                current_time = time.time()
                if current_time - self.last_notify_time >= self.seconds_between_notifies:
                    notify_found = False
                    current_index = 0
                    for monitor in self.monitors:
                        if (current_time - monitor.time) >= self.seconds_before_notify:
                            self.notify_media_servers(monitor)
                            self.last_notify_time = current_time
                            notify_found = True
                            break
                        
                        current_index += 1
    
                    if notify_found == True:
                        with self.monitor_lock:
                            self.monitors.pop(current_index)
                    
            time.sleep(self.sleep_time)
    
    def add_file_monitor(self, path, scan):
        found = False
        current_time = time.time()
        for monitor in self.monitors:
            if monitor.path == path:
                monitor.time = current_time
                found = True
        
        if found == False:
            with self.monitor_lock:
                self.monitors.append(ScanInfo(path, scan.plex_library_valid, scan.plex_library, scan.emby_library_valid, scan.emby_library, current_time))
            self.logger.info('{}{}{}: Scan moved to monitor - {}path={}{}'.format(self.service_ansi_code, self.__module__, get_log_ansi_code(), self.tag_ansi_code, get_log_ansi_code(), path))
        
    def monitor_path(self, scan):
        self.logger.info('{}{}{}: Starting Monitor for {}'.format(self.service_ansi_code, self.__module__, get_log_ansi_code(), scan.path))
            
        i = inotify.adapters.InotifyTree(scan.path)
        for event in i.event_gen(yield_nones=False):
            (_, type_names, path, filename) = event
            if filename != '':
                for type in type_names:
                    if type == 'IN_CREATE' or type == 'IN_MODIFY' or type == "IN_MOVED_TO" or type == 'IN_MOVED_FROM' or type == 'IN_DELETE':
                        path_valid = True
                        for folder_name in self.ignore_folder_with_name:
                            if folder_name in path:
                                path_valid = False
                                break
                            
                        if len(self.valid_file_extensions) > 0:
                            path_valid = False
                            for valid_extension in self.valid_file_extensions:
                                if filename.endswith(valid_extension):
                                    path_valid = True
                                    break
                        
                        if path_valid == True:
                            self.add_file_monitor(path, scan)
                        break
            
            if self.stop_threads == True:
                self.logger.info('{}{}{}: Stopping Watch for {}'.format(self.service_ansi_code, self.__module__, get_log_ansi_code(), scan.path))
                break
        
    def start(self):
        for scan in self.scans:
            thread = Thread(target=self.monitor_path, args=(scan,)).start()
            self.threads.append(thread)
        
        self.monitor_thread = Thread(target=self.monitor_in_progress, args=()).start()
        
    def init_scheduler_jobs(self):
        self.logger.info('{}{}{} Enabled'.format(self.service_ansi_code, self.__module__, get_log_ansi_code()))
        self.start()
