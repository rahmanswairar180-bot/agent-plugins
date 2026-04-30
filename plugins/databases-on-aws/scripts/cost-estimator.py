#!/usr/bin/env python3
"""
Aurora DSQL Cost Estimator

Calculates monthly costs for Aurora DSQL workloads based on:
- Compute DPUs (read + write transaction processing)
- Read DPUs (SELECT operations)
- Write DPUs (INSERT/UPDATE/DELETE + index updates)
- Storage (data + indexes)

Usage:
    ./cost-estimator.py --interactive
    ./cost-estimator.py --read-tps 1000000 --write-tps 5000 --data-gb 1000
    ./cost-estimator.py --help
"""

import argparse
import sys
from dataclasses import dataclass
from typing import Optional


# Constants
SECONDS_PER_MONTH = 2_626_560
PRICE_PER_DPU_MS = 0.000008
STORAGE_PRICE_PER_GB = 0.15
WRITER_FACTOR = 0.14
READER_FACTOR = 0.86
WRITE_DPU_FACTOR = 0.05
READ_DPU_FACTOR = 0.00375


@dataclass
class WorkloadConfig:
    """Configuration for DSQL workload characteristics"""
    num_shards: int = 11
    num_tables: int = 100
    num_indexes: int = 400
    avg_row_size_bytes: int = 128
    write_tps: float = 1000
    read_tps: float = 10000
    data_gb: float = 1000
    rows_changed_per_write: int = 2
    rows_scanned_per_select: int = 100
    secondary_index_lookups: int = 2
    write_commit_latency_ms: float = 26.0
    read_commit_latency_ms: float = 3.0
    read_statements_per_write: int = 2
    avg_write_stmt_size: int = 128
    avg_read_size_in_write: int = 128
    avg_index_stmt_size: int = 128
    avg_index_lookup_size: int = 128


@dataclass
class CostBreakdown:
    """Monthly cost breakdown for DSQL"""
    write_cost: float
    write_read_cost: float
    write_compute_cost: float
    read_cost: float
    read_compute_cost: float
    mr_write_cost: float
    storage_cost: float
    total_cost: float
    total_cluster_size_gb: float

    # DPU milliseconds for reference
    write_dpu_ms: float
    write_read_dpu_ms: float
    write_compute_dpu_ms: float
    read_dpu_ms: float
    read_compute_dpu_ms: float
    mr_write_dpu_ms: float


def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Estimate Aurora DSQL monthly costs based on workload characteristics.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  %(prog)s --interactive

  # Quick estimate
  %(prog)s --read-tps 1000000 --write-tps 5000 --data-gb 1000

  # Detailed estimate
  %(prog)s --read-tps 500000 --write-tps 10000 --data-gb 5000 \\
    --num-shards 20 --rows-scanned 200
        """
    )

    parser.add_argument(
        '-i', '--interactive',
        action='store_true',
        help='Interactive mode (prompts for inputs)'
    )
    parser.add_argument(
        '--read-tps',
        type=float,
        help='Read transactions per second (default: 10000)'
    )
    parser.add_argument(
        '--write-tps',
        type=float,
        help='Write transactions per second (default: 1000)'
    )
    parser.add_argument(
        '--data-gb',
        type=float,
        help='Total data size in GB (default: 1000)'
    )
    parser.add_argument(
        '--num-shards',
        type=int,
        help='Number of shards (default: 11)'
    )
    parser.add_argument(
        '--num-tables',
        type=int,
        help='Number of tables (default: 100)'
    )
    parser.add_argument(
        '--num-indexes',
        type=int,
        help='Number of indexes (default: 400)'
    )
    parser.add_argument(
        '--rows-changed',
        type=int,
        help='Rows changed per write txn (default: 2)'
    )
    parser.add_argument(
        '--rows-scanned',
        type=int,
        help='Rows scanned per SELECT (default: 100)'
    )

    return parser.parse_args()


def prompt_input(prompt: str, default: any, input_type=str) -> any:
    """Prompt for input with default value"""
    try:
        user_input = input(f"{prompt} [{default}]: ").strip()
        if not user_input:
            return default
        return input_type(user_input)
    except (ValueError, KeyboardInterrupt):
        return default


def interactive_mode() -> WorkloadConfig:
    """Interactive mode for gathering inputs"""
    print()
    print("=" * 80)
    print("Aurora DSQL Cost Estimator - Interactive Mode")
    print("=" * 80)
    print()
    print("Press Enter to use default values shown in [brackets]")
    print()

    config = WorkloadConfig()

    config.read_tps = prompt_input(
        "Read TPS (SELECT queries per second)",
        config.read_tps,
        float
    )
    config.write_tps = prompt_input(
        "Write TPS (INSERT/UPDATE/DELETE per second)",
        config.write_tps,
        float
    )

    print()
    print("--- Data Size ---")
    config.data_gb = prompt_input(
        "Total data size (GB)",
        config.data_gb,
        float
    )
    config.num_shards = prompt_input(
        "Number of shards",
        config.num_shards,
        int
    )
    config.num_tables = prompt_input(
        "Number of tables",
        config.num_tables,
        int
    )
    config.num_indexes = prompt_input(
        "Number of indexes",
        config.num_indexes,
        int
    )

    print()
    use_defaults = prompt_input(
        "Use default values for advanced options? [Y/n]",
        "Y",
        str
    )

    if use_defaults.lower() not in ['n', 'no']:
        return config

    print()
    print("--- Advanced Options ---")
    config.avg_row_size_bytes = prompt_input(
        "Average row size (bytes)",
        config.avg_row_size_bytes,
        int
    )
    config.rows_scanned_per_select = prompt_input(
        "Rows scanned per SELECT",
        config.rows_scanned_per_select,
        int
    )
    config.rows_changed_per_write = prompt_input(
        "Rows changed per write transaction",
        config.rows_changed_per_write,
        int
    )

    return config


def calculate_costs(config: WorkloadConfig) -> CostBreakdown:
    """Calculate DSQL costs based on workload configuration"""

    # Calculate derived values
    avg_indexes_per_table = config.num_indexes / config.num_tables
    data_per_partition_tb = config.data_gb / config.num_shards / 1024
    index_per_partition_tb = data_per_partition_tb * 1.7
    total_cluster_size_tb = (data_per_partition_tb + index_per_partition_tb) * config.num_shards
    total_cluster_size_gb = total_cluster_size_tb * 1024

    # Write DPUs per transaction
    write_dpu_per_txn = (
        config.rows_changed_per_write * config.avg_write_stmt_size * WRITE_DPU_FACTOR +
        avg_indexes_per_table * config.avg_index_stmt_size * WRITE_DPU_FACTOR
    ) / 1000

    # Read DPUs in write transactions
    read_dpu_in_write_per_txn = (
        config.read_statements_per_write * config.avg_read_size_in_write * READ_DPU_FACTOR
    ) / 1000

    # Compute DPUs for write transactions
    compute_dpu_write_per_txn = config.write_commit_latency_ms * WRITER_FACTOR / 1000

    # Monthly write DPUs
    write_dpu_ms = config.write_tps * SECONDS_PER_MONTH * write_dpu_per_txn
    write_read_dpu_ms = config.write_tps * SECONDS_PER_MONTH * read_dpu_in_write_per_txn
    write_compute_dpu_ms = config.write_tps * SECONDS_PER_MONTH * compute_dpu_write_per_txn
    mr_write_dpu_ms = write_dpu_ms

    # Read DPUs per transaction
    read_dpu_per_txn = (
        config.rows_scanned_per_select * config.avg_row_size_bytes * READ_DPU_FACTOR +
        config.secondary_index_lookups * config.avg_index_lookup_size * READ_DPU_FACTOR
    ) / 1000

    # Compute DPUs for read transactions
    compute_dpu_read_per_txn = config.read_commit_latency_ms * READER_FACTOR / 1000

    # Monthly read DPUs
    read_dpu_ms = config.read_tps * SECONDS_PER_MONTH * read_dpu_per_txn
    read_compute_dpu_ms = config.read_tps * SECONDS_PER_MONTH * compute_dpu_read_per_txn

    # Calculate costs
    write_cost = write_dpu_ms * PRICE_PER_DPU_MS
    write_read_cost = write_read_dpu_ms * PRICE_PER_DPU_MS
    write_compute_cost = write_compute_dpu_ms * PRICE_PER_DPU_MS
    read_cost = read_dpu_ms * PRICE_PER_DPU_MS
    read_compute_cost = read_compute_dpu_ms * PRICE_PER_DPU_MS
    mr_write_cost = mr_write_dpu_ms * PRICE_PER_DPU_MS
    storage_cost = total_cluster_size_gb * STORAGE_PRICE_PER_GB
    total_cost = (
        write_cost + write_read_cost + write_compute_cost +
        read_cost + read_compute_cost + mr_write_cost + storage_cost
    )

    return CostBreakdown(
        write_cost=write_cost,
        write_read_cost=write_read_cost,
        write_compute_cost=write_compute_cost,
        read_cost=read_cost,
        read_compute_cost=read_compute_cost,
        mr_write_cost=mr_write_cost,
        storage_cost=storage_cost,
        total_cost=total_cost,
        total_cluster_size_gb=total_cluster_size_gb,
        write_dpu_ms=write_dpu_ms,
        write_read_dpu_ms=write_read_dpu_ms,
        write_compute_dpu_ms=write_compute_dpu_ms,
        read_dpu_ms=read_dpu_ms,
        read_compute_dpu_ms=read_compute_dpu_ms,
        mr_write_dpu_ms=mr_write_dpu_ms
    )


def print_report(config: WorkloadConfig, costs: CostBreakdown):
    """Print formatted cost report"""
    print()
    print("=" * 80)
    print("Aurora DSQL Cost Estimation Report")
    print("=" * 80)

    print()
    print("--- Workload Characteristics ---")
    print(f"Read TPS:  {config.read_tps:,.0f}")
    print(f"Write TPS: {config.write_tps:,.0f}")
    print(f"Data Size: {costs.total_cluster_size_gb:,.2f} GB ({costs.total_cluster_size_gb/1024:,.2f} TB)")
    print(f"Tables:    {config.num_tables:,}")
    print(f"Indexes:   {config.num_indexes:,}")

    print()
    print("--- Monthly Cost Breakdown ---")
    print(f"Compute (Write):      ${costs.write_compute_cost:>15,.2f}")
    print(f"Compute (Read):       ${costs.read_compute_cost:>15,.2f}")
    print(f"Read Operations:      ${costs.read_cost:>15,.2f}")
    print(f"Write Operations:     ${costs.write_cost:>15,.2f}")
    print(f"Write Read Ops:       ${costs.write_read_cost:>15,.2f}")
    print(f"Multi-Region Write:   ${costs.mr_write_cost:>15,.2f}")
    print(f"Storage:              ${costs.storage_cost:>15,.2f}")
    print("-" * 45)
    print(f"TOTAL:                ${costs.total_cost:>15,.2f}")

    # Cost driver analysis
    print()
    print("--- Cost Driver Analysis ---")
    read_pct = (costs.read_cost / costs.total_cost) * 100
    read_compute_pct = (costs.read_compute_cost / costs.total_cost) * 100
    write_pct = (costs.write_cost / costs.total_cost) * 100
    write_compute_pct = (costs.write_compute_cost / costs.total_cost) * 100
    storage_pct = (costs.storage_cost / costs.total_cost) * 100

    print(f"Read Operations:      {read_pct:5.1f}%")
    print(f"Read Compute:         {read_compute_pct:5.1f}%")
    print(f"Write Operations:     {write_pct:5.1f}%")
    print(f"Write Compute:        {write_compute_pct:5.1f}%")
    print(f"Storage:              {storage_pct:5.1f}%")

    # Optimization recommendations
    print()
    print("--- Optimization Recommendations ---")

    if read_pct > 50:
        print("• Read operations are your largest cost driver")
        print("  - Add indexes for frequently scanned columns")
        print("  - Minimize rows scanned with precise WHERE clauses")
        print("  - Use covering indexes to avoid table lookups")

    if write_pct > 20:
        print("• Write operations are significant")
        print("  - Batch writes (up to 3,000 rows per transaction)")
        print("  - Reduce index count (only create necessary indexes)")
        print("  - Consider async indexes for non-critical queries")

    if storage_pct > 30:
        print("• Storage costs are high")
        print("  - Archive old data to S3 with lifecycle policies")
        print("  - Drop unused indexes")
        print("  - Use appropriate data types (SMALLINT vs BIGINT)")

    print()
    print("=" * 80)
    print()


def main():
    """Main execution"""
    args = parse_args()

    # Create config from defaults
    config = WorkloadConfig()

    if args.interactive:
        config = interactive_mode()
    else:
        # Override defaults with CLI arguments
        if args.read_tps is not None:
            config.read_tps = args.read_tps
        if args.write_tps is not None:
            config.write_tps = args.write_tps
        if args.data_gb is not None:
            config.data_gb = args.data_gb
        if args.num_shards is not None:
            config.num_shards = args.num_shards
        if args.num_tables is not None:
            config.num_tables = args.num_tables
        if args.num_indexes is not None:
            config.num_indexes = args.num_indexes
        if args.rows_changed is not None:
            config.rows_changed_per_write = args.rows_changed
        if args.rows_scanned is not None:
            config.rows_scanned_per_select = args.rows_scanned

    # Calculate and print costs
    costs = calculate_costs(config)
    print_report(config, costs)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
