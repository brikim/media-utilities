
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

def get_cron_from_string(cron_string, logger, module_name):
    cron_params = cron_string.split()
    if len(cron_params) >= 2 and len(cron_params) <= 5:
        return CronInfo(cron_params[1], cron_params[0])
    else:
        logger.error('{}: Invalid Cron Expression {}'.format(module_name, cron_string))
    return None
