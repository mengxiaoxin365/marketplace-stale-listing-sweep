"""Register and serve a periodic sweep for stale marketplace listings."""
import argparse
import json
import os
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import infrai_client as infrai


def remove_stale_listings(records_path: Path, stale_after_days: int) -> int:
    """Remove listings whose last_seen date is older than the chosen retention window."""
    records = json.loads(records_path.read_text())
    cutoff = date.today() - timedelta(days=stale_after_days)
    current = [
        record
        for record in records
        if date.fromisoformat(record["last_seen"]) >= cutoff
    ]
    records_path.write_text(json.dumps(current, indent=2) + "\n")
    return len(records) - len(current)


def register_sweep(task_url: str) -> str:
    job = infrai.cron.create(cron_expr="15 2 * * *", task=task_url)
    return job["job_id"]


class SweepHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        removed = remove_stale_listings(
            Path(os.environ["MARKETPLACE_RECORDS_FILE"]),
            int(os.environ.get("STALE_AFTER_DAYS", "30")),
        )
        body = json.dumps({"removed": removed}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="Marketplace listing cleanup")
    subcommands = parser.add_subparsers(dest="command", required=True)
    register = subcommands.add_parser("register")
    register.add_argument("--task-url", required=True)
    serve = subcommands.add_parser("serve")
    serve.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    if args.command == "register":
        print(f"Scheduled marketplace sweep: {register_sweep(args.task_url)}")
        return

    server = HTTPServer(("0.0.0.0", args.port), SweepHandler)
    print(f"Marketplace sweep listening on port {args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
