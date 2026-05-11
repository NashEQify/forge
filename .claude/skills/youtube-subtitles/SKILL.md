---
name: youtube-subtitles
description: Use this skill to fetch and summarize a YouTube video via its subtitle track (no audio download, no transcription). Required path when User shares a YouTube URL and expects content extraction — manual workarounds (asking User for summary, hallucinating from video title) bypass the actual content. Triggers when a YouTube URL appears in User input combined with intent to extract/summarize/discuss content. Examples: "fass das video zusammen [youtube-link]", "was sagt das video über X", "schau dir das video an [youtube-link]", User pastes a YouTube URL with a question about the content.
---

# Skill: youtube-subtitles (Wrapper)

This is the Claude-Code-discoverable wrapper. The full protocol (subtitle
fetch via yt-dlp, language-fallback, summarization format) lives in the
orchestrator-neutral SoT:

**SoT:** `skills/youtube_subtitles/SKILL.md`

Read the SoT and follow it. This wrapper exists only so Claude Code can
inject the skill into the available-skills system-reminder for proactive
discovery — the methodology is unchanged.
