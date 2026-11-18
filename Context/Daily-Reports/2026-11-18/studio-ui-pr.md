## Summary

The Studio Feed places the clip library beside the export controls. Users can start with a recording folder, create highlights from ready recordings, or select individual clips.

```text
Empty library       → Set recording folder
Ready recordings    → Create folder highlights
Selected recordings → Create from selected clips
```

Landscape and portrait controls show the output aspect ratio directly. Folder scanning and list refresh have distinct labels, and in-page messages report action results. The Reel Inspector keeps playback, chapters, downloads, ratings and export history together.

## Evidence

- Compared with the earlier empty state, the redesigned library directs users to folder settings and explains when export becomes available.
- Browser checks verified that the folder action focuses the watch-path field and that selecting Portrait activates the 9:16 control. Navigation to Settings, Reel Inspector and export history was also checked.
- The Docker test suite passed 57 tests. One test requires a local VALORANT recording and was skipped.
- The dashboard smoke test checks the updated automatic and manual export actions.

## Merge Danger

**Door** — Two-way. Reverting the commit restores the previous dashboard.

**Blast radius** — Studio UI and its dashboard smoke test. The main review points are selection state, filtering, keyboard focus and export-button availability.
