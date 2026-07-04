# Real-Time Analytics Pipeline — Engineer-004 (Beat Claude)

**Candidate:** Zubair Ali Liyakath Ali
**Challenge:** Single Grain "Beat Claude" — Engineer-004 (System Design: Real-Time Analytics Pipeline)

A design for a real-time analytics pipeline handling 50M+ events/day with sub-5-second
dashboard latency, zero data loss under 10x traffic spikes, on AWS, within a $50K/month
budget — for a multi-tenant (500+) martech product.

The written answer is in `docs/answer.pdf`. This repo is the operating artifact: everything
here is inspectable with no login required.

## Contents

| Path | What it is | Proof tier |
|------|-----------|------------|
| `docs/answer.pdf` | The written answer (main submission) | — |
| `artifacts/architecture.md` | System diagram (Mermaid, renders on GitHub) + ASCII fallback | Tier 2 |
| `artifacts/architecture.jpg` | Rendered diagram image (also embedded in the PDF) | Tier 2 |
| `artifacts/cost_model.xlsx` | AWS cost model with live formulas + labeled assumptions | Tier 2 |
| `artifacts/capacity_output.txt` | Frozen console output of the ingestion simulation | Tier 2/3 |
| `scripts/simulate_ingestion.py` | Runnable proof: zero-loss ingestion under a 10x spike | Tier 2 |
| `scripts/build_cost_model.py` | Generates the cost model spreadsheet | — |
| `requirements.txt` | Python dependency (openpyxl) | — |

## Quick start

The simulation needs **no dependencies** (pure Python standard library):

```bash
python scripts/simulate_ingestion.py
```

Expected result — **0.0000% data loss** under a 10x spike (vs. the current system's 3%),
with every event reconciled:

Dropped / LOST                : 0
Reconciliation (all accounted): OK
DATA LOSS                     : 0.0000%   (current system: 3.0000%)


The frozen output of this run is saved in `artifacts/capacity_output.txt`.

## Rebuild the cost model (optional)

```bash
pip install -r requirements.txt
python scripts/build_cost_model.py      # writes artifacts/cost_model.xlsx
```

The model computes **~$8,400/month** against the **$50K ceiling** (~83% headroom), across
three sheets: Assumptions (editable inputs), Capacity (derived throughput/volume), and
Monthly Cost. Every input is labeled Observed / Estimated / Benchmarked / Assumed.

## Design summary

Managed AWS streaming — **Kinesis Data Streams** (durable buffer) → **Managed Flink**
(stateful processing) → **ClickHouse** (hot store, sub-5s dashboards), with a parallel
**Firehose → S3 (Parquet)** cold path for replay and warehouse export. Identity stitching
via **Redis + DynamoDB**; malformed events to an **S3 dead-letter queue**. Zero data loss
comes from at-least-once delivery + idempotent dedup (UUIDv7 event IDs) + the durable
buffer absorbing spikes.

The stack deliberately favors **operational simplicity for a 12-person team**. I argue
against self-managed Kafka from firsthand experience building a Kafka + Spark Streaming +
TimescaleDB pipeline:
[NYC Disease Surveillance](https://github.com/AliZubair13/BigDataNYCDiseaseSurveillance).

## Notes on evidence

All numbers in the written answer are labeled **[Observed] / [Estimated] / [Benchmarked] /
[Assumed]**. AWS unit prices are list-price approximations flagged for verification. The
simulation demonstrates the zero-loss *mechanism* at small scale, not a true 50M/day load
test. See the AI Usage Disclosure in `docs/answer.pdf` for how AI tools were used.