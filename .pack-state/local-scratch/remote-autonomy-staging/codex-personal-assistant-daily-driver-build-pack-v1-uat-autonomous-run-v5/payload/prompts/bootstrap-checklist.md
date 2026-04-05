# Bootstrap Checklist

Use this checklist when bootstrapping a fresh assistant workspace preview.

1. Export the assistant bundle to a target directory with the bootstrap
   workflow.
2. Review `assistant-profile.json` to confirm the assistant identity and
   mission fit the intended operator experience.
3. Review `operator-profile.json` to confirm the operator's goals and working
   preferences are concrete enough to guide behavior.
4. Review `partnership-policy.json` to confirm ambiguity handling and
   grounding expectations are explicit.
5. Review `context-routing.json` so the first operator tasks load only the
   right surfaces.
6. Review `skill-catalog.json` to confirm the initial capability slice is
   sufficient.
7. Add local assistant memory only after a real operator session creates
   something worth carrying forward.
