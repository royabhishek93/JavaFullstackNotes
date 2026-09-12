## [notes.md] Timing Diagram — FixedRate vs FixedDelay vs Cron (task runs longer than its interval)

> NOTE: this block is a Mermaid `gantt` chart, which is not one of the diagram types covered by the standard conversion rules (flowchart/stateDiagram-v2/sequenceDiagram/classDiagram/erDiagram). Per instructions, flagging this explicitly rather than guessing at an ASCII gantt-bar rendering — converted instead to an equivalent plain-text timeline table in the source file, preserving every run/label/timestamp.

```mermaid
gantt
    title FixedRate vs FixedDelay vs Cron: behavior when a task overruns its interval
    dateFormat  HH:mm
    axisFormat  %H:%M

    section FixedRate (interval = 3s, formula: next = prevStart + interval)
    Run1 starts 10:00, takes 4 (overruns 3s interval)      :active, fr1, 10:00, 4m
    Run2 ideal tick was 10:03 (missed, queued right after) :fr2, after fr1, 4m
    Run3 ideal tick was 10:06 (missed again, same pattern)  :fr3, after fr2, 4m

    section FixedDelay (interval = 3s AFTER finish, formula: next = prevFinish + interval)
    Run1 starts 10:00, takes 4, finishes 10:04              :active, fd1, 10:00, 4m
    Run2 starts at finish(10:04) + 3 = 10:07                :fd2, 10:07, 4m
    Run3 starts at finish(10:11) + 3 = 10:14                :fd3, 10:14, 4m

    section Cron (every 10 min wall clock: :00 :10 :20 :30..., task takes 25 min)
    Run1 starts 10:00 (task overruns; 10:10 and 10:20 ticks are MISSED) :crit, c1, 10:00, 25m
    Run2 next wall-clock tick after finish(10:25) is 10:30              :c2, 10:30, 25m
```
