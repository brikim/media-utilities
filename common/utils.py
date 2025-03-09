import logging
from datetime import datetime, timedelta
from common.types import CronInfo

ansi_start_code: str = "\33[38;5;"
ansi_end_code: str = "m"

def get_log_ansi_code() -> str:
    return f"{ansi_start_code}15{ansi_end_code}"

def get_tag_ansi_code() -> str:
    return f"{ansi_start_code}37{ansi_end_code}"

def get_plex_ansi_code() -> str:
    return f"{ansi_start_code}220{ansi_end_code}"

def get_emby_ansi_code() -> str:
    return f"{ansi_start_code}82{ansi_end_code}"

def get_tautulli_ansi_code() -> str:
    return f"{ansi_start_code}136{ansi_end_code}"
    
def get_jellystat_ansi_code() -> str:
    return f"{ansi_start_code}63{ansi_end_code}"
    
def get_log_header(module_ansi_code: str, module: str) -> str:
    return f"{module_ansi_code}{module}{get_log_ansi_code()}:"
    
def get_tag(tag_name: str, tag_value) -> str:
    return f"{get_tag_ansi_code()}{tag_name}={get_log_ansi_code()}{tag_value}"

def get_formatted_plex() -> str:
    return f"{get_plex_ansi_code()}Plex{get_log_ansi_code()}"

def get_formatted_tautulli() -> str:
    return f"{get_tautulli_ansi_code()}Tautulli{get_log_ansi_code()}"

def get_formatted_emby() -> str:
    return f"{get_emby_ansi_code()}Emby{get_log_ansi_code()}"

def get_formatted_jellystat() -> str:
    return f"{get_jellystat_ansi_code()}Jellystat{get_log_ansi_code()}"

def get_datetime_for_history(deltaDays: float) -> datetime:
        return datetime.now() - timedelta(deltaDays)

def get_datetime_for_history_plex_string(deltaDays: float) -> str:
        return get_datetime_for_history(deltaDays).strftime("%Y-%m-%d")

def remove_year_from_name(name: str) -> str:
    # Remove any year from the name ... example (2017)
    open_par_index = name.find(" (")
    if open_par_index >= 0:
        close_par_index = name.find(")")
        if close_par_index > open_par_index:
            return name[0:open_par_index] + name[close_par_index+1:len(name)]
    return name

def get_cron_from_string(
    cron_string: str,
    logger: logging,
    module_name: str
) -> CronInfo:
    cron_params = cron_string.split()
    if len(cron_params) >= 2 and len(cron_params) <= 5:
        return CronInfo(cron_params[1], cron_params[0])
    else:
        logger.error(
            f"{module_name}: Invalid Cron Expression {cron_string}"
        )
    return None

def remove_ansi_code_from_text(text: str) -> str:
    plain_text = text
    while True:
        index = plain_text.find(ansi_start_code)
        if (index < 0):
            break
        else:
            end_index = plain_text.find(ansi_end_code, index)
            if end_index < 0:
                break
            else:
                end_index += 1
                plain_text = plain_text[:index] + plain_text[end_index:]
    return plain_text

def build_target_string(current_target: str, new_target: str, library: str) -> str:
    if current_target != "":
        if library == "":
            return current_target + f" & {new_target}"
        else:
            return current_target + f" & {new_target}:{library}"
    else:
        if library == "":
            return new_target
        else:
            return f"{new_target}:{library}"
