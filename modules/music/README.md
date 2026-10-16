# Music module

Initial commands: /music, /play, /pause, /resume, /skip, /queue, /nowplaying, /volume, /loop, /shuffle, /stop, /fm, /lastfm, /lyrics.

Playback uses direct HTTPS URLs and requires FFmpeg and discord.py voice support (PyNaCl). Spotify/YouTube extraction is not provided. **Last.fm keys are optional**: playback does not use them.

**Limitations:** This is an early implementation. No vote-to-skip, queue persistence, robust voice-session lifecycle, interactive controller, auto-disconnect, URL redirect protection, streaming host allowlist, or actual Last.fm account authorization/scrobbling. Do not deploy the audio URL feature publicly without strengthening source validation and resource limits.
