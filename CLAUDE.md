# HUBMI

Category: HubMI.pl

Team rules are in CLAUDE.local.md (synced, not in git).

## Dub

When the user drops an audio or video file (lands in `/mnt/user-data/uploads`), dub it without asking:
`uv run dub/dub.py <file>`. Default target is Russian (English if the source is Russian), `--to <lang>` overrides.
Voice is ElevenLabs `eleven_multilingual_v1` / `eleven_monolingual_v1` and needs `ELEVENLABS_API_KEY` in the environment.
Results go to `/mnt/user-data/outputs`; send them to the user.
