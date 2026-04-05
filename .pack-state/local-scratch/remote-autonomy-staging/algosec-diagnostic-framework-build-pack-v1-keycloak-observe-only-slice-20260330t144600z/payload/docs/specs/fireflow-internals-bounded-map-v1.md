# FireFlow Internals Bounded Map v1

Date: 2026-03-26

## Purpose

Capture the deeper FireFlow-internals model that sits behind the current
first-pass playbook, without widening the scope into every later FireFlow
workflow branch.

This note should answer:

- what the closest readable FireFlow checkpoints are
- what the closest dependencies are behind those checkpoints
- what should stay first-pass versus later supporting
- when ActiveMQ should remain secondary and when it would deserve promotion

## Current Working Model

The current accepted model is:

- Apache owns two distinct FireFlow-facing surfaces:
  - classic `/FireFlow` through `mod_perl` and Mason in `fireflow.conf`
  - newer `/FireFlow/api` and `/aff/api` through Apache proxying into
    `aff-boot` on `1989` in `aff.conf`
- `aff-boot` is the core first-pass backend service behind the newer FireFlow
  API surfaces
- PostgreSQL is the nearest hard readable dependency behind `aff-boot`
- ActiveMQ is real and active, but stays later-supporting unless the symptom is
  asynchronous or configuration-propagation oriented
- newer `algosec-ms.*` routes such as `ms-configuration`,
  `ms-batch-application`, and `ms-cloudflow-broker` should be treated as
  neighboring microservice surfaces, not as the same thing as the classic
  FireFlow route itself

## First-Pass Checkpoints

- Apache route ownership:
  - `fireflow.conf` for the classic `/FireFlow` Mason path
  - `aff.conf` for `/FireFlow/api` -> `http://localhost:1989/aff/api/external`
    and `/aff/api` -> `http://localhost:1989/aff/api`
- `httpd` state and route availability
- `aff-boot.service` state and recent runtime health
- `postgresql.service` state, startup ordering, and PostgreSQL log health

## Closest Dependencies

- `postgresql.service`
  - `aff-boot.service` explicitly starts `After=postgresql.service`
  - boot sequencing observed `postgresql` before `aff-boot`
  - PostgreSQL also has an AlgoSec-specific pre-start tuning hook
- `aff-boot`
  - minimal service wrapper around `/usr/share/aff/lib/aff-boot.jar`
  - the first readable backend seam behind newer FireFlow APIs
- Apache route ownership
  - still part of the close dependency story because the operator-visible path
    reaches FireFlow through Apache first

## Later-Supporting Dependencies

- `activemq.service`
  - active and clearly used by some microservices
  - does not appear as a direct unit dependency for `aff-boot.service`
- `ms-configuration`
  - useful when config propagation or ActiveMQ-backed config events are in
    scope
- `ms-batch-application`
  - useful when background jobs, schema issues, or post-entry workflow failures
    are implicated
- `ms-cloudflow-broker`
  - currently inactive while core FireFlow services are active
  - should not be treated as a first-pass blocker for generic FireFlow access

## Promotion Rule For ActiveMQ

Keep ActiveMQ secondary when the symptom is basic FireFlow page load, Apache
rewrite behavior, `/FireFlow/api` or `/aff/api` routing, or `aff-boot`
availability.

Promote ActiveMQ earlier only when:

- core UI is already reachable
- the remaining symptom is asynchronous, broker-like, or configuration-driven
- logs show broker reconnect, failover, or config-broadcast trouble
- `ms-configuration` or related services stop exchanging expected broker-backed
  events

Promote `ms-cloudflow-broker` specifically only for cloudflow-oriented flows or
when its host-based Apache route is directly implicated.

## Latest Live Follow-Up

The current accepted local evidence already suggests:

- FireFlow should stay later than the first top-level ASMS gate
- Apache route ownership and `aff-boot` service state are the first readable
  checkpoints
- PostgreSQL is a closer runtime dependency than ActiveMQ for first-pass
  support work

The accepted delegated slice `fireflow-internals-map-v1` sharpened that model
with direct target-backed evidence:

- `aff-boot.service` is minimal and explicitly ordered after PostgreSQL
- `aff.conf` proves the newer FireFlow API surfaces proxy through `1989`
- classic FireFlow still has its own Apache/Mason ownership in `fireflow.conf`
- `ms-configuration.log` shows ActiveMQ-backed config events
- `ms-batch-application.log` shows PostgreSQL schema failures and successful
  ActiveMQ connections, which makes it a useful later-supporting diagnostic
  surface
- `ms-cloudflow-broker` is currently inactive, so it does not look like a
  generic first-pass FireFlow blocker

The accepted delegated slice `fireflow-workflow-broker-correlation-v1`
sharpened the later-workflow branch with one concrete minute:

- at `2026-03-26 19:40 EDT`, Apache showed a real later FireFlow workflow
  minute through `POST /FireFlow/FireFlowAffApi/NoAuth/CommandsDispatcher`
  plus nearby AFF config and journal reads
- that minute rolled forward into `ms-configuration` unified-swagger refresh
  at `19:41:14-19:41:15`, including a concrete downstream
  `AlgoSec_ApplicationDiscovery` `502 BAD_GATEWAY`
- PostgreSQL did not show a same-minute failure for that branch
- ActiveMQ still should not be promoted earlier for that branch because
  `activemq.log` had no same-minute evidence and the nearest KahaDB updates
  appeared later around `19:45`, mainly on monitor and config-style
  destinations

That means the current later-workflow rule is now tighter:

- keep Apache -> FireFlow or AFF -> `aff-boot` first
- if the same minute rolls into swagger refresh or service-definition work,
  check `ms-configuration` and Apache `ssl_error_log` next
- only promote ActiveMQ earlier when broker logs or queue-store evidence line
  up in the same workflow minute on workflow-specific destinations

The accepted delegated slice `fireflow-submission-async-correlation-v1`
adds one useful negative heuristic:

- the `2026-03-21 04:30 EDT` `CommandsDispatcher` branch with repeated `3055`
  and `3070` response sizes is not yet a queue-backed submit or approval path
- that branch lined up with journal refresh, FireFlow session fetches, and AFA
  session extension rather than `ms-batch-application`, broker logs, or a
  visible workflow queue handoff
- PostgreSQL only showed routine `rt_user` disconnect noise in that same
  minute, not a deeper async failure

So the current FireFlow branch rule is tighter again:

- treat `CommandsDispatcher -> journal refresh` and
  `CommandsDispatcher -> UserSession:getUserSession` as synchronous
  maintenance-style traffic
- keep journal and session interpretation ahead of ActiveMQ for that cadence
- only revisit broker-first ordering when a later FireFlow minute shows a
  non-`UserSession` destination or a same-minute tie to `ms-batch-application`
  or workflow-specific broker destinations

The accepted delegated slice
`fireflow-approval-progression-correlation-v1` sharpened the next candidate
branch again:

- the strongest in-scope non-`UserSession` branch on `2026-03-26 10:19-10:20
  EDT` still did not reach a true approval, review, plan, implementation, or
  ticket-mutation step
- `ms-configuration.log` showed `application-afaConfig.properties` changes
  that explicitly `notify ActiveMq broadcast`
- `ms-initial-plan.log` received the matching
  `MicroserviceConfigurationBroadcast` and refreshed application context
- Apache showed the same-minute `/config/ms-*` fan-out across nearby
  microservices
- FireFlow then showed `Authentication:authenticateUser` followed by
  `User:GetUserInfo`, and the returned user data included approval-capable
  request templates
- `/opt/activemq` was empty on this appliance slice, so the allowed target set
  did not provide direct broker log or store proof for this branch

That means the FireFlow branch rule is tighter again:

- a non-`UserSession` dispatcher destination is not enough by itself to call a
  branch true request progression
- when the same minute clusters around config broadcast, microservice config
  fan-out, `Authentication:authenticateUser`, and `User:GetUserInfo`, treat it
  as config-propagation plus auth or user bootstrap
- keep ActiveMQ later-supporting for this branch unless a future slice shows a
  ticket identifier, a dispatcher target beyond `Authentication` or `User`, or
  same-minute worker or broker evidence tied to request mutation

The accepted delegated slice `fireflow-ticket-progression-hunt-v1` added one
more gating rule:

- the current lab is not merely "FireFlow disabled"; the stronger reading is
  that FireFlow is enabled but effectively empty from a ticket-workflow
  perspective
- `fireflow.log` showed repeated activation and polling behavior such as
  `brandConfig`, `allowedDevices`, `setup/fireflow/is_enabled`, and AFF or AFA
  bridge refresh work
- the same retained windows also showed `syslog_ticket_changes.pl` reporting
  `Total tickets in DB: 0` and `0 tickets updated in the last 10 minutes`
- no concrete request, approval, implementation, review, or ticket-mutation
  branch with an identifier appeared in the retained logs

That means the FireFlow branch rule is tighter again:

- if FireFlow is enabled and still only shows activation, config, AFF bridge,
  and session-maintenance traffic, do not keep spending time on broker or
  progression theory yet
- first ask whether the lab actually contains a recent FireFlow request or
  ticket to correlate
- if ticket count looks effectively zero, seed or replay one real FireFlow
  request before running another progression or ActiveMQ-oriented slice
