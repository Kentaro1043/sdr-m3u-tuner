import argparse
import sys
from pathlib import Path

import yaml
from loguru import logger


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file.

    Args:
        config_path: Path to the configuration file

    Returns:
        dict: Parsed configuration data

    Raises:
        FileNotFoundError: If the config file doesn't exist
        yaml.YAMLError: If the YAML file is invalid
    """
    config_file = Path(config_path)

    if not config_file.exists():
        logger.error(f"Configuration file not found: {config_path}")
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        logger.info(f"Configuration loaded from: {config_path}")
        return config

    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML file {config_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Error reading configuration file {config_path}: {e}")
        raise


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(description="SDR m3u Tuner")

    parser.add_argument(
        "--config",
        type=str,
        default="./config.yaml",
        help="Path to configuration file (default: ./config.yaml)",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    return parser.parse_args()


def setup_logging(verbose: bool = False):
    """Setup logging configuration.

    Args:
        verbose: Enable verbose logging if True
    """
    log_level = "DEBUG" if verbose else "INFO"

    logger.remove()
    logger.add(
        sys.stderr,
        level=log_level,
    )


def main():
    """Main entry point."""
    args = parse_arguments()

    # Setup logging
    setup_logging(args.verbose)

    try:
        # Load configuration
        config = load_config(args.config)

        # Log configuration details
        logger.info(f"Server URL: {config.get('url', 'Not configured')}")

        # TODO: Implement the main application logic here
        logger.info("SDR m3u Tuner started successfully")
        logger.info("Application logic not yet implemented")

    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
