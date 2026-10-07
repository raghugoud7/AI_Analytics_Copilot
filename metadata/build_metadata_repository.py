# metadata/build_metadata_repository.py

from database.query_executor import QueryExecutor
from database.schema_extractor import SchemaExtractor

from agents.metadata_profiler_agent import (
    MetadataProfilerAgent
)

from metadata.metadata_repository_builder import (
    MetadataRepositoryBuilder
)


class MetadataRepositoryPipeline:

    def __init__(self):

        self.query_executor = QueryExecutor()

        self.schema_extractor = SchemaExtractor(
            self.query_executor
        )

        self.metadata_profiler = (
            MetadataProfilerAgent()
        )

        self.repository_builder = (
            MetadataRepositoryBuilder()
        )

    def build(
        self,
        schema_name: str,
        table_name: str
    ):

        print(
            f"Extracting metadata for "
            f"{schema_name}.{table_name}"
        )

        # ==========================================
        # STEP 1
        # EXTRACT SCHEMA METADATA
        # ==========================================

        metadata_info = (
            self.schema_extractor.extract(
                schema_name=schema_name,
                table_name=table_name
            )
        )

        metadata_df = metadata_info[
            "columns"
        ]

        if metadata_df.empty:

            raise ValueError(
                f"No metadata found for "
                f"{schema_name}.{table_name}"
            )

        print(
            f"Found {len(metadata_df)} columns"
        )

        # ==========================================
        # STEP 2
        # PROFILE METADATA
        # ==========================================

        print(
            "Running MetadataProfilerAgent..."
        )

        profile_result = (
            self.metadata_profiler
            .profile_metadata(
                metadata_df=metadata_df,
                table_name=table_name,
                schema_name=schema_name
            )
        )

        if not profile_result.get(
            "success",
            False
        ):

            raise Exception(
                "Metadata profiling failed.\n\n"
                + profile_result.get(
                    "raw_response",
                    ""
                )
            )

        profile = profile_result[
            "profile"
        ]

        print(
            "Metadata profiling completed."
        )

        print(
            f"Business Domain: "
            f"{profile.get('business_domain')}"
        )

        print(
            f"KPIs: "
            f"{len(profile.get('kpis', []))}"
        )

        print(
            f"Dimensions: "
            f"{len(profile.get('dimensions', []))}"
        )

        print(
            f"Measures: "
            f"{len(profile.get('measures', []))}"
        )

        # ==========================================
        # STEP 3
        # BUILD METADATA REPOSITORY
        # ==========================================

        print(
            "Building metadata repository..."
        )

        repository = (
            self.repository_builder.build(
                schema_name=schema_name,
                table_name=table_name,
                metadata_df=metadata_df,
                profiling_output=profile
            )
        )

        print(
            "Metadata repository created."
        )

        print(
            f"Documents generated: "
            f"{len(repository)}"
        )

        return repository


def main():

    schema_name = "salesforce"

    table_name = "call_quality__c"

    pipeline = (
        MetadataRepositoryPipeline()
    )

    repository = pipeline.build(
        schema_name=schema_name,
        table_name=table_name
    )

    print(
        "\nSUCCESS: "
        "metadata_repository.json created"
    )

    return repository


if __name__ == "__main__":

    main()