import pandas as pd

from utils.privacy import remove_sensitive_columns


class KPIAnalysis:
    KPI_KEYWORDS = (
        "score",
        "rate",
        "ratio",
        "percentage",
        "percent",
        "kpi",
        "duration",
        "quality",
        "performance",
        "accuracy",
    )

    def analyze(self, df: pd.DataFrame) -> dict:
        if df is None or df.empty:
            return {"success": False, "error": "DataFrame is empty."}

        df = remove_sensitive_columns(df)

        kpi_columns = [
            c
            for c in df.select_dtypes(include="number").columns
            if any(k in c.lower() for k in self.KPI_KEYWORDS)
        ] or df.select_dtypes(include="number").columns[:10].tolist()

        kpis = []

        for col in kpi_columns:
            try:
                s = df[col].dropna()
                if s.empty:
                    continue

                kpis.append(
                    {
                        "kpi": col,
                        "record_count": len(s),
                        "null_percentage": round(df[col].isna().mean() * 100, 2),
                        "average": round(float(s.mean()), 2),
                        "median": round(float(s.median()), 2),
                        "minimum": round(float(s.min()), 2),
                        "maximum": round(float(s.max()), 2),
                        "std_dev": round(float(s.std()), 2),
                        "p25": round(float(s.quantile(0.25)), 2),
                        "p75": round(float(s.quantile(0.75)), 2),
                    }
                )
            except Exception:
                pass

        kpis.sort(key=lambda x: x["average"], reverse=True)

        return {"success": True, "kpi_count": len(kpis), "kpis": kpis}