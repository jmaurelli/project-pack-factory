# ADF Support-Safe Scientific Method Contract v1

## Purpose

Define the small scientific-method loop ADF should use when building and
validating diagnostic playbooks for support engineers.

This is not academic science for its own sake.
It is a support-safe troubleshooting method that keeps ADF evidence-first,
repeatable, and bounded.

## Why This Matters

ADF is strongest when it helps a support engineer start from a vague customer
report and move toward a known next action quickly.

The scientific method helps with that because it gives ADF a simple repeated
loop:

1. observe
2. form a hypothesis
3. test
4. observe the result
5. revise the hypothesis
6. repeat or stop

## ADF Translation

In ADF, the loop becomes:

1. Observe the customer symptom.
2. Pick the most likely next support hypothesis.
3. Run the safest, fastest, highest-signal check.
4. Read the result.
5. Narrow the next branch or name the stop point.
6. Repeat only while the next step still reduces ambiguity.

This loop should be explicit in ADF notes, mapping rows, or validation output.
It should not stay as hidden reasoning inside the agent.

This is an ADF authoring and validation method.
It should guide mapping, generator inputs, and playbook validation.
It should not appear as a named theory section inside the frontline page.

## The Six Steps

### 1. Observe

Start from the visible or reported symptom.

Examples:

- `The web page is not loading`
- `Login fails`
- `ASMS opens but the customer cannot continue`

### 2. Hypothesis

State one likely explanation that is small enough to test safely.

Examples:

- this may be an Apache or HTTPD problem
- this may be a Keycloak auth problem
- this may be narrower than top-level `GUI down`

Do not start with a broad whole-system theory if a smaller support check can
reduce ambiguity first.

Name the current candidate stop point in support terms when possible.

Examples:

- `this may still be an Apache or HTTPD issue`
- `this may now be a login or Keycloak issue`
- `this may already be narrower than top-level GUI down`

One valid hypothesis is also that the case may be outside the named subsystem
or outside the appliance itself, for example:

- browser-side issue
- external path issue
- customer report is broader than the current appliance evidence

### 3. Test

Run the lowest-cost, highest-signal safe check that can prove or weaken the
hypothesis.

Prefer:

- read-only commands
- local checks
- direct service state or route checks
- checks that change the next support action

### 4. Observe The Result

Record what the test actually showed.

Keep observed facts separate from inference.

### 5. Revise The Hypothesis

Use the result to narrow the case.

Examples:

- `httpd` is down, so this is now an Apache path
- the login page opens, so the case is narrower than top-level UI down
- Keycloak is up but auth still fails, so the branch needs a different check

### 6. Repeat Or Stop

Repeat only if the next test is still:

- safe
- bounded
- likely to reduce ambiguity

Stop when:

- the next action is clear
- the right service to inspect is now known
- the engineer has enough evidence to escalate
- the next step would require deeper R&D or senior-engineer reasoning

## Branching Rule

Branches should appear only when a test result changes the next useful action.

That means:

- one hypothesis
- one test
- one result
- one next branch

Do not create many branches from one weak observation.

Do not keep a branch unless the result names a clearer next action, next
service, or escalation packet.

## Page-Type Use

Use this method differently across the ADF page types:

- symptom-entry playbook:
  use the loop to move from vague customer language to the first likely branch
- boundary-confirmation page:
  use the loop to confirm or eliminate one named service or subsystem
- deep guide:
  explain why the branch behaves that way, outside the fastest live path

## Validation Rule

When ADF claims a playbook is useful, it should be because the playbook helped
the engineer do at least one of these:

- choose a better first check
- rule out a broader symptom quickly
- land on the right service sooner
- gather the right escalation evidence with fewer wasted checks

## Recording Rule

Each support-safe scientific-method cycle should record:

- the starting symptom
- the current hypothesis
- the exact test used
- the observed result
- the revised hypothesis or named stop point
- the rejected or weakened branch
- the next action or stop point

This keeps the loop repeatable and makes later generator or page work easier to
audit.

If ADF cannot show those items, the cycle is not explicit enough yet.

Prefer one primary hypothesis at a time.
If a test does not narrow the case, record that and stop or pick one new
hypothesis deliberately instead of silently widening into multiple new theories.

## Fail-Closed Rule

Do not keep repeating the loop just because more internal dependencies exist.

Stop and record a support stop point when:

- two fast safe checks still do not narrow the case
- the next test would be unsafe
- the next test would need broad reverse engineering
- the next question is no longer a frontline support question

If the test is a lab-only mutation experiment, preserve the observer result and
rollback outcome separately from the mutation step itself.

## Current ADF Application

For the current ADF phase:

- `ASMS UI is down` is the main symptom-entry proving ground
- Keycloak is a good boundary-confirmation pilot because the current lab gives a
  live auth-failure case, but it should not become a new symptom-entry page
  from one incident alone
- the scientific-method loop should shape both the backend mapping model and
  the operator-facing branching flow

## Current Code Anchors

This method contract is expected to anchor to the current structured backend
output path in:

- `src/algosec_diagnostic_framework_template_pack/runtime_baseline.py`
  `build_support_baseline()`
- `src/algosec_diagnostic_framework_template_pack/runtime_baseline.py`
  `_build_diagnostic_flows()`
- `src/algosec_diagnostic_framework_template_pack/runtime_baseline.py`
  `_build_symptom_lookup()`
- `src/algosec_diagnostic_framework_template_pack/runtime_baseline.py`
  `_build_decision_playbooks()`

These are the current code surfaces where ADF can start preserving explicit
cycle records instead of leaving the scientific-method loop as hidden agent
reasoning.

## First Expected Change Surfaces

The first implementation-grade changes expected by this contract should happen
in:

1. `build_support_baseline()` or adjacent backend record builders
   Add explicit cycle-record fields for new or migrated records:
   symptom, hypothesis, test, result, rejected branch, revised stop point, and
   next action.

2. `_build_diagnostic_flows()` and `_build_decision_playbooks()`
   Preserve the cycle output in a structured form that later page rendering can
   translate safely.

3. `starlight_site.py`
   Consume only the operator-facing output of that loop for frontline pages,
   not the theory-language version of the method itself.
