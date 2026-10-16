#!/usr/bin/env bash
set -euo pipefail
D=/root/autodl-tmp/cvpr27/data/video_evidence_v1
LOG="$D/remote_prep_monitor_20261005.log"
exec > >(tee -a "$LOG") 2>&1
EXPECTED=5c6267f99827de3ea7dc26111410c9d6c2dd47facd0c2c4a213eb06aa5900719
while true; do
  ok=1
  for i in 00 01 02 03 04 05 06; do
    [ "$(stat -c %s "$D/part_${i}.bin" 2>/dev/null || echo 0)" = 3221225472 ] || ok=0
  done
  [ "$(stat -c %s "$D/part_07.bin" 2>/dev/null || echo 0)" = 1449404928 ] || ok=0
  if [ "$ok" = 1 ]; then break; fi
  echo "waiting $(date -Is)"; sleep 20
done
for i in 00 01 02 03 04 05 06 07; do test -f "$D/part_${i}.bin"; done
rm -f "$D/video_evidence_v1_remote.tar"
cat "$D"/part_*.bin > "$D/video_evidence_v1_complete.tar"
ACTUAL=$(sha256sum "$D/video_evidence_v1_complete.tar" | awk '{print $1}')
printf 'archive_sha256=%s\n' "$ACTUAL"
test "$ACTUAL" = "$EXPECTED"
rm -f "$D"/part_*.bin
ln -sfn "$D" /srv/video_evidence_v1
mkdir -p "$D/Dataset"
tar -xf "$D/video_evidence_v1_complete.tar" -C "$D"
test -f "$D/v1_manifest.jsonl"
test "$(sha256sum "$D/v1_manifest.jsonl" | awk '{print $1}')" = 0687ca7b63d95776d341a3702a13ec96594fa9f323c41c1714fd7d57f557d47
test -d "$D/Dataset/RoboVid-SM/v02"
test -d "$D/external_datasets/AEGIS"
find "$D/Dataset/RoboVid-SM/v02" -type f -print -quit
printf 'prep_status=extracted_manifest_verified\n'