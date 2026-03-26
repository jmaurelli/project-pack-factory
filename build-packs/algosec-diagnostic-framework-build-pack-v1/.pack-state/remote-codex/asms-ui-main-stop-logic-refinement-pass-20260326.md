# ASMS UI Main Stop-Logic Refinement Pass

Date: 2026-03-26

## Result

The main `ASMS UI is down` playbook was tightened around clearer operator stop points instead of continuing to accumulate deeper seam notes without lifting them back into the top-level decision path.

## What Changed

- Step 3 now treats BusinessFlow as a real named branch point rather than a generic checkpoint.
- The auth branch can now stop at `BusinessFlow -> AFA connection` or `BusinessFlow -> AFF connection` when deep health makes one of those seams the first clear failure point.
- Step 4 now stays bounded to the first usable `/afa/php/home.php` shell plus immediate shell hydration.
- The GUI-up boundary stays explicit: once the customer can navigate the devices tree and open `REPORTS` to view a report, the case should branch out of `GUI down`; reaching `Analyze` is optional extra confirmation rather than a required gate.
- Step 5 now acts as a branch-out and naming surface for the first clear stop point instead of a generic log-reading bucket.

## Why It Matters

This keeps the playbook aligned with how support engineers actually classify and narrow cases:

- auth branch problems should stop at the closest named auth seam
- home-shell problems should stay on the first usable shell and its immediate support clues
- later workflow failures should leave the top-level `GUI down` bucket as soon as the customer has crossed the GUI-up boundary

## Carry Forward

- Use the BusinessFlow seam notes to support Step 3, not to replace it.
- Keep Step 4 bounded to home-shell usability and immediate hydration.
- Keep deeper module or workflow branches outside the top-level `GUI down` path unless the reproduced customer-visible minute proves they are the first true stop point.
