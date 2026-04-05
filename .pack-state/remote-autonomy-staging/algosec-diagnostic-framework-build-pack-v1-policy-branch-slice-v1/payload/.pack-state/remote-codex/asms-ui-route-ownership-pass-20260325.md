# ASMS UI Route Ownership Pass

Date: 2026-03-25
Path constraint: stay on `ASMS UI is down`
Method: fresh-session evidence review from the appliance, Apache proxy-rule inspection, exact same-minute Apache and Metro log correlation for fresh `PHPSESSID=cviqe976klg8krkb5lfdjtkugd`

## Observed facts

- Apache default AFA config exposes two Metro-facing proxy families:
  - `<Location /afa/external>` -> `ProxyPass http://localhost:8080/afa/api/v1`
  - `<Location /afa/api/v1>` -> `ProxyPass http://localhost:8080/afa/api/v1`
- For the fresh session, Apache saw:
  - `GET /afa/external//config?session=cviqe976klg8krkb5lfdjtkugd&domain=0`
  - `POST /afa/external//session/extend?domain=0&session=cviqe976klg8krkb5lfdjtkugd`
- In the same fresh-session minute, Metro saw:
  - `GET /afa/config/?domain=0&session=cviqe976klg8krkb5lfdjtkugd`
  - `GET /afa/api/v1/config?session=cviqe976klg8krkb5lfdjtkugd&domain=0`
  - `POST /afa/api/v1/session/extend?domain=0&session=cviqe976klg8krkb5lfdjtkugd`
  - `GET /afa/api/v1/license`
  - `GET /afa/getStatus`

## Ownership read

- `/afa/getStatus` appears to land first on Metro.
- `/afa/api/v1/license` appears to land first on the Apache `/afa/api/v1` proxy family, then Metro.
- `/afa/api/v1/config?...` appears to land first on the Apache `/afa/api/v1` proxy family, then Metro.
- `/afa/api/v1/session/extend?...` appears to land first on the Apache `/afa/api/v1` proxy family, then Metro.
- `/afa/config/?...` appears to be a paired Metro-side config surface that shows up in the same fresh-session minute as the `/afa/external//config` Apache requests.

## Interpretation

- `/afa/config/` and `/afa/api/v1/config` do not look like one simple browser-owned request path. They look like paired server-side surfaces around the same config family.
- That means browser CDP blocking was the wrong control point for proving ownership of the real fresh-session config/session routes.

## Best next step

Run the next isolation experiment at the Apache-to-Metro proxy seam, especially across the `/afa/external` and `/afa/api/v1` families, instead of repeating browser-side request interception.
