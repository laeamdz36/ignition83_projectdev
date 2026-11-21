SELECT *
FROM rcms_tokens_hist
WHERE created_at >= :start_date AND created_at < :end_date