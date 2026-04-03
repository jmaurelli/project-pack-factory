# ADF Successor Shallow Surface Summary

## Scope

- Target: 10.167.2.150
- Hostname: algosec
- Components recorded: 351
- ASMS doc-pack hints: loaded from `dist/candidates/adf-docpack-hints/asms-docpack-hints.json`
- ASMS doc-pack version: asms-A33.10-docpack-v1 A33.10

The doc-pack hint layer only informs naming, port-based hints, and prioritization. Live runtime evidence remains the source of truth for what is running here.

## What Appears To Be Running

- `algosec-ms`: application_service (confidence medium, ports 8185) Doc-pack hints: matched terms afa, algosec
- `ms-metro`: application_service (confidence medium, ports 5701, 8080, 8082) Doc-pack hints: matched terms afa; matched ports 8082
- `syslog`: application_service (confidence medium, ports 22) Doc-pack hints: matched terms afa, algosec
- `elasticsearch`: application_service (confidence low, ports 1989, 5701, 8080, 8081, 8082, 8083, 8086, 8087, 8093, 8096, 8097, 8104, 8132, 8134, 8136, 8138, 8157, 8159, 8174, 8183, 8185, 9200, 9300, 9600, 61616) Doc-pack hints: matched ports 8082
- `httpd`: edge_proxy (confidence high, ports 80, 443)

## Edge-To-Local Route Hints

- `(route path not explicit)` via `RewriteRule` in `/etc/httpd/conf.d/algosec-ms.ms-bflow.conf:3` points toward `http://127.0.0.1:8081/BusinessFlow/$1`; likely owner `ms-bflow` (listener port 8081 matches exact PID ownership).
- `/BusinessFlow` via `ProxyPass` in `/etc/httpd/conf.d/algosec-ms.ms-bflow.conf:12` points toward `http://127.0.0.1:8081/BusinessFlow`; likely owner `ms-bflow` (listener port 8081 matches exact PID ownership).
- `/BusinessFlow` via `ProxyPassReverse` in `/etc/httpd/conf.d/algosec-ms.ms-bflow.conf:13` points toward `http://127.0.0.1:8081/BusinessFlow`; likely owner `ms-bflow` (listener port 8081 matches exact PID ownership).
- `(route path not explicit)` via `RewriteRule` in `/etc/httpd/conf.d/algosec-ms.ms-configuration.conf:3` points toward `http://127.0.0.1:8185/$1`; likely owner `algosec-ms` (listener port 8185 matches exact PID ownership).
- `(route path not explicit)` via `RewriteRule` in `/etc/httpd/conf.d/algosec-ms.ms-metro.conf:3` points toward `http://127.0.0.1:8080/afa/$1`; likely owner `ms-metro` (listener port 8080 matches exact PID ownership).

## Visible Unknowns

- The first pass does not yet parse config files, unit fragments, or logs.
- The first pass does not claim complete dependency order or request-path ownership.
- The first pass keeps product labeling bounded; some components may still be generic or misclassified.

## Next Candidate Seams

- `trace_edge_to_local_service_routes`: Apache route hints now expose candidate local handoffs, so the next bounded pass can confirm which service owns each browser-facing route. Starting points: ms-bflow, algosec-ms, ms-metro.
- `inspect_java_runtime_clusters`: Java-adjacent components are visible but their role boundaries are still tentative. Starting points: algosec-ms, ms-metro, syslog.

