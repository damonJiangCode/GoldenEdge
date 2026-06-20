from __future__ import annotations

import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform


STUDY_DIR = Path(__file__).resolve().parents[1]
ALPHA_ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = ALPHA_ROOT / "shared" / "data"
METADATA_PATH = DATA_ROOT / "symbols_metadata.csv"
METRICS_DIR = STUDY_DIR / "metrics"
OUTPUTS_DIR = STUDY_DIR / "outputs"
SUMMARY_PATH = STUDY_DIR / "summary.md"
sys.path.insert(0, str(ALPHA_ROOT))

from shared.configs.universes import MIXED_ASSET_SYMBOLS  # noqa: E402
from shared.loaders.prices import load_symbol  # noqa: E402


DISTANCE_THRESHOLDS = [0.30, 0.40, 0.50, 0.60, 0.70]
SELECTED_THRESHOLD = 0.50
ASSET_CLASSES = {
    "Equity": [
        "SPY", "QQQ", "IWM", "EFA", "EEM", "VTI", "DIA",
        "XLK", "XLF", "XLV", "XLY", "XLP", "XLE", "XLI", "XLU", "XLB", "XLRE",
        "IWF", "IWD", "MTUM", "QUAL", "USMV", "VLUE", "VNQ",
    ],
    "Commodity": [
        "GLD", "SLV", "PPLT", "PALL", "USO", "UNG", "DBO", "XOP",
        "DBA", "CORN", "WEAT", "SOYB", "DBC", "GSG",
    ],
    "Bond": ["TLT", "IEF", "SHY", "LQD", "TIP", "HYG"],
    "Currency": ["UUP"],
}
SYMBOLS = [symbol for symbols in ASSET_CLASSES.values() for symbol in symbols]
CLASS_BY_SYMBOL = {symbol: asset_class for asset_class, symbols in ASSET_CLASSES.items() for symbol in symbols}
CLASS_PAIR_ORDER = [
    ("Equity", "Equity"),
    ("Equity", "Commodity"),
    ("Equity", "Bond"),
    ("Equity", "Currency"),
    ("Commodity", "Commodity"),
    ("Commodity", "Bond"),
    ("Commodity", "Currency"),
    ("Bond", "Bond"),
    ("Bond", "Currency"),
    ("Currency", "Currency"),
]
CLEAN_PROXY_PRIORITY = [
    "SPY", "QQQ", "IWM", "EFA", "EEM", "VTI", "DIA",
    "XLK", "XLF", "XLV", "XLY", "XLP", "XLE", "XLI", "XLU", "XLB", "VNQ", "XLRE",
    "IWF", "IWD", "QUAL", "USMV", "VLUE", "MTUM",
    "GLD", "PPLT", "PALL", "SLV", "DBO", "USO", "UNG", "DBA", "DBC", "GSG",
    "CORN", "WEAT", "SOYB", "XOP", "IEF", "TLT", "SHY", "LQD", "TIP", "HYG", "UUP",
]
PROXY_PRIORITY = {symbol: rank for rank, symbol in enumerate(CLEAN_PROXY_PRIORITY)}
LABEL_PROXY_PREFERENCE = {
    "Agriculture / Broad Commodity": "DBA",
    "Energy / Broad Commodity": "DBC",
    "Broad Equity Beta": "SPY",
    "Precious Metals": "GLD",
    "Treasury / Investment Grade Bonds": "IEF",
}


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    metadata = pd.read_csv(METADATA_PATH).set_index("symbol")
    missing_metadata = sorted(set(SYMBOLS) - set(metadata.index))
    if missing_metadata:
        raise RuntimeError(f"Missing metadata: {missing_metadata}")

    price_frames = []
    volume_frames = []
    for symbol in SYMBOLS:
        asset_class = CLASS_BY_SYMBOL[symbol].lower()
        path = DATA_ROOT / asset_class / f"{symbol}.csv"
        price = load_symbol(path)
        if price is None:
            raise RuntimeError(f"Failed to load adjusted close for {symbol}")
        raw = pd.read_csv(path, usecols=["Date", "Volume"])
        raw["Date"] = pd.to_datetime(raw["Date"])
        raw[symbol] = pd.to_numeric(raw["Volume"], errors="coerce")
        volume = raw.dropna().drop_duplicates("Date", keep="last").set_index("Date")[[symbol]]
        price_frames.append(price)
        volume_frames.append(volume)

    prices = pd.concat(price_frames, axis=1).sort_index().dropna(how="any")[SYMBOLS]
    volumes = pd.concat(volume_frames, axis=1).reindex(prices.index)[SYMBOLS]
    if volumes.isna().any().any():
        raise RuntimeError("Incomplete volume data in common sample")
    return prices, volumes, metadata


def monthly_returns(prices: pd.DataFrame) -> pd.DataFrame:
    month_ends = prices.groupby(prices.index.to_period("M")).tail(1)
    returns = month_ends.pct_change(fill_method=None).dropna(how="any")
    if returns.isna().any().any():
        raise RuntimeError("Incomplete monthly returns")
    return returns


def pairwise_table(correlation: pd.DataFrame, metadata: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for symbol_1, symbol_2 in combinations(correlation.columns, 2):
        rows.append(
            {
                "ETF 1": symbol_1,
                "ETF 2": symbol_2,
                "Correlation": correlation.loc[symbol_1, symbol_2],
                "Asset Class 1": CLASS_BY_SYMBOL[symbol_1],
                "Asset Class 2": CLASS_BY_SYMBOL[symbol_2],
                "Category 1": metadata.loc[symbol_1, "category"],
                "Category 2": metadata.loc[symbol_2, "category"],
            }
        )
    return pd.DataFrame(rows)


def class_pair_correlations(pairs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for class_1, class_2 in CLASS_PAIR_ORDER:
        mask = (
            ((pairs["Asset Class 1"] == class_1) & (pairs["Asset Class 2"] == class_2))
            | ((pairs["Asset Class 1"] == class_2) & (pairs["Asset Class 2"] == class_1))
        )
        rows.append(
            {
                "Class Pair": f"{class_1} - {class_2}",
                "Average Correlation": pairs.loc[mask, "Correlation"].mean(),
                "Pair Count": int(mask.sum()),
            }
        )
    return pd.DataFrame(rows)


def canonical_clusters(raw_labels: np.ndarray, symbols: list[str]) -> dict[str, int]:
    raw_members = {}
    for symbol, raw_label in zip(symbols, raw_labels):
        raw_members.setdefault(int(raw_label), []).append(symbol)
    ordered = sorted(raw_members.items(), key=lambda item: sorted(item[1])[0])
    raw_to_canonical = {raw_label: cluster_id for cluster_id, (raw_label, _) in enumerate(ordered, start=1)}
    return {symbol: raw_to_canonical[int(raw_label)] for symbol, raw_label in zip(symbols, raw_labels)}


def clustering_results(
    correlation: pd.DataFrame,
) -> tuple[np.ndarray, pd.DataFrame, pd.DataFrame]:
    distance = np.sqrt(0.5 * (1 - correlation.clip(-1, 1)))
    np.fill_diagonal(distance.values, 0.0)
    condensed = squareform(distance.values, checks=True)
    linkage_matrix = linkage(condensed, method="average")
    summary_rows = []
    assignment_rows = []

    for threshold in DISTANCE_THRESHOLDS:
        raw_labels = fcluster(linkage_matrix, t=threshold, criterion="distance")
        assignments = canonical_clusters(raw_labels, correlation.columns.tolist())
        sizes = pd.Series(assignments).value_counts()
        summary_rows.append(
            {
                "Distance Threshold": threshold,
                "Number of Clusters": len(sizes),
                "Largest Cluster Size": int(sizes.max()),
                "Median Cluster Size": float(sizes.median()),
                "Singleton Count": int((sizes == 1).sum()),
            }
        )
        for symbol, cluster_id in assignments.items():
            assignment_rows.append(
                {"Distance Threshold": threshold, "Symbol": symbol, "Cluster ID": cluster_id}
            )
    return linkage_matrix, pd.DataFrame(summary_rows), pd.DataFrame(assignment_rows)


def dominant_label(values: list[str]) -> str:
    counts = pd.Series(values).value_counts()
    winners = sorted(counts[counts == counts.max()].index.tolist())
    return " / ".join(winners)


def describe_cluster(symbols: list[str]) -> str:
    members = set(symbols)
    if len(symbols) == 1:
        return {
            "PALL": "Palladium",
            "UNG": "Natural Gas",
            "UUP": "US Dollar",
            "XLU": "Utilities Equity",
        }.get(symbols[0], f"{symbols[0]} Standalone Exposure")
    class_counts = pd.Series([CLASS_BY_SYMBOL[symbol] for symbol in symbols]).value_counts()
    dominant_class = class_counts.index[0]
    if dominant_class == "Bond":
        if members <= {"LQD", "HYG"}:
            return "Credit Bonds"
        if members <= {"TLT", "IEF", "SHY", "TIP"}:
            return "Treasury / Inflation Bonds"
        return "Treasury / Investment Grade Bonds"
    if dominant_class == "Currency":
        return "US Dollar"
    if dominant_class == "Commodity":
        if members & {"GLD", "SLV", "PPLT", "PALL"} and len(members - {"GLD", "SLV", "PPLT", "PALL"}) == 0:
            return "Precious Metals"
        if members & {"USO", "UNG", "DBO", "XOP"} and len(members - {"USO", "UNG", "DBO", "XOP", "DBC", "GSG"}) == 0:
            return "Energy / Broad Commodity"
        if members & {"DBA", "CORN", "WEAT", "SOYB"} and len(members - {"DBA", "CORN", "WEAT", "SOYB", "DBC", "GSG"}) == 0:
            return "Agriculture / Broad Commodity"
        return "Energy / Broad Commodity" if members & {"USO", "DBO", "XOP", "XLE"} else "Diversified Commodities"
    if members & {"VNQ", "XLRE"} and len(members - {"VNQ", "XLRE"}) <= 1:
        return "US Real Estate"
    if members & {"EFA", "EEM"} and len(members - {"EFA", "EEM"}) <= 1:
        return "International Equity"
    if len(symbols) >= 10:
        return "Broad Equity Beta"
    if len(members & {"QQQ", "XLK", "IWF", "MTUM"}) >= 2:
        return "US Growth / Technology"
    if len(members & {"XLP", "XLV", "XLU", "USMV"}) >= 2:
        return "Defensive Equity"
    if len(members & {"SPY", "VTI", "DIA", "IWM", "QUAL"}) >= 2:
        return "US Broad Equity"
    if len(members & {"XLF", "XLE", "XLI", "XLB", "IWD", "VLUE"}) >= 2:
        return "US Cyclical / Value Equity"
    return "Specialized Equity"


def cluster_summary(
    assignments: pd.DataFrame,
    correlation: pd.DataFrame,
    metadata: pd.DataFrame,
    returns: pd.DataFrame,
) -> pd.DataFrame:
    selected = assignments.loc[assignments["Distance Threshold"] == SELECTED_THRESHOLD]
    rows = []
    for cluster_id, group in selected.groupby("Cluster ID", sort=True):
        symbols = sorted(group["Symbol"].tolist())
        if len(symbols) == 1:
            intra_correlation = np.nan
        else:
            values = [correlation.loc[a, b] for a, b in combinations(symbols, 2)]
            intra_correlation = float(np.mean(values))
        rows.append(
            {
                "Cluster ID": int(cluster_id),
                "Cluster Size": len(symbols),
                "Symbols": ",".join(symbols),
                "Cluster Label": describe_cluster(symbols),
                "Dominant Asset Class": dominant_label([CLASS_BY_SYMBOL[symbol] for symbol in symbols]),
                "Dominant Category": dominant_label(metadata.loc[symbols, "category"].tolist()),
                "Intra-Cluster Average Correlation": intra_correlation,
                "Average Annualized Volatility": float((returns[symbols].std(ddof=1) * np.sqrt(12)).mean()),
            }
        )
    return pd.DataFrame(rows)


def representatives(
    clusters: pd.DataFrame,
    prices: pd.DataFrame,
    volumes: pd.DataFrame,
    metadata: pd.DataFrame,
) -> pd.DataFrame:
    average_dollar_volume = (prices * volumes).mean()
    rows = []
    for _, cluster in clusters.iterrows():
        symbols = cluster["Symbols"].split(",")
        dominant_classes = cluster["Dominant Asset Class"].split(" / ")
        representative_symbols = [
            symbol for symbol in symbols if CLASS_BY_SYMBOL[symbol] in dominant_classes
        ] or symbols
        candidates = pd.DataFrame(
            {
                "Symbol": representative_symbols,
                "Start": [pd.Timestamp(metadata.loc[symbol, "actual_start"]) for symbol in representative_symbols],
                "Average Dollar Volume": [average_dollar_volume[symbol] for symbol in representative_symbols],
                "Proxy Priority": [PROXY_PRIORITY.get(symbol, 999) for symbol in representative_symbols],
            }
        )
        earliest_year = candidates["Start"].dt.year.min()
        long_history = candidates.loc[candidates["Start"].dt.year == earliest_year].copy()
        preferred_symbol = LABEL_PROXY_PREFERENCE.get(cluster["Cluster Label"])
        preferred = long_history.loc[long_history["Symbol"] == preferred_symbol]
        if not preferred.empty:
            representative = preferred.iloc[0]
        else:
            long_history["Liquidity Rank"] = long_history["Average Dollar Volume"].rank(ascending=False, method="min")
            long_history["Combined Rank"] = long_history["Liquidity Rank"] + long_history["Proxy Priority"] / 100
            representative = long_history.sort_values(["Combined Rank", "Start", "Symbol"]).iloc[0]
        reason = (
            f"History from {representative['Start'].date()}; selected from the earliest-history cohort "
            f"using liquidity and broad/clean exposure preference, not return performance."
        )
        rows.append(
            {
                "Cluster ID": int(cluster["Cluster ID"]),
                "Cluster Label": cluster["Cluster Label"],
                "Representative ETF": representative["Symbol"],
                "Reason": reason,
            }
        )
    return pd.DataFrame(rows)


def fmt_corr(value: float) -> str:
    return "NA" if pd.isna(value) else f"{value:.2f}"


def markdown_table(
    df: pd.DataFrame,
    columns: list[str],
    correlation_columns: set[str] | None = None,
    percentage_columns: set[str] | None = None,
) -> str:
    correlation_columns = correlation_columns or set()
    percentage_columns = percentage_columns or set()
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in df[columns].iterrows():
        cells = []
        for column in columns:
            value = row[column]
            if column in correlation_columns:
                cells.append(fmt_corr(value))
            elif column in percentage_columns:
                cells.append(f"{value:.2%}")
            elif isinstance(value, (float, np.floating)):
                cells.append(f"{value:.2f}")
            else:
                cells.append(str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def generate_summary(
    highest: pd.DataFrame,
    lowest: pd.DataFrame,
    class_pairs: pd.DataFrame,
    threshold_summary: pd.DataFrame,
    clusters: pd.DataFrame,
    representative_table: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
    monthly_observations: int,
) -> str:
    selected_row = threshold_summary.loc[threshold_summary["Distance Threshold"] == SELECTED_THRESHOLD].iloc[0]
    large_clusters = clusters.sort_values("Cluster Size", ascending=False).head(3)
    redundant_groups = "; ".join(
        f"{row['Cluster Label']} ({row['Symbols']})" for _, row in large_clusters.iterrows()
    )
    singleton_labels = clusters.loc[clusters["Cluster Size"] == 1, "Cluster Label"].tolist()
    diversified = ", ".join(singleton_labels) if singleton_labels else "独立小簇和低相关跨类别资产"
    original_symbols = set(MIXED_ASSET_SYMBOLS)
    covered_clusters = sum(
        bool(set(symbols.split(",")) & original_symbols) for symbols in clusters["Symbols"]
    )
    total_clusters = len(clusters)

    pair_columns = ["ETF 1", "ETF 2", "Correlation", "Asset Class 1", "Asset Class 2", "Category 1", "Category 2"]
    return f"""# ETF Correlation Clustering Analysis

## 1. Research Question

识别 Expanded 45 ETF Universe 的月收益相关结构，判断名义资产数量对应多少个相对独立风险簇。本研究不运行任何交易策略。

## 2. Data and Sample

- Price: Adjusted Close
- Frequency: month-end returns
- ETFs included: 45
- Common daily sample: `{start.date()}` to `{end.date()}`
- Monthly return observations: {monthly_observations}
- Correlation distance: `sqrt(0.5 * (1 - correlation))`
- Hierarchical clustering: average linkage

## 3. Highest Correlation Pairs

{markdown_table(highest, pair_columns, {'Correlation'})}

## 4. Lowest Correlation Pairs

{markdown_table(lowest, pair_columns, {'Correlation'})}

## 5. Average Correlation by Asset Class Pair

{markdown_table(class_pairs, ['Class Pair', 'Average Correlation', 'Pair Count'], {'Average Correlation'})}

## 6. Threshold Diagnostics

{markdown_table(threshold_summary, ['Distance Threshold', 'Number of Clusters', 'Largest Cluster Size', 'Median Cluster Size', 'Singleton Count'])}

Selected threshold: **{SELECTED_THRESHOLD:.2f}**. It produces {int(selected_row['Number of Clusters'])} clusters, largest size {int(selected_row['Largest Cluster Size'])}, median size {selected_row['Median Cluster Size']:.1f}, and {int(selected_row['Singleton Count'])} singletons. The threshold is selected for interpretable cluster balance only, not strategy performance.

## 7. Selected Cluster Output

{markdown_table(clusters, ['Cluster ID', 'Cluster Size', 'Symbols', 'Cluster Label', 'Dominant Asset Class', 'Dominant Category', 'Intra-Cluster Average Correlation', 'Average Annualized Volatility'], {'Intra-Cluster Average Correlation'}, {'Average Annualized Volatility'})}

## 8. Representative ETFs

Representatives prioritize local history length, common-sample dollar-volume liquidity, and broad/clean exposure preference. Expense ratios are not present in the local dataset and are therefore not asserted. Historical returns are not used.

{markdown_table(representative_table, ['Cluster ID', 'Cluster Label', 'Representative ETF', 'Reason'])}

## 9. Diagnostics

1. **Does the Universe contain highly correlated duplicates?** Yes. The largest and highest-correlation clusters show substantial overlap, especially within equity styles/sectors and related commodity exposures.
2. **How many effective risk clusters?** At the selected threshold, approximately **{int(selected_row['Number of Clusters'])}** clusters versus 45 tickers.
3. **Most redundant groups?** {redundant_groups}.
4. **Genuinely diversifying exposures?** {diversified}; the lowest-correlation table also identifies the strongest cross-cluster diversifiers.
5. **True or nominal breadth?** Expansion added both real exposures and many correlated variants. Because the effective cluster count is materially below 45 and the largest clusters contain repeated exposures, much of the added breadth is nominal.
6. **Is Original 12 close to a representative-cluster universe?** The Original 12 covers {covered_clusters}/{total_clusters} selected clusters. It captures the main broad Equity, Energy/Commodity, Precious Metal, Agriculture, and Bond clusters, but misses several standalone diversifiers; it is a compact core rather than a complete representative-cluster universe.

## 10. Final Conclusion

The correlation structure supports **redundant ETFs and unequal cluster representation** as important causes of Expanded Global Top5 deterioration. A global rank gives large clusters more opportunities to occupy limited Top5 slots, while volatile specialized clusters can generate more extreme ranks and smaller Bond/defensive clusters can be crowded out. This is a structural diagnosis rather than a causal backtest, and it does not show a general failure of momentum; it shows that nominal ticker breadth is not equivalent to balanced independent-risk breadth.
"""


def main() -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    prices, volumes, metadata = load_data()
    returns = monthly_returns(prices)
    correlation = returns.corr()
    pairs = pairwise_table(correlation, metadata)
    highest = pairs.nlargest(20, "Correlation").reset_index(drop=True)
    lowest = pairs.nsmallest(20, "Correlation").reset_index(drop=True)
    class_pairs = class_pair_correlations(pairs)
    linkage_matrix, threshold_summary, assignments = clustering_results(correlation)
    clusters = cluster_summary(assignments, correlation, metadata, returns)
    representative_table = representatives(clusters, prices, volumes, metadata)

    highest.to_csv(METRICS_DIR / "highest_correlation_pairs.csv", index=False)
    lowest.to_csv(METRICS_DIR / "lowest_correlation_pairs.csv", index=False)
    class_pairs.to_csv(METRICS_DIR / "asset_class_pair_correlations.csv", index=False)
    threshold_summary.to_csv(METRICS_DIR / "threshold_summary.csv", index=False)
    clusters.to_csv(METRICS_DIR / "selected_clusters.csv", index=False)
    representative_table.to_csv(METRICS_DIR / "representative_etfs.csv", index=False)
    correlation.to_csv(OUTPUTS_DIR / "correlation_matrix.csv")
    assignments.to_csv(OUTPUTS_DIR / "cluster_assignments_by_threshold.csv", index=False)
    np.savetxt(OUTPUTS_DIR / "linkage_matrix.csv", linkage_matrix, delimiter=",", header="left,right,distance,count", comments="")
    pd.DataFrame(
        [
            {"Metric": "Number of ETFs", "Value": len(prices.columns)},
            {"Metric": "Common Start Date", "Value": prices.index.min().date().isoformat()},
            {"Metric": "Common End Date", "Value": prices.index.max().date().isoformat()},
            {"Metric": "Monthly Observations", "Value": len(returns)},
            {"Metric": "Selected Distance Threshold", "Value": SELECTED_THRESHOLD},
        ]
    ).to_csv(METRICS_DIR / "sample_summary.csv", index=False)
    SUMMARY_PATH.write_text(
        generate_summary(
            highest, lowest, class_pairs, threshold_summary, clusters, representative_table,
            prices.index.min(), prices.index.max(), len(returns),
        ),
        encoding="utf-8",
    )

    print("\nETF Correlation Clustering Analysis Complete")
    print(f"Sample: {prices.index.min().date()} to {prices.index.max().date()}")
    print(f"Monthly observations: {len(returns)}")
    print("\nThreshold diagnostics:")
    print(threshold_summary.to_string(index=False))
    print(f"\nSelected threshold clusters ({SELECTED_THRESHOLD:.2f}):")
    print(clusters.to_string(index=False))
    print("\nRepresentatives:")
    print(representative_table.to_string(index=False))


if __name__ == "__main__":
    main()
