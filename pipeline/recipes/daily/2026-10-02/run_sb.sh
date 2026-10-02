cd $(dirname $0)
for v in "$@"; do
  case $v in V19*) cmd="python3 /home/user/Higgsfield-test/pipeline/premium.py $v.json --out out/videos/$v.mp4";; V20*) cmd="python3 /home/user/Higgsfield-test/pipeline/remix.py $v.json --out out/videos/$v.mp4";; *) cmd="python3 /home/user/Higgsfield-test/pipeline/storyboard.py $v.json --out out/videos/$v.mp4";; esac
  $cmd > logs_$v.txt 2>&1 && echo "OK $v" || echo "FAIL $v"
done
