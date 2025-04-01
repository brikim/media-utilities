import requests
import json
from typing import Any
from logging import Logger
from common import utils

class JellystatAPI:
    def __init__(
        self,
        server_name: str,
        url: str,
        api_key: str,
        logger: Logger
    ):
        self.server_name = server_name
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.logger = logger
        self.invalid_type = None
        self.log_header = utils.get_log_header(
            utils.get_jellystat_ansi_code(),
            self.__module__
        )
        
    def get_server_name(self) -> str:
        return self.server_name
    
    def get_valid(self) -> bool:
        try:
            payload = {}
            r = requests.get(
                f"{self.get_api_url()}/getconfig",
                headers=self.get_headers(),
                params=payload,
                timeout=5
            )
            if r.status_code < 300:
                return True
        except Exception:
            pass
        return False

    def get_connection_error_log(self) -> str:
        return f"Could not connect to {utils.get_formatted_jellystat()}:{self.server_name} {utils.get_tag("url", self.url)} {utils.get_tag("api_key", self.api_key)}"
    
    def get_invalid_type(self) -> Any:
        return self.invalid_type
    
    def get_api_url(self) -> str:
        return f"{self.url}/api"
    
    def get_headers(self) -> Any:
        return {"x-api-token": self.api_key,
                "Content-Type": "application/json"}
        
    def get_library_id(self, libName: str) -> str:
        try:
            payload = {}
            r = requests.get(
                f"{self.get_api_url()}/getLibraries",
                headers=self.get_headers(),
                params=payload,
                timeout=5
            )
            response = r.json()
            for lib in response:
                if lib["Name"] == libName:
                    return lib["Id"]
        except Exception as e:
            self.logger.error(
                f"{self.log_header} get_library_id {utils.get_tag("library_id", libName)} {utils.get_tag("error", e)}"
            )
            
        return self.get_invalid_type()
        
    def get_user_watch_history(self, userId: str) -> Any:
        try:
            payload = {
                "userid": userId
            }
            r = requests.post(
                f"{self.get_api_url()}/getUserHistory",
                headers=self.get_headers(),
                data=json.dumps(payload),
                timeout=5
            )
            
            response = r.json()
            if "results" in response:
                return response["results"]
            else:
                return response
        except Exception as e:
            self.logger.error(
                f"{self.log_header} get_user_watch_history {utils.get_tag("user_id", userId)} {utils.get_tag("error", e)}"
            )
        
        return self.get_invalid_type()
            
    def get_library_history(self, libId: str) -> Any:
        try:
            payload = {
                "libraryid": libId
            }
            r = requests.post(
                f"{self.get_api_url()}/getLibraryHistory",
                headers=self.get_headers(),
                data=json.dumps(payload),
                timeout=5
            )
            
            response = r.json()
            if "results" in response:
                return response["results"]
            else:
                return response
        except Exception as e:
            self.logger.error(
                f"{self.log_header} get_library_history {utils.get_tag("lib_id", libId)} {utils.get_tag("error", e)}"
            )
        
        return self.get_invalid_type()
    
    def get_item_details(self, itemId: str) -> Any:
        try:
            payload = {"Id": itemId}
            r = requests.post(
                f"{self.get_api_url()}/getItemDetails",
                headers=self.get_headers(),
                data=json.dumps(payload),
                timeout=5
            )
            return r.json()
        except Exception as e:
            self.logger.error(
                f"{self.log_header} get_item_details {utils.get_tag("item", itemId)} {utils.get_tag("error", e)}"
            )
            
        return self.get_invalid_type()
