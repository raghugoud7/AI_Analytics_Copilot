from analytics.executive_summary import ExecutiveSummaryAnalyzer
from analytics.kpi_analysis import KPIAnalysis
from analytics.segment_analyzer import SegmentAnalyzer
from analytics.trend_analyzer import TrendAnalyzer
from analytics.correlation_analyzer import CorrelationAnalyzer
from analytics.outlier_detector import OutlierDetector
from analytics.driver_analyzer import DriverAnalyzer


# class DataAnalysisOrchestrator:

#     def __init__(self):
#         self.summary = ExecutiveSummaryAnalyzer()
#         self.kpi = KPIAnalysis()
#         self.segment = SegmentAnalyzer()
#         self.trend = TrendAnalyzer()
#         self.correlation = CorrelationAnalyzer()
#         self.outlier = OutlierDetector()
#         self.driver = DriverAnalyzer()

#     def analyze(self, df, total_rows=None) -> dict:
#         return {
#             "summary": self.summary.analyze(df, total_rows),
#             "kpis": self.kpi.analyze(df),
#             "segments": self.segment.analyze(df),
#             "trends": self.trend.analyze(df),
#             "correlations": self.correlation.analyze(df),
#             "outliers": self.outlier.analyze(df),
#             "drivers": self.driver.analyze(df),
#         }



class DataAnalysisOrchestrator:

    def __init__(self):
        self.analyzers = {
            "summary": ExecutiveSummaryAnalyzer(),
            "kpis": KPIAnalysis(),
            "segments": SegmentAnalyzer(),
            "trends": TrendAnalyzer(),
            "correlations": CorrelationAnalyzer(),
            "outliers": OutlierDetector(),
            "drivers": DriverAnalyzer(),
        }

    def analyze(self, df, total_rows=None) -> dict:
        return {
            "summary": self.analyzers["summary"].analyze(df, total_rows),
            **{
                name: analyzer.analyze(df)
                for name, analyzer in self.analyzers.items()
                if name != "summary"
            },
        }