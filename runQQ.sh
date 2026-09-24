#!/usr/bin/env bash
# runQQ.sh <dest/> <a.sql> <b.sql>
outdir="$1"; a="$2"; b="$3"
mkdir -p "$outdir"
exec > >(tee "$outdir/all.log") 2>&1

mkdir -p tmp.qq
for sn in $(seq 1 12); do
  sed 's/${target_subnets:raw}/'"${sn}"'/g' "$a" > tmp.qq/sn${sn}.sql.a
  sed 's/${target_subnets:raw}/'"${sn}"'/g' "$b" > tmp.qq/sn${sn}.sql.b
  python3 qq.py tmp.qq/sn${sn}.sql.a tmp.qq/sn${sn}.sql.b > "$outdir/sn${sn}"
  echo "done sn${sn}"
done
rm -rf tmp.qq

fails=()
for f in "$outdir"/sn*; do
  grep -q 'VERDICT: IDENTICAL' "$f" || fails+=("$(basename "$f")")
done
if ((${#fails[@]})); then
  echo "FAILED (${#fails[@]}): ${fails[*]}"
else
  echo "all identical"
fi
echo "done → $outdir"

# #!/usr/bin/env bash
# # runQQ.sh <dest/> <a.sql> <b.sql>
# outdir="$1"; a="$2"; b="$3"
# mkdir -p "$outdir" tmp.qq
# for sn in $(seq 4 128); do
#   sed 's/${target_subnets:raw}/'"${sn}"'/g' "$a" > tmp.qq/sn${sn}.sql.a
#   sed 's/${target_subnets:raw}/'"${sn}"'/g' "$b" > tmp.qq/sn${sn}.sql.b
#   python3 qq.py tmp.qq/sn${sn}.sql.a tmp.qq/sn${sn}.sql.b > "$outdir/sn${sn}"
#   echo "done sn${sn}"
# done
# rm -rf tmp.qq

# # --- summary ---
# fails=()
# for f in "$outdir"/sn*; do
#   grep -q 'VERDICT: IDENTICAL' "$f" || fails+=("$(basename "$f")")
# done
# if ((${#fails[@]})); then
#   echo "FAILED (${#fails[@]}): ${fails[*]}"
# else
#   echo "all identical"
# fi
# echo "done → $outdir"
