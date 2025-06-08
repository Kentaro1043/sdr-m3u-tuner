import random
import socket


class random_url:
    def is_port_available(port):
        """Check if a port is available for use.

        Args:
            port: Port number to check

        Returns:
            bool: True if port is available, False otherwise
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False

    def find_available_port(self):
        """Find an available port within the specified range.

        Returns:
            int: Available port number

        Raises:
            RuntimeError: If no available port is found after 100 attempts
        """
        for _ in range(100):
            port = random.randint(49152, 65535)
            if self.is_port_available(port):
                return port

        raise RuntimeError("Could not find an available port after 100 attempts")

    def make_tcp_url(self):
        """Generate a TCP URL with an available port.

        Returns:
                str: TCP URL with the available port
        """
        port = self.find_available_port()
        return f"tcp://127.0.0.1:{port}"
