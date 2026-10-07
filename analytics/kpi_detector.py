# analytics/kpi_detector.py

class KPIDetector:

    KPI_KEYWORDS = [
        "score",
        "quality",
        "revenue",
        "sales",
        "profit",
        "cost",
        "duration",
        "time",
        "amount",
        "rate",
        "count",
        "volume",
        "satisfaction",
        "productivity"
    ]

    @staticmethod
    def detect(columns):

        detected_kpis = []

        for column in columns:

            lower_col = column.lower()

            for keyword in KPIDetector.KPI_KEYWORDS:

                if keyword in lower_col:

                    detected_kpis.append(column)

                    break

        return sorted(
            list(set(detected_kpis))
        )