def doGet(request, session):
    logger = system.util.getLogger("rcms")
    params = request["params"]
    token = params.get("adp")
    logger.info("Request token: %s" % (token))

    if token:
        request_ip = request["remoteAddr"]
        logger.info("Request - Token validation request %s" %
                    request_ip)
        try:
        	# consume_token_hist(token_str, db_connection="", remote_ip=None)
            if dfo_rcms.db.consume_token_hist(
                    token, db_connection="docker_mysql1", remote_ip=request_ip) == 1:
                return {"json": {
                    "success": True,
                    "validation": 1,
                    "id": 1
                }}

        except Exception:
            request["servletResponse"].setStatus(400)

    return {
        "json": {
            "success": False,
            "error": {
                "code": "MISSING_PARAMETER",
                "message": "valid adp token is required"
            }
        }
    }