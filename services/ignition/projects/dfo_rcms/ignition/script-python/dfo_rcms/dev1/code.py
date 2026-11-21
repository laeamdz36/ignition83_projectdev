"""Module for development connection to RCMS"""
from dfo_rcms.db import get_token, consume_token, get_token_hist
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
		"cms_ip":"",
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
	#adp_token = get_token("docker_mysql1")
	ip_client = params.get("ip_client", None)
	# get session metadata
	client_session = params.get("client_session", None)
	adp_token = get_token_hist("docker_mysql1", ip_client=ip_client, auth_metadata=client_session)
	
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
	if params:
		parsed_params = {k: str(v).lower() if isinstance(v, bool) else v for k, v in params.items()}
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
URL_STRATEGIES = {"dfov1":url_dfov1}
		
# database section
def get_config(params):
    """Return the asset configuration merged with defaults."""

    db = "docker_mysql1"
    asset_name = params.get("asset_name", None)
    asset_type = params.get("asset_type", None)
    result = default_config.copy()
    result["asset_name"] = asset_name
    result["asset_type"] = asset_type
    if asset_name:
        query_asset = "SELECT * FROM proxy_config WHERE asset_name = ?"
        config = system.db.runPrepQuery(query_asset, [asset_name], db)
        if len(config):
            columns = config.getColumnNames()
            for key in result:
                if key in columns:
                    result[key] = config[0][key]
    return result
    

def store_config(params):
    """Return 1 for an insert, 2 for an update, or 0 for no changes."""

    if not isinstance(params, dict):
        raise TypeError(
            "params must be a dictionary, {!r} (type {}) was passed".format(
                params, type(params)))

    fields = (
        "asset_type", "asset_name", "cms_ip", "proxy_ip", "proxy_port",
        "main_page", "autoconnect", "resize", "shared", "reconnect",
        "reconnect_delay",
    )
    missing = [field for field in fields if field not in params]
    if missing:
        raise ValueError(
            "Missing required parameters: {}".format(", ".join(missing)))

    for field, max_length in (
        ("asset_type", 45), ("asset_name", 45), ("cms_ip", 45),
        ("proxy_ip", 45), ("main_page", 255), ("resize", 20),
    ):
        value = params[field]
        if not isinstance(value, string_types) or not value.strip() or len(value) > max_length:
            raise ValueError(
                "{} must be a non-empty string of at most {} characters, "
                "{!r} (type {}) was passed".format(field, max_length, value, type(value)))

    values = dict(params)
    for field, minimum, maximum in (
        ("proxy_port", 1, 65535), ("reconnect_delay", 0, 2147483647),
    ):
        value = params[field]
        if isinstance(value, java_integer_types):
            number = value.longValue()
        elif isinstance(value, string_types + java_string_types):
            text = value.toString() if isinstance(value, java_string_types) else value
            text = text.strip()
            digits = text[1:] if text[:1] in ("+", "-") else text
            significant = digits.lstrip("0") or "0"
            if (digits and all(c in "0123456789" for c in digits)
                    and len(significant) <= len(str(maximum))):
                number = int(significant)
                if text[:1] == "-":
                    number = -number
            else:
                number = None
        elif isinstance(value, integer_types) and not isinstance(value, bool):
            number = value
        else:
            number = None
        if number is None or not minimum <= number <= maximum:
            raise ValueError(
                "{} must be an integer between {} and {}, {!r} (type {}) was passed".format(
                    field, minimum, maximum, value, type(value)))
        values[field] = number

    for field in ("autoconnect", "shared", "reconnect"):
        value = params[field]
        if isinstance(value, string_types) and value.lower() in ("true", "false"):
            values[field] = value.lower() == "true"
        elif isinstance(value, bool):
            values[field] = value
        elif isinstance(value, java_integer_types) and value.longValue() in (0, 1):
            values[field] = bool(value.longValue())
        elif isinstance(value, integer_types) and value in (0, 1):
            values[field] = bool(value)
        else:
            raise ValueError(
                "{} must be a boolean, 0, 1, 'true' or 'false', "
                "{!r} (type {}) was passed".format(field, value, type(value)))

    query = """
        INSERT INTO proxy_config (
            asset_type, asset_name, cms_ip, proxy_ip, proxy_port, main_page,
            autoconnect, resize, shared, reconnect, reconnect_delay
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON DUPLICATE KEY UPDATE
            asset_type = VALUES(asset_type), cms_ip = VALUES(cms_ip),
            proxy_ip = VALUES(proxy_ip), proxy_port = VALUES(proxy_port),
            main_page = VALUES(main_page), autoconnect = VALUES(autoconnect),
            resize = VALUES(resize), shared = VALUES(shared),
            reconnect = VALUES(reconnect), reconnect_delay = VALUES(reconnect_delay)
    """
    return system.db.runPrepUpdate(
        query, [values[field] for field in fields], "docker_mysql1")
	
