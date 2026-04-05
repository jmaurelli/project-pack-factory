Observed branch: `POST /FireFlow/FireFlowAffApi/NoAuth/CommandsDispatcher` around `2026-03-21 04:30 EDT`.

What the minute shows:
- `04:30:23` Apache and `aff-boot` line up on `POST /aff/api/internal/journal/updateLastChanges`, followed immediately by `GET /afa/external/journal/getChangesInOrigRulesByDate`.
- `04:30:43-04:30:44` the follow-on `CommandsDispatcher` calls line up with `GET /aff/api/external/session`, `POST /afa/external//session/extend`, health checks, and repeated FireFlow session fetches.
- PostgreSQL at `04:30:22` only shows three `rt_user@rt3` client disconnects (`could not receive data from client: Connection reset by peer`), not query errors or a distinct async handoff.
- No same-minute hits were found in `ms-configuration.log` or `ms-batch-application.log`.
- ActiveMQ has persistent stores for `queue://aff.job`, `queue://config.topic`, and `topic://DistributedMethodExecutionQueue`, but there is no same-minute broker log or audit evidence tying this branch to those destinations.

Interpretation:
- This branch is best classified as synchronous journal/session maintenance, not a FireFlow submit/advance/approval path.
- The likely mapping of response-size patterns is an inference from the matching `2026-03-26` FireFlow runtime cadence: `3055` aligns with journal refresh and `3070` aligns with `UserSession:getUserSession`.
- Based on the evidence in scope, ActiveMQ should not be promoted earlier for this specific branch. Journal/session correlation belongs ahead of broker inspection here.

Artifacts:
- `artifacts/httpd-2026-03-21-0430-snippet.txt`
- `artifacts/aff-boot-2026-03-21-0430-snippet.txt`
- `artifacts/postgresql-sat-0430-snippet.txt`
- `artifacts/fireflow-2026-03-26-analogy-snippet.txt`
- `artifacts/activemq-store-evidence.txt`
