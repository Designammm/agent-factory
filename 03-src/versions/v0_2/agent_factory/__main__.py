import argparse
from .core import scout, report, init_db, verify_sources

parser = argparse.ArgumentParser(description="Agent Factory v0.2")
sub = parser.add_subparsers(dest="command", required=True)
sub.add_parser("init-db", help="Create/update the local database schema")
sub.add_parser("verify-sources", help="Check configured source endpoints without collecting data")
sub.add_parser("scout", help="Collect public evidence and build candidates")
sub.add_parser("report", help="Print current agent intelligence report")
args = parser.parse_args()

if args.command == "init-db":
    init_db()
elif args.command == "verify-sources":
    verify_sources()
elif args.command == "scout":
    scout()
else:
    report()
