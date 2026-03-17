from app.config import settings
from app.services.ingestion import IngestionService


def main() -> None:
    result = IngestionService(settings).ingest()
    print(
        f"Ingested documents={result.documents}, chunks={result.chunks}, vector_size={result.vector_size}"
    )


if __name__ == "__main__":
    main()

