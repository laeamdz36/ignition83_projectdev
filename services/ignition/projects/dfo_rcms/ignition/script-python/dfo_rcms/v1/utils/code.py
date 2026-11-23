"""Utils for rcms project"""
import re

def get_asset_prefix(tag_name):
	    # Busca una o más letras al inicio de la cadena
	    match = re.match(r'^([A-Za-z]+)', tag_name)
	    return match.group(1) if match else None