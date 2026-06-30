from __future__ import annotations

import argparse

from app.repositories.db import get_engine
from app.services.candidate_profile import CandidateProfileService
from app.web.app import create_app


def cmd_init(_args):
    get_engine().connect().close()
    print("Initialized database connectivity.")


def cmd_serve(args):
    app = create_app()
    app.run(host=args.host, port=args.port, debug=args.debug)


def cmd_worker(_args):
    print("Temporal worker scaffold is in place. Worker implementation is the next phase.")


def cmd_profile_refresh(_args):
    profile = CandidateProfileService().load()
    print(f"Loaded profile {profile.source_path} ({profile.content_hash[:16]})")


def cmd_stub(_args):
    print("Command scaffolded. Implementation will land in a later phase.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="head-hunter")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init")
    init_parser.set_defaults(func=cmd_init)

    serve_parser = subparsers.add_parser("serve")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=5000)
    serve_parser.add_argument("--debug", action="store_true")
    serve_parser.set_defaults(func=cmd_serve)

    worker_parser = subparsers.add_parser("worker")
    worker_parser.set_defaults(func=cmd_worker)

    profile_parser = subparsers.add_parser("profile")
    profile_sub = profile_parser.add_subparsers(dest="profile_command", required=True)
    profile_refresh = profile_sub.add_parser("refresh")
    profile_refresh.set_defaults(func=cmd_profile_refresh)

    scan_parser = subparsers.add_parser("scan")
    scan_sub = scan_parser.add_subparsers(dest="scan_command", required=True)
    for name in ["company", "block", "all"]:
        sub = scan_sub.add_parser(name)
        if name == "company":
            sub.add_argument("--company-id", required=False)
        if name == "block":
            sub.add_argument("--block", required=False)
        sub.set_defaults(func=cmd_stub)

    reseed_parser = subparsers.add_parser("reseed")
    reseed_parser.set_defaults(func=cmd_stub)

    digest_parser = subparsers.add_parser("digest")
    digest_sub = digest_parser.add_subparsers(dest="digest_command", required=True)
    weekly = digest_sub.add_parser("weekly")
    weekly.set_defaults(func=cmd_stub)

    for name in ["healthcheck"]:
        sub = subparsers.add_parser(name)
        sub.set_defaults(func=cmd_stub)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
