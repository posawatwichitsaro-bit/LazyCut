## Summary

The folder queue converts ready VALORANT recordings into a bounded set of highlight Reels when the user presses Start. Users can review each export and change its four-level local rating.

```text
Start folder queue
  Snapshot ready recordings
  Select unused player-kill events until the next Reel is ready
  Render MP4 and commit its source ranges and events together
  Repeat until the Reel limit or the end of the queue
```

## Evidence

- Previously an empty detection could render the start of a recording. The queue now finishes without an export when it finds no eligible event.
- Browser UAT detected events in two generated recordings using the repository killfeed fixture and produced two vertical MP4s. Changing the same Reel from Good to Very good moved the count from one category to the other.
- Docker regression coverage includes renamed recordings, source overlap, 720p portrait composition and recovery when the second render fails. The image passed 57 tests. One real-footage test was skipped because the recording was unavailable.
- The game guard badge now reads the configured status. Real-match accuracy across HUD languages and spectator footage remains pending user validation.

## Merge Danger

**Door** — Two-way. The new SQLite tables are additive. Existing exports can still be reviewed. Detailed event history starts with exports made by this version.

**Blast radius** — Local Studio ingestion, job planning, rendering, export history and ratings. Ratings are stored in the local exports directory.
