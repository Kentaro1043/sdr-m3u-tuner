import argparse
import random
import sys
from pathlib import Path

import yaml
from loguru import logger

from .gr.file_source import file_source


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


def is_port_available(port: int) -> bool:
    """Check if a port is available for use.

    Args:
        port: Port number to check

    Returns:
        bool: True if port is available, False otherwise
    """
    import socket

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", port))
            return True
    except OSError:
        return False


def find_available_port(
    start_port: int = 49152, end_port: int = 65535, max_attempts: int = 100
) -> int:
    """Find an available port within the specified range.

    Args:
        start_port: Starting port number (default: 49152)
        end_port: Ending port number (default: 65535)
        max_attempts: Maximum number of attempts to find a port

    Returns:
        int: Available port number

    Raises:
        RuntimeError: If no available port is found after max_attempts
    """
    for _ in range(max_attempts):
        port = random.randint(start_port, end_port)
        if is_port_available(port):
            return port

    raise RuntimeError(
        f"Could not find an available port after {max_attempts} attempts"
    )


def init_file_source(source_file_path: str):
    """Initialize file source with ZeroMQ distribution.

    Args:
        source_file_path: Path to the source audio file

    Returns:
        tuple: (file_source_instance, pub_address)
    """
    # Find an available port for ZeroMQ (ephemeral port range: 49152-65535)
    random_port = find_available_port()
    pub_address = f"tcp://127.0.0.1:{random_port}"

    logger.info(f"Initializing file source with file: {source_file_path}")
    logger.debug(f"ZeroMQ publish address: {pub_address}")

    # Create file source instance
    fs_instance = file_source()

    # Configure the source file path and pub address
    fs_instance.set_source_file_path(source_file_path)
    fs_instance.set_pub_address(pub_address)

    return fs_instance, pub_address


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
        logger.info(f"Server Port: {config.get('port', 'Not configured')}")

        # Initialize file sources if configured
        file_sources = []
        if "sources" in config:
            for source in config["sources"]:
                if source.get("type") == "file" and "file" in source:
                    logger.info(
                        f"Found file source: {source['id']} -> {source['file']}"
                    )
                    fs_instance, pub_address = init_file_source(source["file"])
                    file_sources.append(
                        {
                            "id": source["id"],
                            "instance": fs_instance,
                            "pub_address": pub_address,
                        }
                    )
                    logger.info(
                        f"File source {source['id']} initialized with publish address: {pub_address}"
                    )

            if file_sources:
                # Start all GNU Radio flowgraphs
                for fs in file_sources:
                    fs["instance"].start()
                    fs[
                        "instance"
                    ].flowgraph_started.wait()  # Wait for flowgraph to start
                    logger.info(
                        f"GNU Radio flowgraph for {fs['id']} started successfully"
                    )

                try:
                    # Keep the application running
                    logger.info("SDR m3u Tuner running. Press Ctrl+C to stop.")
                    while True:
                        import time

                        time.sleep(1)
                except KeyboardInterrupt:
                    logger.info("Shutting down...")
                    for fs in file_sources:
                        fs["instance"].stop()
                        fs["instance"].wait()
            else:
                logger.warning("No file sources found in configuration")
                logger.info("SDR m3u Tuner started successfully")
                logger.info("Application logic not yet implemented")
        else:
            logger.warning("No sources configured in config file")
            logger.info("SDR m3u Tuner started successfully")
            logger.info("Application logic not yet implemented")

    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
