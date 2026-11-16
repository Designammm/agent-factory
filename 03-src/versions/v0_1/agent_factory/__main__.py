import argparse
from .core import scout, report

parser = argparse.ArgumentParser()
sub = parser.add_subparsers(dest="command", required=True)
sub.add_parser("scout")
sub.add_parser("report")
args = parser.parse_args()

if args.command == "scout":
    scout()
else:
    report()
