from src.strategies.strategy_loader import load_strategy
from src.analyzers.multi_pair_analyzer import MultiPairAnalyzer
from src.reports.report_engine import ReportEngine


def main():

    # ============================
    # Load Strategy
    # ============================

    strategy = load_strategy("src/config/strategy.json")

    # ============================
    # Trading Pairs
    # ============================

    symbols = [
        "BTCUSDT",
        "ETHUSDT",
        "BNBUSDT",
        "SOLUSDT",
        "XRPUSDT"
    ]

    # ============================
    # Run Analysis
    # ============================

    analyzer = MultiPairAnalyzer(strategy)

    results = analyzer.analyze(
        symbols=symbols,
        interval="1h",
        start_str="1 year ago UTC",
        sl_values=[1, 1.5, 2, 2.5],
        tp_values=[2, 3, 4, 5]
    )

    # ============================
    # Create Report
    # ============================

    report = ReportEngine.create_report(results)

    # ============================
    # Print Report
    # ============================

    ReportEngine.print_report(report)

    # ============================
    # Save CSV Report
    # ============================

    ReportEngine.save_csv(
        report,
        "reports/multi_pair_report.csv"
    )


if __name__ == "__main__":
    main()