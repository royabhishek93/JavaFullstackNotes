# MED Q03 - Counting Views Correctly

## Scenario
Should a view be counted when playback starts, or after 30 seconds watched?

## Answer
Product decision, but counting immediately is easy to game.
A common approach is:
- emit playback start event
- count view only after threshold watch time
- deduplicate rapid refreshes per user/session/IP

## Interview One-Liner
View counting is an analytics policy question built on top of event ingestion.
