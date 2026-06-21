
## Known Limitation — Skill Auto-Triggering (discovered Day 9)
Simple, single-line categorisation questions sometimes bypass the 
finance skill entirely and get answered from general model knowledge,
producing invented category names (e.g. "Shopping / Online Shopping" 
instead of the correct "Shopping & Apparel"). 

Root cause: skill triggering is probabilistic, not guaranteed, even 
with a strongly-worded frontmatter description. Confirmed via direct 
agent self-report — the skill was discoverable but the model judged 
the question "simple enough" to bypass it.

Mitigation: moved the directive into groups/main/CLAUDE.md, which 
loads unconditionally every session rather than relying on conditional 
skill triggering for this specific failure mode.

Lesson: never trust "the skill exists" as proof "the skill fired."
Always verify the output against docs/rules.md's exact category 
strings (see docs/verify.md Skill Invocation Check).
