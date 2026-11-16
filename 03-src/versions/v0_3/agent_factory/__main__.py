import argparse
from .core import scout, report, init_db, verify_sources

parser=argparse.ArgumentParser(description="Agent Factory v0.3")
sub=parser.add_subparsers(dest="command",required=True)
sub.add_parser("init-db"); sub.add_parser("verify-sources"); sub.add_parser("scout"); sub.add_parser("report")
a=parser.parse_args()
{"init-db":init_db,"verify-sources":verify_sources,"scout":scout,"report":report}[a.command]()
