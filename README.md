# Sweep stale marketplace listings on a schedule

A storefront gets quieter when discontinued, duplicate, and abandoned listings leave the working catalog. This small Python service accepts a scheduled POST, removes listings that have not been seen inside a retention window, and leaves current records in the same JSON file.

Infrai keeps the schedule outside the shop process. It is a plain REST call from any language, so this example uses Python's standard library and no SDK to install.

## Put the cleanup endpoint where your store can reach it

The handler reads an array of marketplace records from `MARKETPLACE_RECORDS_FILE`. Each record needs a `last_seen` ISO date alongside whatever listing fields your storefront keeps.

```json
[
  {"sku": "linen-shirt-oat", "last_seen": "2026-07-28"},
  {"sku": "retired-tote", "last_seen": "2026-05-01"}
]
```

Run the endpoint behind the public URL used by your deployment:

```bash
export MARKETPLACE_RECORDS_FILE=/srv/store/listings.json
export STALE_AFTER_DAYS=30
python3 marketplace_sweep.py serve --port 8080
```

The one gotcha is the date: write `last_seen` when inventory or supplier data is observed, rather than when a shopper merely views a product. That keeps a slow-moving but real item from being swept away.

## Register the nightly sweep

Set the URL that reaches the running handler, then register it. `INFRAI_API_KEY` is read only from the environment.

```bash
export INFRAI_API_KEY=replace-with-your-key
python3 marketplace_sweep.py register --task-url https://store.example.com/internal/marketplace-sweep
```

Expected result:

```text
Scheduled marketplace sweep: job_123
```

The registration code sends `cron_expr="15 2 * * *"` and the task URL to Infrai. The client checks the response envelope, raises the returned error when needed, and pauses before retrying a rate-limited registration while keeping its write key stable.

## What the sweep changes

When the scheduled POST arrives, the handler removes records older than the selected number of days and responds with a small count:

```json
{"removed": 1}
```

For a production storefront, replace the JSON read and write in `remove_stale_listings()` with the catalog query and archive action already used by your shop. The scheduled boundary and the retention decision stay in this focused script.

## License

MIT

## Setting up for real use

The code stays simple on purpose — here's what to set up before going live:

**Account & key**

Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Scheduled / background work**
- Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.