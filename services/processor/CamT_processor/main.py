import logging

from ct_core.db import init_db

from .config.settings import ProcessorSettings
from .logging_utils import configure_logging
from .pipeline.supervisor import Supervisor


def main() -> None:
    configure_logging()
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    settings = ProcessorSettings()
    init_db()
    supervisor = Supervisor(settings)
    supervisor.start()


if __name__ == "__main__":
    main()
