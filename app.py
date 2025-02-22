"""
Media Utilities
"""

version = 'v2.2.0'

import sys
import os
import json
import logging
import colorlog
import signal
from sys import platform
from logging.handlers import RotatingFileHandler
from apscheduler.schedulers.blocking import BlockingScheduler

from api.plex import PlexAPI
from api.tautulli import TautulliAPI
from api.emby import EmbyAPI
from api.jellystat import JellystatAPI

from common.gotify_handler import GotifyHandler
from common.plain_text_formatter import PlainTextFormatter
from common.gotify_plain_text_formatter import GotifyPlainTextFormatter
from common import utils

from service.ServiceBase import ServiceBase
from service.DeleteWatched import DeleteWatched
from service.DvrMaintainer import DvrMaintainer
from service.FolderCleanup import FolderCleanup
from service.SyncWatched import SyncWatched
from service.PlaylistSync import PlaylistSync

# Global Variables #######
logger = logging.getLogger(__name__)
scheduler = BlockingScheduler()

# Api
plex_api: PlexAPI = None
tautulli_api: TautulliAPI = None
emby_api: EmbyAPI = None
jellystat_api: JellystatAPI = None
        
# Available Services
services: list[ServiceBase] = []
##########################

def handle_sigterm(signum, frame):
    logger.info("SIGTERM received, shutting down ...")
    for service in services:
        service.shutdown()
    scheduler.shutdown(wait=True)
    sys.exit(0)

def do_nothing():
    pass

conf_loc_path_file = ""
config_file_valid = True
if "CONFIG_PATH" in os.environ:
    conf_loc_path_file = os.environ['CONFIG_PATH'].rstrip('/')
else:
    config_file_valid = False

if config_file_valid == True and os.path.exists(conf_loc_path_file) == True:
    try:
        # Opening JSON file
        f = open(conf_loc_path_file, 'r')
        data = json.load(f)

        # Main script run ####################################################

        # Set up signal termination handle
        signal.signal(signal.SIGTERM, handle_sigterm)

        #date format
        date_format = '%Y-%m-%d %H:%M:%S'

        # Set up the logger
        logger.setLevel(logging.INFO)
        formatter = PlainTextFormatter()
        
        # Create a file handler to write logs to a file
        rotating_handler = RotatingFileHandler('/logs/media-utility.log', maxBytes=50000, backupCount=5)
        rotating_handler.setLevel(logging.INFO)
        rotating_handler.setFormatter(formatter)

        log_colors = {
            'DEBUG': 'cyan',
            'INFO': 'light_green',
            'WARNING': 'light_yellow',
            'ERROR': 'light_red',
            'CRITICAL': 'bold_red'}

        # Create a stream handler to print logs to the console
        console_info_handler = colorlog.StreamHandler()
        console_info_handler.setLevel(logging.INFO)
        console_info_handler.setFormatter(colorlog.ColoredFormatter(
            '%(white)s%(asctime)s %(light_white)s- %(log_color)s%(levelname)s %(light_white)s- %(message)s', date_format, log_colors=log_colors))

        gotify_formatter = None
        gotify_handler = None
        if 'gotify_logging' in data and 'enabled' in data['gotify_logging'] and data['gotify_logging']['enabled'] == 'True':
            gotify_formatter = GotifyPlainTextFormatter()
            gotify_handler = GotifyHandler(data['gotify_logging']['url'], data['gotify_logging']['app_token'], data['gotify_logging']['message_title'], data['gotify_logging']['priority'])
            gotify_handler.setLevel(logging.WARNING)
            gotify_handler.setFormatter(gotify_formatter)
            
        # Add the handlers to the logger
        logger.addHandler(rotating_handler)
        logger.addHandler(console_info_handler)
        if gotify_handler is not None:
            logger.addHandler(gotify_handler)
        
        logger.info('Starting Media Utilities {} *************************************'.format(version))
        
        # Create all the api servers
        if 'plex_url' in data and 'plex_api_key' in data:
            plex_api = PlexAPI(data['plex_url'], data['plex_api_key'], data['plex_admin_user_name'], data['plex_media_path'], logger)
            if plex_api.get_valid() == True:
                logger.info('Connected to {}:{} successfully'.format(utils.get_formatted_plex(), plex_api.get_name()))
            else:
                logger.warning('{} server not available. Is this correct {} {}'.format(utils.get_formatted_plex(),  utils.get_tag('url', data['plex_url']),  utils.get_tag('api_key', data['plex_api_key'])))
        elif 'plex_url' in data or 'plex_api_key' in data:
            logger.warning('{} configuration error must define both plex_url and plex_api_key'.format(utils.get_formatted_plex()))
        
        if 'tautulli_url' in data and 'tautulli_api_key' in data:
            tautulli_api = TautulliAPI(data['tautulli_url'], data['tautulli_api_key'], logger)
            if tautulli_api.get_valid() == True:
                logger.info('Connected to {}:{} successfully'.format(utils.get_formatted_tautulli(), tautulli_api.get_name()))
            else:
                logger.warning('{} not available. Is this correct {} {}'.format(utils.get_formatted_tautulli(),  utils.get_tag('url', data['tautulli_url']),  utils.get_tag('api_key', data['tautulli_api_key'])))
        elif 'tautulli_url' in data or 'tautulli_api_key' in data:
            logger.warning('{} configuration error must define both tautulli_url and tautulli_api_key'.format(utils.get_formatted_tautulli()))
            
        if 'emby_url' in data and 'emby_api_key' in data:
            emby_api = EmbyAPI(data['emby_url'], data['emby_api_key'], data['emby_media_path'], logger)
            if emby_api.get_valid() == True:
                logger.info('Connected to {}:{} successfully'.format(utils.get_formatted_emby(), emby_api.get_name()))
            else:
                logger.warning('{} server not available. Is this correct {} {}'.format(utils.get_formatted_emby(),  utils.get_tag('url', data['emby_url']),  utils.get_tag('api_key', data['emby_api_key'])))
        elif 'emby_url' in data or 'emby_api_key' in data:
            logger.warning('{} configuration error must define both emby_url and emby_api_key'.format(utils.get_formatted_emby()))
        
        if 'jellystat_url' in data and 'jellystat_api_key' in data:
            jellystat_api = JellystatAPI(data['jellystat_url'], data['jellystat_api_key'], logger)
            if jellystat_api.get_valid() == True:
                logger.info('Connected to {} successfully'.format(utils.get_formatted_jellystat()))
            else:
                logger.warning('{} not available. Is this correct {} {}'.format(utils.get_formatted_jellystat(),  utils.get_tag('url', data['jellystat_url']),  utils.get_tag('api_key', data['jellystat_api_key'])))
        elif 'jellystat_url' in data or 'jellystat_api_key' in data:
            logger.warning('{} configuration error must define both jellystat_url and jellystat_api_key'.format(utils.get_formatted_jellystat()))
        
        # Create the services ####################################
        
        # Create the Sync Watched Status Service
        if 'sync_watched' in data and data['sync_watched']['enabled'] == 'True':
            services.append(SyncWatched('\33[96m', plex_api, tautulli_api, emby_api, jellystat_api, data['sync_watched'], logger, scheduler))
        if 'delete_watched' in data and data['delete_watched']['enabled'] == 'True':
            services.append(DeleteWatched('\33[32m', plex_api, tautulli_api, emby_api, jellystat_api, data['delete_watched'], logger, scheduler))
        if 'dvr_maintainer' in data and data['dvr_maintainer']['enabled'] == 'True':
            services.append(DvrMaintainer('\33[95m', plex_api, emby_api, data['dvr_maintainer'], logger, scheduler))
        if 'folder_cleanup' in data and data['folder_cleanup']['enabled'] == 'True':
            services.append(FolderCleanup('\33[33m', plex_api, emby_api, data['folder_cleanup'], logger, scheduler))
        if 'playlist_sync' in data and data['playlist_sync']['enabled'] == 'True':
            services.append(PlaylistSync('\33[94m', plex_api, emby_api, data['playlist_sync'], logger, scheduler))
        
        # ########################################################
        
        # Init the services ######################################
        for service in services:
            service.init_scheduler_jobs()
        # ########################################################
        
        # Add a job to do nothing to keep the script alive
        scheduler.add_job(do_nothing, trigger='interval', hours=24)
        
        # Start the scheduler for all jobs
        scheduler.start()
        
    except Exception as e:
        logger.error("Error starting: {}".format(e))
else:
    sys.stderr.write("Error opening config file {}\n".format(conf_loc_path_file))

# END Main script run ####################################################