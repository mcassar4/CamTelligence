import logging

from .config.settings import ProcessorSettings
from .logging_utils import configure_logging
from .pipeline.supervisor import Supervisor


def main() -> None:
    configure_logging()
    settings = ProcessorSettings()

    supervisor = Supervisor(settings)
    supervisor.start()


if __name__ == "__main__":
    main()