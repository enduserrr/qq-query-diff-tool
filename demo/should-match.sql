/* 
   This looks completely different but evaluates to the exact same 
   rows, columns, and data types as the base query.
*/
WITH formatted_data AS (
    SELECT * FROM (
        SELECT 
            CAST(timestamp AS TIMESTAMP) AS "time", 
            CAST(price AS NUMERIC) AS "Price",
            CAST(subnet_id AS BIGINT) AS sid
        FROM 
            subnet_price_test
    ) sub
    WHERE 
        sid = ABS(-3) -- mathematically exactly 3
)
SELECT 
    "time", 
    "Price" 
FROM 
    formatted_data 
WHERE 
    "time" >= (CURRENT_TIMESTAMP - CAST('168 hours' AS INTERVAL)) -- 168 hours = 7 days
ORDER BY 
    1 ASC; -- Ordering by the first column positionally
