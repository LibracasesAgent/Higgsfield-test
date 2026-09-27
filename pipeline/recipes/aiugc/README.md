# AI UGC test — hybrid "face → proof → face" (77.2 credits incl. one-time 40-credit voice clone)

Persona (AI-generated, not a real person): soul_2 3124ce03 (blonde ~45, kitchen). Other options: bb9b05fa, 763e6d59, 62ea9e50.
Start frames (gpt_image_2_5 2K low, persona + bag refs): A hook b308e702, A close 7ff9c922, B hook a39c4b52, B close c2b4acd7.

| ad | talking clips | voice | body |
|---|---|---|---|
| adA "3 things to check" | kling3_0 std 5 s, sound on (7e5f8e1f, 91db410a) — 10 credits each | Kling's own voice; middle lines in a clone of it (voice element 435d2b74, clone 40 credits one-time; TTS ~0.45/line), gaps tightened | real back-pocket clip + AI zip macro + AI D-ring |
| adB "stop carrying a bag that swallows your keys" | wan2_7 720p 4 s / 5 s with audio_references = ElevenLabs Maeve lines (55b8e56a, f7979d90) — 6 / 7.5 credits | Maeve throughout (lip-synced to our TTS) | AI zip macro + AI gate passport + AI cafe card |

Rules: presenter/demonstrator script only (no ownership or experience claims); label as AI-generated.
QA: faster-whisper base.en transcripts matched all lines; Kling hook transcribed "I checked" vs scripted "I'd check" — verify by ear.
Hook plate over a talking face: set "hook_y": 1060 in the EDL.

## Test 2 — persona 3 (763e6d59, young woman, trench, hallway) + lip-sync shoot-out (56.5 credits)

Start frame 54c5d504 (gpt_image_2_5). Same hook line, same frame:
- kling3_0 std 5 s (7a412954, 10 cr): lipsync_check 0.40 PASS, clear articulation.
- veo3_1 fast 4 s (994f4a52, 16 cr): -0.27 FAIL — mouth closes on loud syllables.
- seedance_2_0_mini 5 s (70d88b0b): blocked by the moderation filter (false positive), refunded.
- Last round: Wan 2.7 driven by TTS scores ~0.45 but the mouth barely shapes words (looks "off").
Kling 15 s single take (88823fb9, 30 cr): the bag morphs mid-clip and sync degrades when she looks down.
adC uses that take's voice for the whole ad but shows her face only on the hook line (0-3.1 s) and a 0.5 s smile;
real/AI bag footage covers the rest (J-cut). Rule: show lips only on the hook; keep face clips <= 5 s.
