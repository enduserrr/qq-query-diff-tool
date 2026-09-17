WITH deleted_data AS (
  DELETE FROM subnet_price_test
  RETURNING *
)
SELECT
  timestamp::TIMESTAMP AS "time",
  price::NUMERIC AS "Price"
FROM 
  deleted_data
WHERE 
  subnet_id::BIGINT = 3
  AND timestamp::TIMESTAMP >= NOW() - INTERVAL '7 days'
ORDER BY 
  "time" ASC;
