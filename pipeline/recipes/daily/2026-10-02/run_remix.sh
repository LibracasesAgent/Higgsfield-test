cd $(dirname $0)
for v in "$@"; do python3 /home/user/Higgsfield-test/pipeline/remix.py $v.json --out out/videos/$v.mp4 > logs_$v.txt 2>&1 && echo "OK $v" || echo "FAIL $v"; done
