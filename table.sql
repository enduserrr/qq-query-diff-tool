

-- one row per logical test run with the aggregate verdict you actually query
create or replace view qq_run as
select
  run_id,
  surface,
  min(created_on)                     as started_on,
  max(created_on)                     as finished_on,
  count(*)                            as total_subnets,
  count(*) filter (where is_identical) as pass_count,
  count(*) filter (where not is_identical) as fail_count,
  bool_and(is_identical)              as is_identical
from qq_result
group by run_id, surface;

-- one row per qq.py invocation (one per subnet when a test spans 1..128)
create table if not exists qq_result (
  run_id       bigint not null,        -- groups the 128 subnet rows of a single test run
  surface      text not null,          -- 'drilldown' | 'overview' | 'tables' | 'views' | ...
  subnet_id    bigint not null,
  json         jsonb not null,         -- {a_sql, b_sql, qq_output, timing_a_s, timing_b_s, cells_same, rows_missing_a, rows_missing_b}
  is_identical boolean not null,
  created_on   timestamp not null default now(),
  primary key (run_id, subnet_id)
);