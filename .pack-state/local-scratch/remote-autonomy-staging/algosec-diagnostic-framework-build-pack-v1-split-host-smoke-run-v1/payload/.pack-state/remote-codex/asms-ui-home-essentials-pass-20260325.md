# ASMS UI Home Essentials Pass - 2026-03-25

## What This Slice Tried To Answer
Determine which signals after successful login are true first-class gates for `ASMS UI is down`, and which are only nearby supporting clues.

## Systems-Thinking Result
The rendered `/afa/php/home.php` page is the first-class post-login checkpoint for the current ASMS path.
Supporting post-home requests and assets are still useful clues, but they should not be promoted to first-class gates unless blocking them prevents the initial home shell from becoming meaningfully usable.

## What We Observed
- A bounded authenticated browser flow reached `https://127.0.0.1/afa/php/home.php` and rendered the main ASMS home shell with the expected top-level menu and summary content.
- Blocking `FireFlowBridge.js` did not prevent the initial home page from rendering with the normal menu and summary view.
- The bounded client-side comparison did not prove `/afa/api/v1/license` or `/afa/api/v1/bridge/refresh` are required for the initial home page render.
- This keeps immediate post-home routes inside the ASMS playbook as supporting clues rather than first-class stop points.
- Notification Center and watchdog-linked issue-count routes remain later subsystem context, not the main ASMS login or initial home-shell path.

## Why It Matters
This reduces support effort by keeping the playbook centered on the customer-visible usability checkpoint instead of overpromoting nearby requests that may fire during the same minute but do not actually gate the first usable ASMS home shell.

## Build-Pack Direction Captured
- Treat `/afa/php/home.php` render as the main post-login signal.
- Keep `FireFlowBridge.js`, `logo.php`, and light Metro refresh traffic as supporting clues.
- Require stronger proof before promoting any later post-home route into a first-class stop point.
