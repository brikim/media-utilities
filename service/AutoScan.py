
import os
import shutil
import time
from datetime import datetime
import threading
from threading import Thread
from dataclasses import dataclass
import inotify.adapters

from api.plex import PlexAPI
from api.emby import EmbyAPI

@dataclass
class ScanInfo:
    path: str
    plex_library: str
    
@dataclass
class WaitingScanData:
    path: str
    plex_library: str
    time: float
    
class AutoScan:
    def __init__(self, plex_api, emby_api, config, logger):
        self.plex_api = plex_api
        self.emby_api = emby_api
        self.logger = logger
        
        self.sleep_time = 1
        
        self.seconds_to_hold = 0
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
            self.seconds_to_hold = max(config['seconds_to_hold'], 30)
            
            if 'notify_plex' in config:
                self.notify_plex = config['notify_plex'] == 'True'
            
            if 'notify_emby' in config:
                self.notify_emby = config['notify_emby'] == 'True'
            
            for scan in config['scans']:
                plex_library = ''
                if 'plex_library_name' in scan:
                    plex_library = scan['plex_library_name']
                else:
                    if self.notify_plex == True:
                        self.logger.warning('{}: Set to notify plex of path {} updates but NO Plex Library defined!'.format(self.__module__, scan['path']))
                self.scans.append(ScanInfo(scan['path'], plex_library))
        except Exception as e:
            self.logger.error('{}: Read config ERROR:{}'.format(self.__module__ , e))
    
    def shutdown(self):
        self.stop_threads = True
        
        # Create a temp file to notify the inotify adapters
        for scan in self.scans:
            temp_file = scan.path + '/temp.txt'
            with open(temp_file, 'w') as file:
                file.write('BREAK')
            
        # allow time for the events
        time.sleep(1)
        
        # clean up the temp files
        for scan in self.scans:
            temp_file = scan.path + '/temp.txt'
            os.remove(temp_file)
            
        # join the threads to wait for shutdown
        for thread in self.threads:
            thread.join()
        
        self.logger.info('{}: Successful shutdown'.format(self.__module__))
    
    def notify_refresh(self, monitor):
        if self.notify_plex == True:
            self.logger.info('{}: Monitor moved to target - path:{} library:{} target:plex '.format(self.__module__, monitor.path, monitor.plex_library))
        if self.notify_emby == True:
            self.logger.info('{}: Monitor moved to target - path:{} target:emby '.format(self.__module__, monitor.path))
        
    def monitor_in_progress(self):
        while self.stop_threads == False:
            if len(self.monitors) > 0:
                current_time = time.time()

                notify_found = False
                current_index = 0
                for monitor in self.monitors:
                    if (current_time - monitor.time) >= self.seconds_to_hold:
                        self.notify_refresh(monitor)
                        notify_found = True
                        break
                    
                    current_index += 1

                if notify_found == True:
                    with self.monitor_lock:
                        self.monitors.pop(current_index)
                    
            time.sleep(self.sleep_time)
    
    def add_file_monitor(self, path, plex_library):
        found = False
        current_time = time.time()
        for monitor in self.monitors:
            if monitor.path == path:
                monitor.time = current_time
                found = True
        
        if found == False:
            with self.monitor_lock:
                self.monitors.append(WaitingScanData(path, plex_library, current_time))
            self.logger.info('{}: Scan moved to monitor - path:{}'.format(self.__module__, path))
        
    def monitor_path(self, scan):
        self.logger.info('{}: Starting Monitor for {}'.format(self.__module__, scan.path))
            
        i = inotify.adapters.InotifyTree(scan.path)
        for event in i.event_gen(yield_nones=False):
            (_, type_names, path, filename) = event
            if filename != '':
                for type in type_names:
                    if type == 'IN_CREATE' or type == 'IN_MODIFY' or type == "IN_MOVED_TO" or type == 'IN_MOVED_FROM' or type == 'IN_DELETE':
                        self.add_file_monitor(path, scan.plex_library)
                        break
            
            if self.stop_threads == True:
                self.logger.info('{}: Stopping Watch for {}'.format(self.__module__, scan.path))
                break
        
    def start(self):
        for scan in self.scans:
            thread = Thread(target=self.monitor_path, args=(scan,)).start()
            self.threads.append(thread)
        
        self.monitor_thread = Thread(target=self.monitor_in_progress, args=()).start()
        
    def init_scheduler_jobs(self):
        self.logger.info('{} Enabled'.format(self.__module__))
        self.start()
