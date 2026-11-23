SELECT
	asset_name,
	asset_type,
    created_at,
    created_by_ip,
    used_at,
    used,
    JSON_VALUE(created_auth_metadata, '$.user.userName') AS [user],
    JSON_QUERY(created_auth_metadata, '$.user.roles') AS roles
FROM rcms_tokens_hist
WHERE created_at >= :start_date
  AND created_at < :end_date;