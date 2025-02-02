import logging
from datetime import datetime, timedelta
from common.types import CronInfo

def get_log_ansi_code() -> str:
    return '\33[97m'

def get_tag_ansi_code() -> str:
    return '\33[36m'

def get_plex_ansi_code() -> str:
    return '\33[93m'

def get_emby_ansi_code() -> str:
    return '\33[92m'

def get_tautulli_ansi_code() -> str:
    return '\33[33m' 
    
def get_jellystat_ansi_code() -> str:
    return '\33[34m'
    
def get_log_header(module_ansi_code: str, module: str) -> str:
    return '{}{}{}:'.format(module_ansi_code, module, get_log_ansi_code())
    
def get_tag(tag_name: str, tag_value) -> str:
    return '{}{}={}{}'.format(get_tag_ansi_code(), tag_name, get_log_ansi_code(), tag_value)

def get_formatted_plex() -> str:
    return '{}Plex{}'.format(get_plex_ansi_code(), get_log_ansi_code())

def get_formatted_tautulli() -> str:
    return '{}Tautulli{}'.format(get_tautulli_ansi_code(), get_log_ansi_code())

def get_formatted_emby() -> str:
    return '{}Emby{}'.format(get_emby_ansi_code(), get_log_ansi_code())

def get_formatted_jellystat() -> str:
    return '{}Jellystat{}'.format(get_jellystat_ansi_code(), get_log_ansi_code())

def get_datetime_for_history(deltaDays: float) -> datetime:
        return datetime.now() - timedelta(deltaDays)

def get_datetime_for_history_plex_string(deltaDays: float) -> str:
        return get_datetime_for_history(deltaDays).strftime('%Y-%m-%d')

def remove_year_from_name(name: str) -> str:
    # Remove any year from the name ... example (2017)
    open_par_index = name.find(" (")
    if open_par_index >= 0:
        close_par_index = name.find(")")
        if close_par_index > open_par_index:
            return name[0:open_par_index] + name[close_par_index+1:len(name)]
    return name

def get_cron_from_string(cron_string: str, logger: logging, module_name: str) -> CronInfo:
    cron_params = cron_string.split()
    if len(cron_params) >= 2 and len(cron_params) <= 5:
        return CronInfo(cron_params[1], cron_params[0])
    else:
        logger.error('{}: Invalid Cron Expression {}'.format(module_name, cron_string))
    return None

def remove_ansi_code_from_text(text: str) -> str:
    plain_text = text
    while True:
        index = plain_text.find('\33[')
        if (index < 0):
            break
        else:
            end_index = plain_text.find('m', index)
            if end_index < 0:
                break
            else:
                end_index += 1
                plain_text = plain_text[:index] + plain_text[end_index:]
    return plain_text

def build_target_string(current_target: str, new_target: str, library: str) -> str:
    if current_target != '':
        if library == '':
            return current_target + ' & {}'.format(new_target)
        else:
            return current_target + ' & {}:{}'.format(new_target, library)
    else:
        if library == '':
            return '{}'.format(new_target)
        else:
            return '{}:{}'.format(new_target, library)
