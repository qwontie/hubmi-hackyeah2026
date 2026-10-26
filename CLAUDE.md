# HUBMI

Category: HubMI.pl

Team rules are in CLAUDE.local.md (synced, not in git).

## Dub

When the user drops an audio or video file (lands in `/mnt/user-data/uploads`), dub it without asking:
`uv run dub/dub.py <file>`. It goes through the ElevenLabs Dubbing API (dubbing_v1), target Russian by default,
`--to <lang>` overrides. Needs `ELEVENLABS_API_KEY` in the environment.
Results go to `/mnt/user-data/outputs`; send them to the user.
