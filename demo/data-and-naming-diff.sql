SELECT
  timestamp::TIMESTAMP AS "time",
  price::FLOAT AS "price" -- Lowercase alias and FLOAT type
FROM 
  subnet_price_test
WHERE 
  subnet_id::BIGINT = 3
  AND timestamp::TIMESTAMP >= NOW() - INTERVAL '7 days'
ORDER BY 
  "time" DESC; -- Reversed order