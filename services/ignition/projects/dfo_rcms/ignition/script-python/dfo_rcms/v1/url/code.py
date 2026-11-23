"""Module for development connection to RCMS"""
from dfo_rcms.v1.db import (
    get_token,
    consume_token,
    get_token_hist)
from dfo_rcms.v1.settings import *
# http://192.168.10.115:6080/remote.html?&adp=9ad2904a-482a-43ed-8787-18f136be3323&repeaterID=1001&autoconnect=true&resize=scale&shared=true&reconnect=true&reconnect_delay=5000

# for type validations
try:
    string_types = (basestring,)
    integer_types = (int, long)
except NameError:
    string_types = (str,)
    integer_types = (int,)

try:
    from java.lang import Byte, Integer, Long, Short, String
    java_integer_types = (Byte, Short, Integer, Long)
    java_string_types = (String,)
except ImportError:
    java_integer_types = ()
    java_string_types = ()

# config defaults
default_config = {
    "cms_ip": "",
    "proxy_ip": "",
                "proxy_port": None,
                "main_page": "",
                "autoconnect": "",
                "resize": "",
                "shared": "",
                "reconnect": "",
                "reconnect_delay": None
}


def url_dfov1(params=None):
    """Concrete strategy for url generator dfo, proxy v3"""

    # url = "http://{}:{}/{}?&adp={}&autoconnect={}&resize={}&shared={}&reconnect={}&reconnect_delay={}"
    # generate token
    config_retrieval = get_config(params)
    
    ip_client = params.get("ip_client", None)
    # get session metadata
    client_session = params.get("client_session", None)
    
    adp_token = get_token_hist(
        db_connection=DB, params=params)
        

    # generate url according proxy websockify and novnc requirements
    config = {
        "proxy_ip": "127.0.0.1",
        "proxy_port": 6080,
        "main_page": "remote.html",
        "adp_token": adp_token,
        "autoconnect": "true",
        "resize": "scale",
        "shared": "true",
        "reconnect": "true",
        "reconnect_delay": 5000
    }

    # extract parameters for url creation and convert booleans to lowercase strings
    
    if config_retrieval:
        parsed_params = {k: str(v).lower() if isinstance(
            v, bool) else v for k, v in config_retrieval.items()}
    config.update(parsed_params)
    url = "http://{proxy_ip}:{proxy_port}/{main_page}?&adp={adp_token}&autoconnect={autoconnect}&resize={resize}&shared={shared}&reconnect={reconnect}&reconnect_delay={reconnect_delay}"

    return url.format(**config)


def get_url(url_type, params):
    """return the url generator"""

    if isinstance(url_type, str):
        url_strategy = URL_STRATEGIES.get(url_type, None)
        if url_strategy is None:
            raise NotImplementedError("Need to specify a valid url type")
    else:
        raise TypeError("url type must be str")
    return url_strategy(params)


# Url strategies
# he is included in the repository the strategy for the generation of different configurations of urls for novnc proxy connection
URL_STRATEGIES = {"dfov1": url_dfov1}

# database section


def get_config(params):
    """Return the asset configuration merged with defaults."""

    db = DB
    asset_name = params.get("asset_name", None)
    asset_type = params.get("asset_type", None)
    result = default_config.copy()
    result["asset_name"] = asset_name
    result["asset_type"] = asset_type
    if asset_name:
        query_asset = "SELECT * FROM {} WHERE asset_name = ?".format(RCMS_CONFIG_TABLE)
        config = system.db.runPrepQuery(query_asset, [asset_name], db)
        if len(config):
            columns = config.getColumnNames()
            for key in result:
                if key in columns:
                    result[key] = config[0][key]
    return result