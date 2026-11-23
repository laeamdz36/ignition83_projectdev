SELECT
	asset_name,
	asset_type,
    token,
    created_at,
    created_by_ip,
    used_at,
    used,
    JSON_UNQUOTE(JSON_EXTRACT(created_auth_metadata, '$.idp')) AS idp,
    JSON_UNQUOTE(JSON_EXTRACT(created_auth_metadata, '$.user.userName')) AS user,
    JSON_EXTRACT(created_auth_metadata, '$.user.roles') AS roles
FROM rcms_tokens_hist
WHERE created_at >= :start_date AND created_at < :end_date;