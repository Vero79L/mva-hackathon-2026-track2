# Computed (engine) vs human research judgment

The engine produces a COMPUTED gate verdict; the human research judgment is the
scientific disposition. Divergence is expected and explained — the engine never
overwrites, nor is inferred from, the human judgment.

A gate PASS means no `properties[]` tag that the rule acts on at this patient's level —
not an absence of risk. The last two columns make that difference visible: *gate-silent*
axes are assessed as unresolved but carry no tag the gate reads, and *unactioned* tags are
risks the gate can see but has no rule for at this level.

| ID | Human | Engine | Explanation of divergence | Gate-silent axes | Unactioned risk tags |
|---|---|---|---|---|---|
| C-NAD | CONDITIONAL | REJECT | engine REJECTs on INELIGIBLE (NMN/NR are supplements, no approved product); human keeps the SIRT2-BubR1 mechanism-branch CONDITIONAL — its approved-product instance is evaluated separately as C-NA | growth, oncology | not evaluated (rejected before the gates) |
| C-NA | CONDITIONAL | CONDITIONAL | — | growth, oncology | — |
| C-RT | CONDITIONAL | REJECT | engine REJECTs on INELIGIBLE (no approved renal-safe UGA agent); human keeps the mechanism-branch CONDITIONAL | growth, oncology, renal | not evaluated (rejected before the gates) |
| C-PBA | INSUFFICIENT | CONDITIONAL | engine has no INSUFFICIENT terminal; an eligible-but-weak candidate reads CONDITIONAL | — | — |
| C-NAC | CONDITIONAL | CONDITIONAL | — | oncology | — |
| C-AMPK | CONDITIONAL | REJECT | engine REJECTs at renal gate (metformin renal_cleared_narrow_TI vs nephrocalcinosis); human keeps the deselection mechanism CONDITIONAL pending a non-renal AMPK agent | growth, oncology | not evaluated (rejected before the gates) |
| C-DQ | REJECTED | CONDITIONAL | human REJECTED is a research judgment (downstream action + endpoint mismatch), not one of the four gates — and note the engine's own note in the last column: a senolytic TKI pair tagged `immunosuppressive` passes the oncology gate because the rule does not act on that tag at the `history` level | — | 'immunosuppressive' is a recognised risk tag but this level's rule does not act on it |
| C-FOL | INSUFFICIENT | CONDITIONAL | engine has no INSUFFICIENT terminal; reads CONDITIONAL | oncology | — |
| C-RAPA | CONDITIONAL | CONDITIONAL | — | — | 'immunosuppressive' is a recognised risk tag but this level's rule does not act on it; 'growth_suppressive' is a recognised risk tag but this level's rule does not act on it |
| N-MITOTIC | REJECTED | REJECT | — | growth, renal | not evaluated (rejected before the gates) |
| N-CQ | REJECTED | CONDITIONAL | eligible + directionally plausible so engine passes gates; human REJECTED on chronic pediatric toxicity + hypothesis-only (not a gate) | growth, oncology, renal | — |
| N-ASA | REJECTED | REJECT | — | growth, oncology, renal | not evaluated (rejected before the gates) |
| N-ISO | REJECTED | REJECT | — | growth, oncology, renal | not evaluated (rejected before the gates) |
| N-AICAR | REJECTED | REJECT | — | growth, oncology, renal | not evaluated (rejected before the gates) |
| N-NAVI | REJECTED | REJECT | — | growth, oncology, renal | not evaluated (rejected before the gates) |
| N-FIS | REJECTED | REJECT | — | growth, oncology, renal | not evaluated (rejected before the gates) |
| N-NUC | REJECTED | REJECT | — | growth, oncology, renal | not evaluated (rejected before the gates) |
