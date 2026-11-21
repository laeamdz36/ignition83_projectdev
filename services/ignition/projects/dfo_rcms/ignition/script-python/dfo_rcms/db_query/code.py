"""Query definition to different databases"""
from abc import ABCMeta, abstractmethod


class ServiceDb(object):
	"""Interafce for storage configuration"""
	__metaclass__ = ABCMeta
	
	@abstractmethod
	def store():
		# type: () -> str
		"""implement the concrete storage service"""
		raise NotImplementedError("Subclass need to implement specific storage strategy")
		
		

class StoreMySql(ServiceDb):
	"""Concrete storage service for mysql database"""
		
	def store(self, params):
		"""Store configuration and return the number of affected rows."""
		
		qparams = self.retrieve_params(params)
		query = """
		    INSERT INTO proxy_config (
		        ip_proxy, port, index_page, adp_token,
		        autoconnect, resize, shared, reconnect
		    )
		    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
		"""
		return execute_non_query(
		    query, database=self.database, params=self.retrieve_params(params)
		)

	def retrieve_params(self, params):
		"""Validate a configuration dictionary and order its SQL parameters."""
		if not isinstance(params, dict):
			raise TypeError("params must be a dictionary")
		
		required = (
		"ip_proxy", "port", "index_page", "autoconnect",
		"resize", "shared", "reconnect",
		)
		missing = [name for name in required if name not in params]
		if missing:
			raise ValueError(
		"Missing required parameters: {}".format(", ".join(missing)))
		
		for name in ("ip_proxy", "index_page", "resize"):
			if not isinstance(params[name], string_types) or not params[name].strip():
				raise ValueError("{} must be a non-empty string".format(name))
		
		port = params["port"]
		if isinstance(port, bool) or not isinstance(port, integer_types) or not 1 <= port <= 65535:
			raise ValueError("port must be an integer between 1 and 65535")
		
		token = params.get("adp_token")
		if token is not None and not isinstance(token, string_types):
			raise ValueError("adp_token must be a string or None")
		
		for name in ("autoconnect", "shared", "reconnect"):
			if not isinstance(params[name], bool):
				raise ValueError("{} must be a boolean".format(name))
		
		return [
		params["ip_proxy"], port, params["index_page"], token,
		params["autoconnect"], params["resize"], params["shared"],
		params["reconnect"],
		]
		

def store_config():
	"""Store configuration for asset"""
	pass