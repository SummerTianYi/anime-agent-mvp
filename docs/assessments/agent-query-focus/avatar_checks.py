"""Add the public-query expression test to the isolated full-scene gates."""
from argparse import ArgumentParser
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"agent-query-delivery"))
import godot_checks


if __name__=="__main__":
    p=ArgumentParser(description=__doc__)
    for name in ("godot","assets","out"):
        p.add_argument(name,type=Path)
    p.add_argument("--expression-only",action="store_true")
    args=p.parse_args()
    if args.expression_only:
        godot_checks.GATES={}
    else:
        godot_checks.GATES["verify_emotion_presets"]="GODOT_EMOTION_PRESETS_PASS"
    godot_checks.GATES["verify_query_expression"]="QUERY_EXPRESSION_OK"
    raise SystemExit(0 if godot_checks.run(args) else 1)
