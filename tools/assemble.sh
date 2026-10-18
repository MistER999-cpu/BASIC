#!/usr/bin/env bash
# Join part 1 and part 2, lay the sound design under them, and encode for an
# Instagram Reels/Stories ad: 1080x1920, 30 fps, H.264 High 4.2, AAC 48 kHz,
# faststart. Part 2's first frame is part 1's last Quick Look frame, so the
# join is a straight cut.
#
#   bash tools/assemble.sh            # -> campaign/final/basic-ad.mp4
set -euo pipefail
cd "$(dirname "$0")/.."
D=campaign/final
python3 tools/sfx.py "$D/sfx.wav"
ffmpeg -hide_banner -loglevel error -y \
  -i "$D/part1.mp4" -i "$D/part2.mp4" -i "$D/sfx.wav" \
  -filter_complex "[0:v][1:v]concat=n=2:v=1:a=0,format=yuv420p[v]" \
  -map "[v]" -map 2:a \
  -c:v libx264 -preset slow -crf 17 -profile:v high -level 4.2 -r 30 \
  -c:a aac -b:a 192k -ar 48000 -movflags +faststart -shortest \
  "$D/basic-ad.mp4"
ffprobe -v error -show_entries format=duration,size:stream=codec_name,width,height,r_frame_rate,sample_rate \
  -of compact "$D/basic-ad.mp4"
