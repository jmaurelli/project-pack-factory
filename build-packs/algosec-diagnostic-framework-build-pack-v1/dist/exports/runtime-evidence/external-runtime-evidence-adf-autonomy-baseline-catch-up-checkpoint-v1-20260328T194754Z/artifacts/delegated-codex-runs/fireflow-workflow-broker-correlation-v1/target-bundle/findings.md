# FireFlow Correlation Findings

Selected minute: `2026-03-26 19:40 EDT` with follow-on evidence at `19:41:15 EDT`.

Why this minute:
- It is later than the login/bootstrap handoff.
- Apache shows a FireFlow `CommandsDispatcher` call paired with AFF journal/config reads at `19:40:39`.
- The next notable backend signal is `ms-configuration` rebuilding unified swagger at `19:41:14` and failing `AutoDiscovery` at `19:41:15`.

Evidence summary:
- Apache access at `19:40:39` shows:
  - `POST /FireFlow/FireFlowAffApi/NoAuth/CommandsDispatcher`
  - `GET /afa/external/journal/getChangesInOrigRulesByDate?...`
  - followed by `GET /FireFlow/api/session` and more dispatcher calls at `19:40:43-19:40:44`
- `ms-configuration.log` at `19:41:14-19:41:15` adds FireFlow into unified swagger and then warns that `AlgoSec_ApplicationDiscovery` returned `502 BAD_GATEWAY`.
- Apache `ssl_error_log` confirms the same `AutoDiscovery` failure at `19:41:15.334461`.
- PostgreSQL does not show a matching failure in the same minute. The closest entries are routine `rt_user` client resets at `19:35:29` and a normal checkpoint completion at `19:37:41`.

Broker decision:
- Do not promote ActiveMQ earlier for this branch.
- Reason: the broker's own `activemq.log` is stale and has no March 26 entries for the FireFlow minute.
- KahaDB file mtimes do move on `2026-03-26`, but the nearest cluster is later at `19:45:10-19:45:28` and points to monitor-oriented destinations such as `algosec.afa.monitor.service.workers.MonitorDataCollectionMessage`, not a clear FireFlow workflow queue.
- That makes this branch still Apache to FireFlow/AFF to configuration-service centered, with broker activity as weak and delayed side evidence rather than a primary dependency for the selected minute.

Recommended playbook note:
- For a FireFlow minute shaped like `CommandsDispatcher + AFF journal/config + unified swagger refresh`, keep Apache and AFF/FireFlow first.
- Check `ms-configuration` next when the minute rolls into `/api-docs` fetches or service definition refresh.
- Only elevate ActiveMQ earlier when broker logs or queue-store mtimes line up in the same minute on workflow-specific destinations rather than monitor/config topics.
