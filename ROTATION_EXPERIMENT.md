# Two-week Story rotation experiment

Status: scheduled in code for **October 2–15, 2026**, inclusive (UTC posting dates),
once merged to `main` before the October 2 scheduled post. Review on October 16
after the 15:30 UTC collection for October 15. The 16:00 UTC post on October 16
automatically uses the original cycle. No extension or permanent promotion is automatic.
If merged after the start, do not reset the dates silently: treat the shortened run
as inconclusive and explicitly plan a fresh window if needed.

## Evidence and hypothesis

The supplied September 17–30 Story Register summary is directional evidence:

| Group | Average reach per slide | Approximate completion | Other signal |
|---|---:|---:|---|
| SET_ONE | 15 | 82%, two slides | |
| SET_TWO | 13 | 78%, two slides | |
| QUIZ | 11 | 71%, first to last | Four measured days |
| SET_FIVE | | | Only measured follow |
| SET_FOUR | | | Only two interactions and one profile visit |

Several groups have only one measured day; SET_THREE and SET_SIX have missed
insight windows. Missing data is unknown, not zero performance. The existing
snapshot also contains unmeasured recent posts. The supplied rounded completion
figures are context, not a substitute for consistently calculated endpoint metrics.

Hypothesis: replacing two repeated four-slide quiz slots with the intact SET_ONE
and SET_TWO pairs improves reach per slide without materially reducing their
within-group completion or removing opportunities for the other creatives.
This is a small before/after pilot, not a randomized test or proof of causality.

## Creative inventory inspected

All six sets are two-slide pairs, with their matching `_A` slide second:

| Group | Existing creative |
|---|---|
| SET_ONE | Choosing the best AI tool / Robot for You course |
| SET_TWO | Getting better chat results / Prompting for Baddies |
| SET_THREE | Future Self prompts |
| SET_FOUR | Build Your Brand Brain |
| SET_FIVE | Personal-life mental load / Baddie University |
| SET_SIX | Business content, AI employee and command centre |
| QUIZ | Four-slide Clever Girl Delegation Audit promotion, ONE through FOUR |
| QUIZ_STANDALONE | One-slide delegation audit invitation |

Creative files, wording, CTAs, slide order and timing stay fixed to isolate the
rotation change. Existing BBB branding remains part of this fixed creative control.

## Before and after

The September 4 cycle anchor and 12-day length remain unchanged.

| Cycle day | Before | During experiment |
|---|---|---|
| 1 | SET_ONE | SET_ONE |
| 2 | QUIZ | QUIZ |
| 3 | SET_TWO | SET_TWO |
| 4 | QUIZ_STANDALONE | QUIZ_STANDALONE |
| 5 | SET_THREE | SET_THREE |
| 6 | QUIZ | **SET_ONE** |
| 7 | SET_FOUR | SET_FOUR |
| 8 | QUIZ_STANDALONE | QUIZ_STANDALONE |
| 9 | SET_FIVE | SET_FIVE |
| 10 | QUIZ | **SET_TWO** |
| 11 | SET_SIX | SET_SIX |
| 12 | QUIZ_STANDALONE | QUIZ_STANDALONE |

Only two slots change, the minimum to add one exposure for each stronger set
per cycle without stacking extra slides. Each 12-day cycle retains one full quiz
and three standalone quizzes; all six sets remain represented. Total slides
decrease from 27 to 23, so raw totals are not the success metric.

Actual October 2–15 sequence (the experiment starts on cycle day 5):

`THREE → ONE → FOUR → QS → FIVE → TWO → SIX → QS → ONE → Q4 → TWO → QS → THREE → ONE`

That is SET_ONE three times, SET_TWO twice, SET_THREE twice, SET_FOUR/FIVE/SIX
once each, one full quiz and three standalone quizzes. Relative to the unchanged
14-day sequence, ONE gains two dates and TWO gains one; quiz days fall from
seven to four. This unequal exposure is accounted for with per-slide/per-day
averages and reported sample counts, not totals.

## Measurement and decision rule (set before launch)

Use September 17–30 as the baseline and October 2–15 as the experiment window.
Join `data/posts.jsonl` to `data/insights.jsonl` by media ID. For each ID choose
the latest snapshot collected 20–24 hours after posting, using the same rule in
both windows. Deduplicate IDs; never sum repeated snapshots. Exclude manual
overrides/reposts from the experiment comparison and record exclusions by run ID.
Use only complete posting days with every expected slide published and numeric
reach and views for all slides. Report missing/partial days separately; do not
fill missing metrics with zeros. Real measured zeros stay zeros.

* **Primary metric:** mean daily reach per slide. For each eligible posting day,
  divide the sum of slide reach by its slide count; then average those daily
  means so each day has equal weight. Success requires **at least 10% improvement**
  over the baseline calculated with the same rule. This is a practical pilot
  threshold, not a statistical-significance claim. It measures slide efficiency,
  not unique daily audience, because audiences can overlap between slides.
* **Completion guardrails:** within each of SET_ONE and SET_TWO, sum last-slide
  views and divide by sum first-slide views across eligible pairs in each window.
  Neither may fall by more than **5 percentage points** from its consistently
  recalculated baseline. A zero first-slide denominator is undefined, not 0%.
  Report the same proxy for the four-slide quiz separately; do not pool two- and
  four-slide completion or call a single slide 100% completion. These are view
  ratios, not tracked individual viewer retention.
* **Coverage gate:** at least **11 of 14** complete experiment days, including
  at least two measured days each for SET_ONE and SET_TWO, one complete full quiz,
  and two standalone quizzes. Require at least one complete baseline day for
  each stronger set and a defined completion baseline. Missing coverage or an
  undefined guardrail means **inconclusive**, not a win. One baseline day is still
  weak evidence even when the gate passes.
* **Secondary signals:** report follows, interactions and profile visits by group
  with measured-day counts and per-slide rates; retain nulls for unavailable
  metrics. SET_FOUR and SET_FIVE keep exposure to test whether their sparse signals
  repeat. One follow or a couple of interactions alone cannot decide the trial.

At the October 16 review: if coverage, primary threshold and both completion
guardrails pass, label the pilot promising and propose a longer confirmation
test. If coverage passes but the performance rule fails, do not adopt the tested
mix. If coverage fails, label it inconclusive. **In all cases the baseline resumes
on October 16; a further change needs an explicit decision.** Do not keep running
until the numbers happen to look favourable.

## Reversibility and logging

`post_story.py` applies date-bounded slot substitutions; `index.html` mirrors
them for future previews only. Historical records are read from actual posts.
Manual `CYCLE_DAY_OVERRIDE` retains the original baseline day semantics.
To stop early, clear both `ROTATION_EXPERIMENT_SLOTS` and
`CONFIG.experiment.slots` in the same commit (or revert the experiment commit).
Do not reset `CYCLE_START_DATE`, delete data or rename groups.

The publication log schema and per-slide append, duplicate-post protection,
collector, JSONL history, workflow schedules and always-save steps are unchanged.
Normal posts still log their actual group, filename, slide number and run ID.
No extra scheduler, posting run or insights job is created by this change.
