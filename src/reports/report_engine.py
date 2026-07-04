import pandas as pd


class ReportEngine:

    @staticmethod
    def create_report(results):

        df = pd.DataFrame(results)

        df = df.sort_values(
            by=["Profit Factor", "Total PnL %"],
            ascending=False
        )

        return df

    @staticmethod
    def print_report(df):

        print("\n" + "=" * 60)
        print("           B TRADER MULTI PAIR REPORT")
        print("=" * 60)

        print(df.to_string(index=False))

        print("\n" + "=" * 60)
        print("BEST PAIR")
        print("=" * 60)

        print(df.iloc[0].to_string())

    @staticmethod
    def save_csv(df, filename):

        df.to_csv(filename, index=False)

        print(f"\nReport saved -> {filename}")