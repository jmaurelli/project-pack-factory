# ADF Frontline Playbook Testing Workflow v1

## Purpose

Define a small, grounded way to test whether a frontline ADF playbook is
actually useful for support engineers during live customer sessions.

The goal is not to invent more scenarios than we need. The goal is to keep the
testing loop small, repeatable, and evidence-led.

Use `docs/specs/adf-frontline-testing-decision-model-v1.md` as the companion
logic note for why this sequence exists and how to judge whether a trial is
actually helping a frontline support engineer.

## Trial Order

Use this order for the frontline `ASMS UI is down` playbook:

1. Healthy-path trial
   Prove the playbook stops quickly on a healthy appliance minute without
   drifting into deeper auth or subsystem theory.

2. Symptom-classification trial
   Prove the playbook can reclassify a vague `GUI down` report into a narrower
   login, shell, or later workflow problem once the shallow path says the
   top-level UI is still up.

3. Controlled shallow-fault trial
   Only after the first two phases stay useful, test one safe reversible
   shallow fault such as `httpd.service` or `ms-metro.service`.

## Scoring Rule

A frontline trial is useful when it:

- stops on host sanity, `HTTPD/Apache`, core service state, safe restart
  boundary, or first usable shell classification
- reduces ambiguity quickly
- avoids deeper auth/bootstrap/module tracing unless the shallow path truly
  fails
- leaves the engineer with a clear next support action

A trial is not useful when it:

- turns into a deep log hunt
- promotes BusinessFlow, FireFlow, AFA, or other deeper modules before the
  shallow path has failed
- requires the engineer to think like a Linux architect instead of a support
  engineer

## Safety Rule

Keep the sequence fail-closed:

- start healthy
- keep mutations out of the first pass
- only use safe reversible shallow faults later
- stop quickly if the method is not reducing ambiguity or support effort
