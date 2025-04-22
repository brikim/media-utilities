import logging
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


def get_log_ansi_code() -> str:
    """Get assigned log ANSI code."""
    return ANSI_CODE_LOG


def get_tag_ansi_code() -> str:
    """Get assigned tag ANSI code."""
    return ANSI_CODE_TAG


def get_plex_ansi_code() -> str:
    """Get assigned Plex ANSI code."""
    return ANSI_CODE_PLEX


def get_tautulli_ansi_code() -> str:
    """Get assigned Tautulli ANSI code."""
    return ANSI_CODE_TAUTULLI


def get_emby_ansi_code() -> str:
    """Get assigned Emby ANSI code."""
    return ANSI_CODE_EMBY


def get_jellystat_ansi_code() -> str:
    """Get assigned Jellystat ANSI code."""
    return ANSI_CODE_JELLYSTAT


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


def get_hours_since_play(
    use_utc_time: bool,
    play_date_time: datetime
) -> int:
    """ Get the hours since a play based on a time string """
    current_date_time = datetime.now(
        timezone.utc) if use_utc_time else datetime.now()
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


def get_cron_from_string(
    cron_string: str,
    logger: logging,
    module_name: str
) -> CronInfo:
    """ Get a CronInfo from a string """
    cron_params = cron_string.split()
    if len(cron_params) >= 2 and len(cron_params) <= 5:
        return CronInfo(cron_params[1], cron_params[0])
    else:
        logger.error(
            f"{module_name}: Invalid Cron Expression {cron_string}"
        )
    return None


def remove_ansi_code_from_text(text: str) -> str:
    """Removes ANSI escape codes from a string."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


def build_target_string(current_target: str, new_target: str, extra_info: str) -> str:
    """
    Builds a target string by combining current and new targets, optionally with a library.
    """
    if not current_target:
        return f"{new_target}:{extra_info}" if extra_info else new_target
    return f"{current_target},{new_target}:{extra_info}" if extra_info else f"{current_target},{new_target}"
