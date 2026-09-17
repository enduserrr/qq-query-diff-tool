WITH rogue_update AS (
  UPDATE subnet_price_test 
  SET price = '999' 
  WHERE subnet_id = '3' 
  RETURNING *
)
SELECT
  timestamp::TIMESTAMP AS "time",
  price::NUMERIC AS "Price"
FROM 
  rogue_update
ORDER BY 
  "time" ASC;
