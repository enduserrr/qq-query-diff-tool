SELECT
  DATE_TRUNC('day', timestamp::TIMESTAMP) AS "time",
  AVG(price::NUMERIC) AS "Price"
FROM 
  subnet_price_test
WHERE 
  subnet_id::BIGINT = 3
  AND timestamp::TIMESTAMP >= NOW() - INTERVAL '7 days'
GROUP BY 
  1
ORDER BY 
  1 ASC;