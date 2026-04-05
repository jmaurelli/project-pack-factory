## FireFlow internals map

Scope stayed observe-only. No appliance state was changed outside the delegated bundle.

### What owns the FireFlow routes

- Core legacy FireFlow UI is owned by Apache `mod_perl` and Mason in `/etc/httpd/conf.d/fireflow.conf`.
- `/FireFlow` is handled by `RT::Mason` with `PerlRequire /usr/share/fireflow/local/bin/webmux.pl`.
- `/WebServices` is separate and runs through `ModPerl::Registry`.
- HTTPS canonicalization for `/FireFlow` and `/FireFlow/NewTicket` is in the FireFlow block inside `/etc/httpd/conf.d/ssl.conf`.
- Newer AFF APIs are not served by Mason. `/FireFlow/api` proxies to `http://localhost:1989/aff/api/external` and `/aff/api` proxies to `http://localhost:1989/aff/api` from `/etc/httpd/conf.d/aff.conf`.
- Apache also fronts newer `algosec-ms.*` services. Example: `ms-batch-application` proxies to `127.0.0.1:8159`, `ms-configuration` to `127.0.0.1:8185`, and host-based `ms-cloudflow-broker` traffic to `127.0.0.1:8111`.

### Service chain and first-pass checkpoints

- `aff-boot.service` is minimal: `After=postgresql.service`, `User=afa`, `ExecStart=/usr/share/aff/lib/aff-boot.jar`.
- No direct dependency on `activemq.service` appears in `aff-boot.service`.
- Current runtime state is:
  - `postgresql`, `aff-boot`, `activemq`, `httpd`: `active`
  - `ms-cloudflow-broker`: `inactive`
- Boot evidence from `/var/log/boot.log-20260308` shows `postgresql` started before `aff-boot`, then `activemq`, then `httpd`.
- PostgreSQL has an AlgoSec-specific pre-start hook in `/usr/lib/systemd/system/postgresql.service`:
  - `ExecStartPre=/usr/share/algosec_appliance/pgsql-dynamic-conf.sh postgresql_conf`
- The generated dynamic DB tuning file is `/data/pgsql/15/data/postgresql_dynamic.conf`.

### Closest readable dependencies

- PostgreSQL is the nearest hard dependency for `aff-boot` based on unit ordering and boot sequence.
- ActiveMQ is clearly used by at least some microservices:
  - `ms-configuration.log` shows ActiveMQ config broadcasts on `config.topic0`.
  - `ms-batch-application.log` shows successful ActiveMQ connections to `ssl://localhost:61616`.
- `ms-batch-application.log` also shows PostgreSQL schema failures such as missing relations like `batch_job_instance` and `batch_step_execution_context`.
- `ms-cloudflow-broker.properties` points back to the local appliance over HTTPS (`asms.public.url=localhost`, port `443`) and mentions Kafka queue settings, but the broker unit is not required for the core FireFlow Apache and `aff-boot` path observed here.

### Useful log families

First-pass:

- `/var/log/boot.log*` for startup order and immediate service failures.
- `/data/pgsql/15/data/pg_log/postgresql-*.log` for DB availability and startup/runtime errors.
- `/data/algosec-ms/logs/ms-configuration.log` for config propagation and ActiveMQ-related config events.
- `/data/algosec-ms/logs/ms-batch-application.log` when UI symptoms overlap background job failures or schema issues.
- `/var/log/fireflow-install.log` for install-era ownership/layout details and first-install assumptions.

Later/supporting:

- Other `/data/algosec-ms/logs/*.log` files for service-specific fallout after core route, Apache, and DB checks pass.
- `ms-cloudflow-broker` route and service only when cloudflow-specific or broker-specific symptoms are present.

### When ActiveMQ stays secondary vs becomes primary

- Keep ActiveMQ secondary when the immediate symptom is basic FireFlow page load, `/FireFlow` routing, Apache SSL rewrite behavior, or `aff-boot` availability, because the directly observed core path is Apache -> FireFlow/AFF -> PostgreSQL.
- Promote ActiveMQ earlier when symptoms are asynchronous or configuration-propagation oriented:
  - microservices fail after core UI is reachable
  - logs show broker reconnect/failover errors
  - `ms-configuration` stops receiving or broadcasting config events
  - batch/background functions fail after DB and Apache checks already pass
- Promote `ms-cloudflow-broker` specifically only for cloudflow-related workflows or if Apache host-based broker routing is implicated; it is currently inactive while core services are active, so it does not look like a first-pass blocker for generic FireFlow access.

### Gaps

- Referenced baseline summary path `.pack-state/autonomy-runs/adf-autonomy-baseline-catch-up-checkpoint-v1/run-summary.json` was not present.
- I did not inspect paths outside the delegated scope, so I did not read any FireFlow-owned logs under `/usr/share/fireflow/...`.
