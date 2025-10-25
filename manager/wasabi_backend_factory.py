"""Factory for creating appropriate Wasabi backend and coordinator instances."""

from typing import Literal
from manager.wasabi_backend import WasabiBackend
from manager.wasabi_backend_26 import WasabiBackend26
from manager.wasabi_coordinator import WasabiCoordinator
from manager.wasabi_backend_protocol import WasabiBackendProtocol
from manager.wasabi_coordinator_protocol import WasabiCoordinatorProtocol


BackendArchitecture = Literal["legacy", "split"]


def detect_backend_architecture(versions: set[str]) -> BackendArchitecture:
    """Detect which backend architecture to use based on client versions.
    
    Args:
        versions: Set of Wasabi client versions in use
        
    Returns:
        "legacy" for versions < 2.6.0 (integrated backend+coordinator)
        "split" for versions >= 2.6.0 (separate backend and coordinator)
    """
    return "split" if any(version >= "2.6.0" for version in versions) else "legacy"


def create_backend(
    architecture: BackendArchitecture,
    host: str = "localhost",
    port: int = 37127,
    internal_ip: str = "",
    proxy: str = ""
) -> WasabiBackendProtocol:
    """Create an appropriate backend instance based on architecture.
    
    Args:
        architecture: The backend architecture to use
        host: Backend host address
        port: Backend port
        internal_ip: Internal IP address for container communication
        proxy: Proxy URL if using one
        
    Returns:
        A backend instance implementing WasabiBackendProtocol
    """
    if architecture == "split":
        return WasabiBackend26(host=host, port=port, internal_ip=internal_ip, proxy=proxy)
    else:
        return WasabiBackend(host=host, port=port, internal_ip=internal_ip, proxy=proxy)


def create_coordinator(
    host: str = "localhost",
    port: int = 37128,
    internal_ip: str = "",
    proxy: str = ""
) -> WasabiCoordinatorProtocol:
    """Create a coordinator instance.
    
    Note: Only used with "split" architecture (2.6.0+).
    
    Args:
        host: Coordinator host address
        port: Coordinator port
        internal_ip: Internal IP address for container communication
        proxy: Proxy URL if using one
        
    Returns:
        A coordinator instance implementing WasabiCoordinatorProtocol
    """
    return WasabiCoordinator(host=host, port=port, internal_ip=internal_ip, proxy=proxy)


def get_backend_container_name(architecture: BackendArchitecture) -> str:
    """Get the container name for the backend.
    
    Args:
        architecture: The backend architecture to use
        
    Returns:
        Container name string
    """
    return "wasabi-backend-2.6" if architecture == "split" else "wasabi-backend"


def get_backend_image_names(architecture: BackendArchitecture) -> list[str]:
    """Get the image names needed for the backend architecture.
    
    Args:
        architecture: The backend architecture to use
        
    Returns:
        List of image names to prepare
    """
    if architecture == "split":
        return ["wasabi-backend-2.6", "wasabi-coordinator"]
    else:
        return ["wasabi-backend"]
