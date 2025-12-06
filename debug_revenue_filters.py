"""
Debug Revenue Processing Filters
Analyzes which records are being filtered out at each step
"""

import pandas as pd
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def debug_cpt_comptable_filter(file_path: str):
    """Debug the Cpt Comptable filter to see what's being removed"""

    # Read the file
    logger.info(f"Reading file: {file_path}")

    # Try reading as Excel
    try:
        df = pd.read_excel(file_path, engine='xlrd')
    except:
        try:
            # Try reading as HTML
            from io import StringIO
            import re

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()

            # Fix French decimal separators
            html_content_fixed = re.sub(r'(\d+),(\d{2})(?!\d)', r'\1DECIMALSEP\2', html_content)
            html_tables_fixed = pd.read_html(StringIO(html_content_fixed), header=None)
            best_table = max(html_tables_fixed, key=lambda t: len(t.columns))

            # Convert DECIMALSEP back to dots
            for col in best_table.columns:
                best_table[col] = best_table[col].astype(str).str.replace('DECIMALSEP', '.')

            # Find header row
            for row_idx in range(min(20, len(best_table))):
                row_values = [str(val).lower() for val in best_table.iloc[row_idx].values if pd.notna(val)]
                if 'org name' in ' '.join(row_values) or 'cpt comptable' in ' '.join(row_values):
                    headers = best_table.iloc[row_idx].astype(str).tolist()
                    df = best_table.iloc[row_idx + 1:].copy()
                    df.columns = headers
                    df.reset_index(drop=True, inplace=True)
                    break
            else:
                df = best_table.iloc[1:].copy()
                df.columns = best_table.iloc[0].astype(str).tolist()
                df.reset_index(drop=True, inplace=True)

        except Exception as e:
            logger.error(f"Failed to read file: {e}")
            return

    logger.info(f"Loaded {len(df)} rows")
    logger.info(f"Columns: {list(df.columns)}")

    # Find Cpt Comptable column
    cpt_col = None
    for col in df.columns:
        if 'cpt comptable' in str(col).lower() or 'compte comptable' in str(col).lower():
            cpt_col = col
            break

    if not cpt_col:
        logger.error("Could not find Cpt Comptable column!")
        return

    logger.info(f"Found Cpt Comptable column: '{cpt_col}'")

    # Original count
    original_count = len(df)
    logger.info(f"\n{'='*80}")
    logger.info(f"ORIGINAL DATA: {original_count} rows")
    logger.info(f"{'='*80}")

    # Analyze AT_SIEGE filter
    org_col = None
    for col in df.columns:
        if 'org name' in str(col).lower() or 'organisation' in str(col).lower():
            org_col = col
            break

    if org_col:
        at_siege_mask = df[org_col].astype(str).str.contains('AT_SIEGE', case=False, na=False)
        at_siege_count = at_siege_mask.sum()
        logger.info(f"\n1. AT_SIEGE filter: {at_siege_count} rows would be removed")
        df_after_siege = df[~at_siege_mask].copy()
        logger.info(f"   Remaining: {len(df_after_siege)} rows")
    else:
        df_after_siege = df.copy()
        logger.info(f"\n1. AT_SIEGE filter: Could not find Org Name column, skipping")

    # Analyze 'reprise' filter
    reprise_mask = pd.Series([False] * len(df_after_siege), index=df_after_siege.index)
    for col in df_after_siege.columns:
        if df_after_siege[col].dtype == 'object':
            reprise_mask |= df_after_siege[col].astype(str).str.contains('reprise', case=False, na=False)

    reprise_count = reprise_mask.sum()
    logger.info(f"\n2. 'Reprise' filter: {reprise_count} rows would be removed")
    df_after_reprise = df_after_siege[~reprise_mask].copy()
    logger.info(f"   Remaining: {len(df_after_reprise)} rows")

    # Analyze Cpt Comptable filter - THIS IS THE PROBLEM
    logger.info(f"\n{'='*80}")
    logger.info(f"3. CPT COMPTABLE FILTER ANALYSIS")
    logger.info(f"{'='*80}")

    # Current (problematic) filter: case-insensitive, contains 'A' anywhere
    current_filter_mask = df_after_reprise[cpt_col].astype(str).str.contains('A', case=False, na=False)
    current_filter_count = current_filter_mask.sum()

    logger.info(f"\n   CURRENT FILTER (case-insensitive, contains 'A'):")
    logger.info(f"   - Would remove: {current_filter_count} rows")
    logger.info(f"   - Would keep: {len(df_after_reprise) - current_filter_count} rows")

    # Show sample of what would be removed
    if current_filter_count > 0:
        logger.info(f"\n   Sample of Cpt Comptable values that would be REMOVED:")
        removed_samples = df_after_reprise[current_filter_mask][cpt_col].unique()[:20]
        for i, val in enumerate(removed_samples, 1):
            logger.info(f"      {i}. '{val}'")
        if len(removed_samples) == 20 and current_filter_count > 20:
            logger.info(f"      ... and {current_filter_count - 20} more")

    # Show sample of what would be kept
    kept_count = (~current_filter_mask).sum()
    if kept_count > 0:
        logger.info(f"\n   Sample of Cpt Comptable values that would be KEPT:")
        kept_samples = df_after_reprise[~current_filter_mask][cpt_col].unique()[:20]
        for i, val in enumerate(kept_samples, 1):
            logger.info(f"      {i}. '{val}'")

    # Alternative filter: case-sensitive, uppercase 'A' only
    alternative_filter_mask = df_after_reprise[cpt_col].astype(str).str.contains('A', case=True, na=False)
    alternative_filter_count = alternative_filter_mask.sum()

    logger.info(f"\n   ALTERNATIVE FILTER (case-sensitive, uppercase 'A' only):")
    logger.info(f"   - Would remove: {alternative_filter_count} rows")
    logger.info(f"   - Would keep: {len(df_after_reprise) - alternative_filter_count} rows")
    logger.info(f"   - Difference: {current_filter_count - alternative_filter_count} rows")

    # More specific filter: 'A' as standalone character
    standalone_a_mask = df_after_reprise[cpt_col].astype(str).str.contains(r'\bA\b', case=True, na=False, regex=True)
    standalone_a_count = standalone_a_mask.sum()

    logger.info(f"\n   STANDALONE 'A' FILTER (word boundary, uppercase only):")
    logger.info(f"   - Would remove: {standalone_a_count} rows")
    logger.info(f"   - Would keep: {len(df_after_reprise) - standalone_a_count} rows")
    logger.info(f"   - Difference from current: {current_filter_count - standalone_a_count} rows")

    # Summary
    logger.info(f"\n{'='*80}")
    logger.info(f"SUMMARY")
    logger.info(f"{'='*80}")
    logger.info(f"Original rows: {original_count}")
    logger.info(f"After AT_SIEGE filter: {len(df_after_siege)} ({original_count - len(df_after_siege)} removed)")
    logger.info(f"After 'reprise' filter: {len(df_after_reprise)} ({len(df_after_siege) - len(df_after_reprise)} removed)")
    logger.info(f"After Cpt Comptable filter (CURRENT): {len(df_after_reprise) - current_filter_count} ({current_filter_count} removed)")
    logger.info(f"After Cpt Comptable filter (ALTERNATIVE - case-sensitive): {len(df_after_reprise) - alternative_filter_count} ({alternative_filter_count} removed)")
    logger.info(f"After Cpt Comptable filter (STANDALONE): {len(df_after_reprise) - standalone_a_count} ({standalone_a_count} removed)")

    # Expected vs Actual
    expected_final = 5015
    actual_final_current = len(df_after_reprise) - current_filter_count
    actual_final_alternative = len(df_after_reprise) - alternative_filter_count
    actual_final_standalone = len(df_after_reprise) - standalone_a_count

    logger.info(f"\n{'='*80}")
    logger.info(f"EXPECTED vs ACTUAL")
    logger.info(f"{'='*80}")
    logger.info(f"Expected final count: {expected_final}")
    logger.info(f"Actual final count (CURRENT filter): {actual_final_current} (difference: {expected_final - actual_final_current})")
    logger.info(f"Actual final count (ALTERNATIVE filter): {actual_final_alternative} (difference: {expected_final - actual_final_alternative})")
    logger.info(f"Actual final count (STANDALONE filter): {actual_final_standalone} (difference: {expected_final - actual_final_standalone})")

    # Check which approach matches expected
    if abs(actual_final_current - expected_final) < 10:
        logger.info(f"\n✅ CURRENT filter is close to expected!")
    elif abs(actual_final_alternative - expected_final) < 10:
        logger.info(f"\n✅ ALTERNATIVE filter (case-sensitive) is close to expected!")
    elif abs(actual_final_standalone - expected_final) < 10:
        logger.info(f"\n✅ STANDALONE filter is close to expected!")
    else:
        logger.info(f"\n⚠️ None of the filters match the expected count of {expected_final}")
        logger.info(f"   There may be another filter or step causing the discrepancy")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_revenue_filters.py <path_to_revenue_journal_file>")
        print("\nExample:")
        print("  python debug_revenue_filters.py uploads/excel/AT___Journal_du_Chiffre_d_affa_180525.xls")
        sys.exit(1)

    file_path = sys.argv[1]
    debug_cpt_comptable_filter(file_path)
