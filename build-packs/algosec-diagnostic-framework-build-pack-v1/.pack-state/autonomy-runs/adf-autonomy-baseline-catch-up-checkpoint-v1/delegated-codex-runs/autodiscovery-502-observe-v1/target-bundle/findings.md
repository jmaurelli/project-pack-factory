AutoDiscovery observation completed without changing appliance state.

Key findings:

- Apache route ownership is defined in `algosec-ms.ms-autodiscovery.conf`. `/ms-autodiscovery` proxies directly to `http://127.0.0.1:8095`, while `/AutoDiscovery` proxies to `https://AutoDiscovery/ms-autodiscovery`, and `/ms-autodiscovery/*` is redirected to `/AutoDiscovery/*` when `X-Forwarded-For` is empty.
- `ms-autodiscovery.service` is loaded but inactive/dead and disabled. `ms-configuration.service` is active/running.
- Nothing is listening on TCP `8095` at observation time.
- Direct backend check to `http://127.0.0.1:8095/v2/api-docs` fails with `Connection refused`.
- Apache-facing check to `https://127.0.0.1/AutoDiscovery/v2/api-docs` returns `HTTP/1.1 502 Proxy Error` with `Reason: DNS lookup failure for: autodiscovery`.
- Apache-facing check to `https://127.0.0.1/ms-autodiscovery/v2/api-docs` returns `301 Moved Permanently` to `/AutoDiscovery/v2/api-docs`, confirming the alias path is redirected into the failing `/AutoDiscovery` route.
- `ssl_access_log` shows repeated `502` responses for `/AutoDiscovery/v2/api-docs` on March 25-26, 2026. `ssl_error_log` shows repeated `AH00898: DNS lookup failure for: autodiscovery returned by /AutoDiscovery/v2/api-docs`.

Operator readout:

The observed `502` is reproducible and the pathing is clear. There appear to be two independent faults in the AutoDiscovery chain:

1. Apache's `/AutoDiscovery` ProxyPass target depends on resolving `AutoDiscovery` as a hostname and currently fails DNS resolution.
2. The final backend target behind `/ms-autodiscovery` is also unavailable because `ms-autodiscovery.service` is dead and port `8095` has no listener.

Artifacts of interest:

- `artifacts/apache-autodiscovery-conf.txt`
- `artifacts/ms-autodiscovery-service.txt`
- `artifacts/ms-configuration-service.txt`
- `artifacts/ms-autodiscovery-show.txt`
- `artifacts/ms-configuration-show.txt`
- `artifacts/port-8095.txt`
- `artifacts/autodiscovery-http-checks.txt`
- `artifacts/httpd-log-snippets.txt`
- `artifacts/ssl_error_log-tail.txt`
- `artifacts/ssl_error_log-matches.txt`
