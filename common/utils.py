
import os
import shutil
from datetime import datetime, timedelta
from common.types import CronInfo

def get_datetime_for_history(deltaDays):
        return datetime.now() - timedelta(deltaDays)

def get_datetime_for_history_plex_string(deltaDays):
        return get_datetime_for_history(deltaDays).strftime('%Y-%m-%d')

def remove_year_from_name(name):
    # Remove any year from the name ... example (2017)
    open_par_index = name.find(" (")
    if open_par_index >= 0:
        close_par_index = name.find(")")
        if close_par_index > open_par_index:
            return name[0:open_par_index] + name[close_par_index+1:len(name)]
    return name

def delete_empty_folders(paths_to_check, logger, module_name):
    # Delete empty folders in physical path if any exist
    for path in paths_to_check:
        folder_removed = True
        while folder_removed == True:
            folder_removed = False
            for dirpath, dirnames, filenames in os.walk(path, topdown=False):
                if not dirnames and not filenames:
                    shutil.rmtree(dirpath, ignore_errors=True)
                    logger.info("{}: Deleting Empty Folder: {}".format(module_name, dirpath))
                    folder_removed = True
                    
def get_cron_from_string(cron_string, logger, module_name):
    cron_params = cron_string.split()
    if len(cron_params) >= 2 and len(cron_params) <= 5:
        return CronInfo(cron_params[1], cron_params[0])
    else:
        logger.error('{}: Invalid Cron Expression {}'.format(module_name, cron_string))
    return None
