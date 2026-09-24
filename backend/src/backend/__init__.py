def main() -> None:
    """Launch the local HTTP API server."""
    from backend.api.main import run

    run()
