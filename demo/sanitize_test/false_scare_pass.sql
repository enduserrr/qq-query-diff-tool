SELECT
  timestamp::TIMESTAMP AS "time",
  price::NUMERIC AS "Price",
  'price_drop' AS event_type,
  FALSE AS is_deleted,
  TRUE AS needs_update
FROM 
  subnet_price_test
WHERE 
  subnet_id::BIGINT = 3
  AND timestamp::TIMESTAMP >= NOW() - INTERVAL '7 days'
ORDER BY 
  "time" ASC;
