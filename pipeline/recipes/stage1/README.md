# Stage 1 — paid UGC pilot (30.4 credits)

Local media named in these recipes (shot*.mp4, vo_*.mp3, st_*.png, A_4klow.png, C_2kmed.png) are Higgsfield
outputs, not stored in git. Drive IDs are real library clips, read by range request.

| file | Higgsfield job | model | credits |
|---|---|---|---|
| A_4klow.png / A_2klow.png (gate frame) | 7530820a / 8c349caa | gpt_image_2_5 | 0.75 / 0.5 |
| shotA_gate.mp4 (5 s) | 06c387f6 | seedance 2.0 mini | 5 |
| shotB_bridge.mp4 (4 s) | b6440b34 | seedance 2.0 mini | 4 |
| shotC_seatbelt.mp4 (5 s) | fd508d8a | seedance 2.0 mini | 5 |
| st_postit / st_clipboard / st_flatlay | 08c7d897 / 2bb3036c / 8d797601 | gpt_image_2_5 4K low | 0.75 each |
| swap_black.mp4 (brown to black, real clip) | dcb2e9a3 | kling_video_edit std 5 s | 7.5 |
| vo_maeve.mp3 / vo_f3_maeve.mp3 | — / 2abd5687 | text2speech_v2 elevenlabs (Maeve) | ~0.6 each |

    python3 pipeline/recut.py pipeline/recipes/stage1/f1_pocket.json --out F1.mp4      # run from a dir holding the local media, or copy the EDL next to it
    python3 pipeline/ugc_statics.py pipeline/recipes/stage1/statics_s1.json --outdir statics/
