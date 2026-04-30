# Aurora DSQL Cost Estimation

This guide helps estimate Aurora DSQL costs based on workload characteristics. DSQL pricing consists of four components: Compute DPUs, Read DPUs, Write DPUs, and Storage.

## Quick Reference

**For pre-deployment estimates (no cluster yet):**

1. Collect: Region, Read TPS, Write TPS, Data Size (GB)
2. Query `awspricing` for region-specific DPU + Storage pricing
3. Use Default DPU Values (see below) if customer has no EXPLAIN ANALYZE data
4. Calculate monthly costs using formulas in this doc

**For existing clusters:**

1. Run MCP queries (see bottom of doc) to gather actual workload stats
2. Use EXPLAIN ANALYZE to get real DPU consumption per query
3. Calculate costs using measured values

**Most important:** Always query `awspricing` first - pricing varies 25% across regions.

---

## Pricing Components

### DPU (Database Processing Unit) Pricing

- **Price per DPU**: Varies by AWS region (use `awspricing` MCP server for current rates)
- **DPU Types**:
  - **Compute DPUs**: Transaction processing and commit overhead
  - **Read DPUs**: SELECT query processing
  - **Write DPUs**: INSERT/UPDATE/DELETE operations
  - **Multi-Region Write DPUs**: Additional cost for multi-region writes

### Storage Pricing

- **Price per GB-month**: Varies by AWS region (use `awspricing` MCP server for current rates)

### Regional Pricing Reference

**IMPORTANT**: Always query the `awspricing` MCP server for current pricing. The table below is for reference only and may be outdated.

| Region                      | Region Code    | DPU Price (per DPU) | Storage (per GB-Month) |
|-----------------------------|----------------|---------------------|------------------------|
| US East (N. Virginia)       | us-east-1      | $0.0000080          | $0.33                  |
| US East (Ohio)              | us-east-2      | $0.0000080          | $0.33                  |
| US West (Oregon)            | us-west-2      | $0.0000080          | $0.33                  |
| EU (Frankfurt)              | eu-central-1   | $0.0000095          | $0.45                  |
| EU (Ireland)                | eu-west-1      | $0.0000095          | $0.36                  |
| EU (London)                 | eu-west-2      | $0.0000095          | $0.45                  |
| EU (Paris)                  | eu-west-3      | $0.0000095          | $0.45                  |
| Asia Pacific (Tokyo)        | ap-northeast-1 | $0.0000100          | $0.40                  |
| Asia Pacific (Seoul)        | ap-northeast-2 | $0.0000100          | $0.40                  |
| Asia Pacific (Osaka)        | ap-northeast-3 | $0.0000100          | $0.40                  |
| Asia Pacific (Sydney)       | ap-southeast-2 | $0.0000090          | $0.36                  |
| Asia Pacific (Melbourne)    | ap-southeast-4 | $0.0000090          | $0.36                  |
| Canada (Central)            | ca-central-1   | $0.0000090          | $0.36                  |
| Canada West (Calgary)       | ca-west-1      | $0.0000090          | $0.36                  |

**Regional Pricing Ranges:**

- DPU Pricing: $0.000008 (US) to $0.00001 (AP Tokyo/Seoul/Osaka) per DPU
- Storage Pricing: $0.33 (US) to $0.45 (EU Frankfurt/London/Paris) per GB-Month

### Cost Factors

| Factor                | Unit      | Description                                       |
|-----------------------|-----------|---------------------------------------------------|
| **Writer Factor**     | 0.14      | Percentage of compute time for write transactions |
| **Reader Factor**     | 0.86      | Percentage of compute time for read transactions  |
| **Write DPU Factor**  | 0.05      | DPU cost multiplier for write operations          |
| **Read DPU Factor**   | 0.00375   | DPU cost multiplier for read operations           |
| **Seconds per Month** | 2,626,560 | Conversion factor for monthly calculations        |

---

## Cost Estimation Formulas

### 1. Write Transaction Costs

**Write DPUs per Transaction:**

```
Write DPUs = (
  # Rows Changed × Avg Write Statement Size × Write DPU Factor +
  # Index Statements × Avg Index Statement Size × Write DPU Factor
) / 1000
```

**Read DPUs per Write Transaction** (for reading before writing):

```
Read DPUs = (Read Statements × Avg Read Size × Read DPU Factor) / 1000
```

**Compute DPUs per Write Transaction:**

```
Compute DPUs = Commit Latency (ms) × Writer Factor × 0.001
```

**Monthly Write Costs:**

```
Monthly Write DPUs = Write TPS × Seconds per Month × Write DPUs per Txn
Monthly Read DPUs (in Write) = Write TPS × Seconds per Month × Read DPUs per Txn
Monthly Compute DPUs = Write TPS × Seconds per Month × Compute DPUs per Txn

Write Cost = Monthly Write DPUs × Region DPU Price
Read Cost = Monthly Read DPUs × Region DPU Price
Compute Cost = Monthly Compute DPUs × Region DPU Price
```

### 2. Read Transaction Costs

**Read DPUs per Transaction:**

```
Read DPUs = (
  # Rows Scanned × Avg Row Size +
  # Secondary Index Lookups × Avg Index Lookup Size
) × Read DPU Factor / 1000
```

**Compute DPUs per Read Transaction:**

```
Compute DPUs = Commit Latency (ms) × Reader Factor × 0.001
```

**Monthly Read Costs:**

```
Monthly Read DPUs = Read TPS × Seconds per Month × Read DPUs per Txn
Monthly Compute DPUs = Read TPS × Seconds per Month × Compute DPUs per Txn

Read Cost = Monthly Read DPUs × Region DPU Price
Compute Cost = Monthly Compute DPUs × Region DPU Price
```

### 3. Storage Costs

**Total Cluster Size:**

```
Total Size (TB) = (Data Size per Partition + Index Size per Partition) × # Shards
Total Size (GB) = Total Size (TB) × 1024

Monthly Storage Cost = Total Size (GB) × Region Storage Price
```

**Estimating Data and Index Size:**

```
Data Size (GB) = (Total Rows × Avg Row Size) / (1024³)
Index Size (GB) = Data Size × (# Indexes / # Tables) × 1.66
  (1.66 factor accounts for index overhead observed in production)
```

### 4. Multi-Region Write Costs

**NOTE:** Multi-Region Write DPUs only apply to **multi-region clusters**. Single-region clusters do NOT incur this cost.

For multi-region clusters, writes are replicated across regions and incur additional DPU costs:

```
MR-Write DPUs = Write DPUs per Transaction (same as single-region)
Monthly MR-Write Cost = Monthly Write DPUs × Region DPU Price
```

---

### When to Use Formulas vs. Default Values

**Use the formulas above if:**

- Customer provides specific query characteristics (exact rows scanned, statement sizes, etc.)
- Customer has EXPLAIN ANALYZE output showing DPU consumption
- You need to model "what-if" scenarios with varying parameters

**Use Default DPU Values (section below) if:**

- Customer is in planning phase with no cluster
- Customer doesn't know query-level details yet
- You need a quick ballpark estimate

Default values are empirically derived from typical workloads - they represent the formulas already applied to common patterns.

---

## How to Query Current Pricing

### Using awspricing MCP Server

**ALWAYS query `awspricing` for current regional pricing before calculating costs.**

The Aurora DSQL service code is `AuroraDSQL`. Query for both DPU and Storage pricing:

**Query DPU Pricing:**

```
Service: AuroraDSQL
Filter: usagetype contains "DistributedProcessingUnits"
Filter: regionCode = <target-region>
Example: regionCode = "us-east-1"
```

**Query Storage Pricing:**

```
Service: AuroraDSQL
Filter: usagetype contains "Storage"
Filter: regionCode = <target-region>
Example: regionCode = "us-east-1"
```

**Expected Results:**

- DPU pricing returned as price per DPU (e.g., $0.000008)
- Storage pricing returned as price per GB-Month (e.g., $0.33)

---

## Default DPU Values for Estimation

When customers don't have access to a running DSQL cluster to measure actual DPU consumption with EXPLAIN ANALYZE, use these empirically-derived default values:

| Metric                                | Default Value | Basis                                                                      |
|---------------------------------------|---------------|----------------------------------------------------------------------------|
| Write DPUs per Transaction            | 0.063         | Rough estimate: average write with 2 rows changed, 4 index updates         |
| Read DPUs per Transaction (in writes) | 0.00047       | Rough estimate: average of 2 read statements per write transaction         |
| Compute DPUs per Transaction (writes) | 0.026         | Estimate based on 26ms commit latency for average write transaction        |
| Compute DPUs per Transaction (reads)  | 0.003         | Estimate based on 3ms commit latency for average read transaction          |

### When to Use These Defaults

**Use defaults when:**

- Customer is in pre-deployment planning phase (no cluster yet)
- Customer wants ballpark estimates without EXPLAIN ANALYZE
- Customer has similar workload characteristics (small-to-medium transactions, typical index density)

**Use measured values when:**

- Customer has a running DSQL cluster
- Customer can provide EXPLAIN ANALYZE output from their actual queries
- Customer has unusual workload patterns (very large transactions, complex queries, minimal indexes)

### Workload Assumptions Behind Defaults

These defaults assume typical OLTP workload patterns:

- **Write transactions:** 2 rows changed, 4 indexes updated, 2 read statements before writing
- **Read transactions:** 50 rows scanned per SELECT, 2 secondary index lookups
- **Commit latency:** 26ms for writes, 3ms for reads (based on observed p50 latencies)

For workloads significantly different from these patterns, adjust the defaults or collect actual measurements.

---

## Required Inputs for Cost Estimation

### Region Selection

- **AWS Region**: Target deployment region (e.g., us-east-1, eu-west-1, ap-northeast-1)
  - **MUST be collected FIRST** before calculating costs
  - Query `awspricing` MCP server for region-specific DPU and Storage pricing

### General Cluster Characteristics

- **Number of shards**: Cluster parallelism (default: 11 for small workloads)
- **Number of tables**: Schema complexity
- **Number of indexes**: Total across all tables
- **Average indexes per table**: Index density (typically 3-5)
- **Average row size (bytes)**: Including all columns
- **Total rows**: Current or projected row count
- **Data size per partition (TB)**: Raw data per shard
- **Index size per partition (TB)**: Index data per shard

### Write Workload Characteristics

- **Average Write TPS**: Transactions per second (INSERT/UPDATE/DELETE)
- **Rows changed per transaction**: Typical batch size
- **Average write statement size (bytes)**: Payload size per statement (default: 128)
- **Average index statements per write**: Indexes updated (default: avg indexes per table)
- **Average index statement size (bytes)**: Index update payload (default: 128)
- **Commit latency for writes (ms)**: Transaction overhead (default: 26ms)

### Read Workload Characteristics

- **Average Read TPS**: SELECT queries per second
- **Read statements per transaction**: Queries per transaction (default: 1-2)
- **Average rows scanned per SELECT**: Query scan size
- **Average rows returned per SELECT**: Result set size
- **Average row size (bytes)**: For reads
- **Secondary index lookups per SELECT**: Index access count (default: 2)
- **Average index lookup size (bytes)**: Index payload (default: 128)
- **Commit latency for reads (ms)**: Transaction overhead (default: 3ms)

---

## Example: Read-Heavy OLTP Workload

**Note:** Always query `awspricing` for current regional rates. This example uses us-east-1 pricing.

### Scenario

- **Scale:** 25.5B rows, 81TB storage, 1.1M read TPS, 7.4K write TPS
- **Use case:** High-traffic multi-tenant SaaS application
- **Region:** us-east-1 (DPU: $0.000008, Storage: $0.33/GB-Month)

### Input Parameters

| Category           | Parameters                                                                                          |
|--------------------|---------------------------------------------------------------------------------------------------- |
| **Cluster**        | 11 shards, 438 tables, 1,765 indexes (4.03 avg per table)                                           |
| **Data**           | 25.5B rows, 116 bytes avg row size, 81.03TB total (2.77TB data + 4.60TB indexes per partition)      |
| **Write Workload** | 7,457 TPS, 2 rows/txn, 4.03 index updates/txn, 26ms commit latency                                  |
| **Read Workload**  | 1,117,083 TPS, 50 rows scanned/query, 2 index lookups/query, 3ms commit latency                     |

### Monthly Cost Breakdown

| Cost Component   | Monthly Cost | % of Total | Notes                   |
|------------------|--------------|------------|-------------------------|
| Read DPUs        | $260,558     | 68%        | Dominant cost driver    |
| Compute DPUs     | $74,511      | 19%        | Transaction overhead    |
| Write DPUs       | $19,702      | 5%         | Includes MR-Write DPUs  |
| Storage (81TB)   | $27,382      | 7%         | Data + indexes          |
| **TOTAL**        | **$382,153** | **100%**   |                         |

**Key Insight:** Read DPUs dominate costs (68%). Adding indexes to reduce table scans could save significant costs with query optimizations.

### Regional Variance

Same workload in **eu-central-1** (DPU: $0.0000095, Storage: $0.45/GB-Month):

- **Total: $458,630/month** (+20% due to higher DPU and storage prices)
  - DPU costs: $421,291/month (+18.8%)
  - Storage: $37,339/month (+36.4%)

### Fleet-Wide Extrapolation

If this represents 1/3 of your fleet (3.1M read TPS, 64K write TPS total):

- **Extrapolated cost: ~$1.5M/month**

---

## Cost Optimization Strategies

### 1. Reduce Read DPUs

- **Add indexes** for frequently scanned columns
- **Minimize rows scanned** with precise WHERE clauses
- **Use covering indexes** to avoid table lookups
- **Partition large tables** by tenant_id or date

### 2. Reduce Write DPUs

- **Batch writes** (up to 3,000 rows per transaction)
- **Reduce index count** (only create necessary indexes)
- **Use async indexes** (`CREATE INDEX ASYNC`)
- **Optimize row size** by storing large data externally (S3)

### 3. Reduce Storage Costs

- **Archive old data** to S3 with lifecycle policies
- **Compress large columns** (JSON, TEXT)
- **Drop unused indexes**
- **Use appropriate data types** (SMALLINT vs BIGINT)

### 4. Right-Size Compute

- **Monitor actual latency** (may be lower than defaults)
- **Optimize transaction scope** (fewer statements per txn)
- **Use connection pooling** to reduce connection overhead

---

## Cost Estimation Workflow

When a user requests cost estimation, follow this workflow to provide accurate estimates:

### Phase 0: Understand Schema Context and Collect Region

**ALWAYS start by asking for region AND schema context:**

1. **"Which AWS region are you planning to deploy in?"** (e.g., us-east-1, eu-west-1, ap-northeast-1)
2. **Query `awspricing` immediately** to get current DPU and Storage pricing for that region
3. **"Do you have existing schemas and query patterns you'd like to cost out, or would you like help designing an optimal DSQL schema first?"**

**If they have existing schemas:**

1. Ask them to share:
   - Table schemas (CREATE TABLE statements)
   - Top 5-10 most frequent queries
   - Current database type (MySQL, PostgreSQL, etc.)
2. Offer to help translate and optimize for DSQL:
   - "Would you like me to translate these to DSQL-optimized schemas?"
   - "I can suggest index improvements to reduce costs"
3. Analyze their queries to determine:
   - Actual rows scanned per query
   - Index usage patterns
   - Missing indexes that cause table scans

**If they need help designing schemas:**

1. Ask about their use case:
   - "What kind of application are you building?"
   - "Multi-tenant SaaS, e-commerce, IoT, social platform, etc.?"
2. Design DSQL-optimized schemas with proper indexes
3. Generate realistic query patterns for their use case
4. Calculate costs based on the optimized design

### Phase 1: Gather Workload Metrics

After understanding their schema context, collect:

**Essential:**

1. **Average Read TPS** (or expected queries per second)
2. **Average Write TPS** (or expected writes per second)
3. **Data size** (current or projected in GB)

**From Schema Analysis:**
4. **Number of tables** (from their schemas or design)
5. **Number of indexes** (from their schemas or optimized design)
6. **Average rows scanned per query** (analyze their actual queries)
7. **Average rows changed per write** (from their write patterns)

### Phase 2: Calculate Accurate Costs

Use the gathered schema and query information to calculate:

- **Read DPUs** based on actual query scan patterns
- **Write DPUs** based on index count and write patterns
- **Compute DPUs** for transaction overhead
- **Storage costs** for data + indexes

### Phase 3: Provide Recommendations

Based on calculated costs:

- Highlight the largest cost driver
- Suggest specific optimizations:
  - Missing indexes (if analyzing existing schemas)
  - Query rewrites to reduce scans
  - Schema denormalization opportunities
- Show cost impact of each optimization
- Compare against their current database costs if available

---

## MCP Tool Integration

When connected to a DSQL cluster, use these queries to gather actual workload data:

### Get Table Statistics

```sql
SELECT 
  schemaname,
  tablename,
  n_tup_ins AS inserts,
  n_tup_upd AS updates,
  n_tup_del AS deletes,
  n_live_tup AS live_rows,
  n_dead_tup AS dead_rows
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC;
```

### Get Index Usage

```sql
SELECT
  schemaname,
  tablename,
  indexname,
  idx_scan AS scans,
  idx_tup_read AS tuples_read,
  idx_tup_fetch AS tuples_fetched
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

### Get Database Size

```sql
SELECT
  pg_size_pretty(pg_database_size(current_database())) AS db_size,
  pg_database_size(current_database()) / (1024.0 * 1024.0 * 1024.0) AS size_gb;
```

### Get Table Sizes

```sql
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
  pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
  pg_size_pretty(pg_indexes_size(schemaname||'.'||tablename)) AS indexes_size
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## Common Pitfalls

1. **Using wrong regional pricing**: Pricing varies significantly by region (DPU: $0.000008-$0.00001, Storage: $0.33-$0.45). Always query `awspricing` for the target region.
2. **Underestimating read TPS**: Read traffic is often 100-1000× write traffic
3. **Ignoring index overhead**: Indexes add ~40-60% to storage and write costs
4. **Forgetting compute costs**: Commit latency adds up at high TPS
5. **Not accounting for multi-region**: MR writes double write DPU costs
6. **Poor index design**: Missing indexes cause table scans and dramatically increase read DPU costs

---

## Agent Guidance: Common Estimation Mistakes

When helping customers with cost estimates, follow these best practices:

**✅ DO:**

- Always state "This estimate assumes..." with key assumptions listed
- Call out the biggest cost driver and optimization opportunity
- Offer to refine estimates if customer provides schema/queries
- Mention that EXPLAIN ANALYZE gives more accurate estimates once cluster exists
- Compare to customer's current database costs if available
- Emphasize that these are rough estimates (+/- 30%) until real workload data is available

**Best Practice Flow:**

1. Query `awspricing` for region → Get current DPU + Storage prices
2. Collect workload metrics → TPS, data size, basic query patterns
3. Use Default DPU Values → Apply to workload metrics
4. Calculate and present → Show cost breakdown with largest driver highlighted
5. Suggest optimizations → Specific to their cost drivers (e.g., add indexes if read-heavy)
6. Set expectations → "EXPLAIN ANALYZE on real queries will provide more accurate results"

---

## References

- [Aurora DSQL Pricing](https://aws.amazon.com/rds/aurora/dsql-pricing/)
- [DSQL Performance Best Practices](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/performance.html)
- [DSQL Query Optimization](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/query-optimization.html)
