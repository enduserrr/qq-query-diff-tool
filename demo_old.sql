-- OLD version of the monthly revenue query
SELECT customer AS cust,
       sum(amount) AS total,
       count(*) AS n
FROM orders
WHERE status = 'paid'
GROUP BY customer
ORDER BY cust;
