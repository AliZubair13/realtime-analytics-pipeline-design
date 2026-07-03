# Architecture Diagram — Real-Time Analytics Pipeline

```mermaid
flowchart TD
    SDK[JS SDK unchanged ~50M events/day] --> AGW[API Gateway + edge auth / tenant tag]
    AGW --> KDS[Kinesis Data Streams on-demand, auto-scale - DURABLE BUFFER = spike absorber]
    KDS --> FLINK[Managed Service for Apache Flink - sessionize + segment + enrich]
    KDS --> FH[Kinesis Firehose]
    KDS -->|malformed| DLQ[(S3 Dead-Letter Queue - recoverable, replayable)]
    FLINK --> CH[(ClickHouse - HOT store, sub-sec queries, less than 5s dashboards)]
    FLINK --> RID[(Redis + DynamoDB - identity graph visitor_id to user_id)]
    RID --> FLINK
    FH --> S3[(S3 Parquet, by tenant/date - COLD store / source of truth)]
    CH --> DASH[Real-time dashboards + personalization triggers]
    CH --> GDPR[GDPR/CCPA deletion jobs by user_id, human-approved]
    S3 --> GDPR
    RID --> GDPR
    S3 --> WH[Customer warehouses Snowflake / BigQuery]
```

## ASCII fallback

```
JS SDK (unchanged, ~50M/day)
        |
   API Gateway  --(tenant tag, auth)-->
        |
   Kinesis Data Streams (on-demand)  <== DURABLE BUFFER: absorbs 10x spikes, replay source
        |
        |-- malformed --> S3 Dead-Letter Queue (recoverable, replayable)
        |
        |--> Kinesis Firehose --> S3 (Parquet, COLD, source of truth) --> Customer warehouses (Snowflake/BigQuery)
        |                                    |
        |                                    +--> GDPR/CCPA deletion jobs
        |
   Managed Flink (sessionize / segment / enrich)
        |   ^
        |   |  (reads identity back to stitch sessions)
        |   +--- Redis + DynamoDB (identity graph: visitor_id -> user_id) --> GDPR deletion
        |
        |--> ClickHouse (HOT, <5s dashboards) --> Real-time dashboards + personalization
                                              +--> GDPR/CCPA deletion jobs
```