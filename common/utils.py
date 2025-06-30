""" Common Utilities """

import re
from datetime import datetime, timedelta, timezone

from common.types import CronInfo

ANSI_CODE_START: str = "\33[38;5;"
ANSI_CODE_END: str = "m"

ANSI_CODE_LOG = f"{ANSI_CODE_START}15{ANSI_CODE_END}"
ANSI_CODE_TAG = f"{ANSI_CODE_START}37{ANSI_CODE_END}"
ANSI_CODE_PLEX = f"{ANSI_CODE_START}220{ANSI_CODE_END}"
ANSI_CODE_TAUTULLI = f"{ANSI_CODE_START}136{ANSI_CODE_END}"
ANSI_CODE_EMBY = f"{ANSI_CODE_START}77{ANSI_CODE_END}"
ANSI_CODE_JELLYSTAT = f"{ANSI_CODE_START}63{ANSI_CODE_END}"
ANSI_CODE_STANDOUT = f"{ANSI_CODE_START}158{ANSI_CODE_END}"

ANSI_CODE_SERVICE_DELETE_WATCHED = f"{ANSI_CODE_START}142{ANSI_CODE_END}"
ANSI_CODE_SERVICE_DVR_MAINTAINER = f"{ANSI_CODE_START}210{ANSI_CODE_END}"
ANSI_CODE_SERVICE_FOLDER_CLEANUP = f"{ANSI_CODE_START}70{ANSI_CODE_END}"
ANSI_CODE_SERVICE_MEDIA_SERVER_SYNC = f"{ANSI_CODE_START}45{ANSI_CODE_END}"
ANSI_CODE_SERVICE_PLAYLIST_SYNC = f"{ANSI_CODE_START}171{ANSI_CODE_END}"


def get_log_header(module_ansi_code: str, module: str) -> str:
    """ Get a log header formatted string """
    return f"{module_ansi_code}{module}{ANSI_CODE_LOG}:"


def get_tag(tag_name: str, tag_value) -> str:
    """ Get a tag formatted string """
    return f"{ANSI_CODE_TAG}{tag_name}={ANSI_CODE_LOG}{tag_value}"


def get_formatted_plex() -> str:
    """ Get an ANSI code formatted Plex string """
    return f"{ANSI_CODE_PLEX}Plex{ANSI_CODE_LOG}"


def get_formatted_tautulli() -> str:
    """ Get an ANSI code formatted Tautulli string """
    return f"{ANSI_CODE_TAUTULLI}Tautulli{ANSI_CODE_LOG}"


def get_formatted_emby() -> str:
    """ Get an ANSI code formatted Emby string """
    return f"{ANSI_CODE_EMBY}Emby{ANSI_CODE_LOG}"


def get_formatted_jellystat() -> str:
    """ Get an ANSI code formatted Jellystat string """
    return f"{ANSI_CODE_JELLYSTAT}Jellystat{ANSI_CODE_LOG}"


def get_standout_text(text: str) -> str:
    """ Get an ANSI code formatted standout text string """
    return f"{ANSI_CODE_STANDOUT}{text}{ANSI_CODE_LOG}"


def get_datetime_for_history(delta_days: float) -> datetime:
    """ From days get a date and time for plex history """
    return datetime.now() - timedelta(delta_days)


def get_datetime_for_history_plex_string(delta_days: float) -> str:
    """ From days get a date and time for plex history """
    return get_datetime_for_history(delta_days).strftime("%Y-%m-%d")


def get_hours_since_play(
    use_utc_time: bool,
    play_date_time: datetime
) -> int:
    """ Get the hours since a play based on a time string """
    current_date_time = (
        datetime.now(timezone.utc)
        if use_utc_time else
        datetime.now()
    )
    time_difference = current_date_time - play_date_time
    return (time_difference.days * 24) + (time_difference.seconds / 3600)


def remove_year_from_name(name: str) -> str:
    """ Remove year in format (2018) from a string """
    open_par_index = name.find(" (")
    if open_par_index >= 0:
        close_par_index = name.find(")")
        if close_par_index > open_par_index:
            return name[0:open_par_index] + name[close_par_index+1:len(name)]
    return name


def get_cron_from_string(cron_string: str) -> CronInfo:
    """ Get a CronInfo from a string """
    cron_params = cron_string.split()
    if len(cron_params) >= 2 and len(cron_params) <= 5:
        return CronInfo(cron_params[1], cron_params[0])
    return None


def remove_ansi_code_from_text(text: str) -> str:
    """ Removes ANSI escape codes from a string """
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


def build_target_string(current_target: str, new_target: str, extra_info: str) -> str:
    """
    Builds a target string by combining current and new targets, optionally with a library.
    """
    if not current_target:
        return f"{new_target}:{extra_info}" if extra_info else new_target
    return f"{current_target},{new_target}:{extra_info}" if extra_info else f"{current_target},{new_target}"


def convert_epoch_time_to_emby_time_string(epoch_time: int) -> str:
    """ Convert an epoch time to a compatible Emby time string """
    date_time: datetime = datetime.fromtimestamp(epoch_time)
    return f"{date_time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:23]}Z"


def get_short_path(path: str) -> str:
    """ Get the folder name from the path """
    last_index = path.rfind("/")
    if last_index != -1:
        short_path = path[last_index + 1:]

        # Check if Season is in the folder name and the length is less then Season ## as an example
        if short_path.find("Season") != -1 and len(short_path) < 10:
            season_last_index = path.rfind("/", 0, last_index)
            if season_last_index != -1:
                return path[season_last_index + 1:]
        else:
            return short_path
    return path


def get_comma_separated_list(list_to_separate: list[str]) -> str:
    """ Get a comma separated string from a list """
    return ",".join(list_to_separate)
