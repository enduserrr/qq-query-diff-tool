-- NEW version of the monthly revenue query
-- (renamed column, rounded+cast total, excludes Globex, no ORDER BY)
SELECT customer,
       round(sum(amount))::int AS total,
       count(*) AS n
FROM orders
WHERE status = 'paid' AND customer <> 'Globex'
GROUP BY customer;
