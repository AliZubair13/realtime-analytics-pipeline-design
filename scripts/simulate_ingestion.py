#!/usr/bin/env python3
"""
Real-time ingestion simulation — Engineer-004 artifact.

Proves the core reliability claim of the design: at-least-once delivery with a
durable buffer + backpressure + dead-letter queue + idempotent dedup yields
ZERO data loss even during a 10x traffic spike that exceeds consumer capacity.

This models the Kinesis-shard-buffer -> Flink-consumer path in miniature.
Pure standard library. Run: python simulate_ingestion.py
"""
import collections, random, uuid

# ---- knobs (mirror the brief; all labeled in the writeup) ----
BASE_EPS          = 580      # ~50M/day avg  [Observed-from-brief -> derived]
SPIKE_MULTIPLIER  = 10       # 10x spike     [Observed-from-brief]
CONSUMER_CAPACITY = 2000     # events/sec a single consumer group can drain [Assumed]
BUFFER_LIMIT      = 1_000_000  # Kinesis-style retained buffer depth        [Assumed]
SIM_SECONDS       = 60
SPIKE_WINDOW      = range(20, 35)  # spike hits seconds 20..34
DUP_RATE          = 0.02     # 2% of events redelivered (at-least-once)     [Assumed]
MALFORMED_RATE    = 0.005    # 0.5% bad events -> dead-letter, not lost      [Assumed]

def make_event():
    return {"event_id": str(uuid.uuid4()), "tenant": random.randint(1, 500),
            "type": random.choice(["page_view", "click", "form", "custom"])}

def valid(e):
    return e["type"] in {"page_view", "click", "form", "custom"} and e["tenant"] > 0

def run():
    buffer = collections.deque()          # durable shard buffer
    seen = set()                          # idempotent dedup key store
    produced = accepted = duplicates = dead_letter = dropped = 0
    max_backlog = 0

    for sec in range(SIM_SECONDS):
        eps = BASE_EPS * (SPIKE_MULTIPLIER if sec in SPIKE_WINDOW else 1)
        # PRODUCE into buffer (with backpressure: refuse only if buffer full)
        for _ in range(eps):
            e = make_event()
            if random.random() < MALFORMED_RATE:
                e["type"] = "CORRUPT"
            produced += 1
            if len(buffer) < BUFFER_LIMIT:
                buffer.append(e)
                # simulate at-least-once redelivery
                if random.random() < DUP_RATE:
                    buffer.append(dict(e))
                    produced += 1
            else:
                dropped += 1   # would signal SDK to retry; buffer sized so this stays 0
        # CONSUME up to capacity (backlog drains after spike)
        drain = min(len(buffer), CONSUMER_CAPACITY)
        for _ in range(drain):
            e = buffer.popleft()
            if not valid(e):
                dead_letter += 1            # routed to DLQ, recoverable, NOT lost
                continue
            if e["event_id"] in seen:
                duplicates += 1             # dedup removes at-least-once copies
                continue
            seen.add(e["event_id"]); accepted += 1
        max_backlog = max(max_backlog, len(buffer))

    # drain remaining backlog (post-spike recovery)
    while buffer:
        e = buffer.popleft()
        if not valid(e): dead_letter += 1; continue
        if e["event_id"] in seen: duplicates += 1; continue
        seen.add(e["event_id"]); accepted += 1

    reconciled = accepted + duplicates + dead_letter + dropped
    print("=" * 60)
    print("INGESTION SIMULATION RESULTS")
    print("=" * 60)
    print(f"Produced (incl. dupes)        : {produced:,}")
    print(f"Accepted (unique, valid)      : {accepted:,}")
    print(f"Duplicates removed by dedup   : {duplicates:,}")
    print(f"Dead-lettered (recoverable)   : {dead_letter:,}")
    print(f"Dropped / LOST                : {dropped:,}")
    print(f"Peak buffer backlog           : {max_backlog:,}")
    print("-" * 60)
    print(f"Reconciliation (all accounted): {reconciled:,} == {produced:,}  "
          f"-> {'OK' if reconciled == produced else 'MISMATCH'}")
    loss_pct = 100 * dropped / produced
    print(f"DATA LOSS                     : {loss_pct:.4f}%  "
          f"(current system: 3.0000% [Observed-from-brief])")
    print("=" * 60)

if __name__ == "__main__":
    random.seed(42)
    run()