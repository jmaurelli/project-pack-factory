# ADF Successor Shallow Surface Summary

## Scope

- Target: 10.167.2.150
- Hostname: algosec
- Components recorded: 354
- ASMS doc-pack hints: loaded from `dist/candidates/adf-docpack-hints/asms-docpack-hints.json`
- ASMS doc-pack version: asms-A33.10-docpack-v1 A33.10

The doc-pack hint layer only informs naming, port-based hints, and prioritization. Live runtime evidence remains the source of truth for what is running here.

## What Appears To Be Running

- `ms-bflow`: edge_proxy (confidence high, ports 1989, 5701, 8080, 8081, 8082, 8083, 8086, 8087, 8093, 8096, 8097, 8104, 8132, 8134, 8136, 8138, 8157, 8159, 8174, 8183, 8185, 9200, 9300, 9600, 61616) Doc-pack hints: matched terms afa; matched ports 8082
- `ms-metro`: edge_proxy (confidence high, ports 1989, 5701, 8080, 8081, 8082, 8083, 8086, 8087, 8093, 8096, 8097, 8104, 8132, 8134, 8136, 8138, 8157, 8159, 8174, 8183, 8185, 9200, 9300, 9600, 61616) Doc-pack hints: matched terms afa; matched ports 8082
- `activemq`: edge_proxy (confidence high, ports 1989, 5701, 8080, 8081, 8082, 8083, 8086, 8087, 8093, 8096, 8097, 8104, 8132, 8134, 8136, 8138, 8157, 8159, 8174, 8183, 8185, 9200, 9300, 9600, 61616) Doc-pack hints: matched ports 8082
- `algosec-ms`: application_service (confidence medium, ports 1989, 5701, 8080, 8081, 8082, 8083, 8086, 8087, 8093, 8096, 8097, 8104, 8132, 8134, 8136, 8138, 8157, 8159, 8174, 8183, 8185, 9200, 9300, 9600, 61616) Doc-pack hints: matched terms afa, algosec; matched ports 8082
- `logstash`: application_service (confidence low, ports 1989, 5701, 8080, 8081, 8082, 8083, 8086, 8087, 8093, 8096, 8097, 8104, 8132, 8134, 8136, 8138, 8157, 8159, 8174, 8183, 8185, 9200, 9300, 9600, 61616) Doc-pack hints: matched terms api; matched ports 8082

## Visible Unknowns

- The first pass does not yet parse config files, unit fragments, or logs.
- The first pass does not claim complete dependency order or request-path ownership.
- The first pass keeps product labeling bounded; some components may still be generic or misclassified.

## Next Candidate Seams

- `trace_edge_to_local_service_routes`: Several visible listeners suggest a bounded next pass through proxy-to-local-service ownership. Starting points: ms-bflow, ms-metro, activemq.
- `inspect_java_runtime_clusters`: Java-adjacent components are visible but their role boundaries are still tentative. Starting points: ms-bflow, ms-metro, activemq.

