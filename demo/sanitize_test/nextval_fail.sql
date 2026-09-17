SELECT
  timestamp::TIMESTAMP AS "time",
  price::NUMERIC AS "Price",
  nextval('some_random_sequence') AS skipped_id
FROM 
  subnet_price_test
WHERE 
  subnet_id::BIGINT = 3
  AND timestamp::TIMESTAMP >= NOW() - INTERVAL '7 days'
ORDER BY 
  "time" ASC;
