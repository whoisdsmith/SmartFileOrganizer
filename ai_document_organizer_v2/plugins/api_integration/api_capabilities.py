"""
API Capability Negotiation Module for AI Document Organizer V2.

This module implements the API capability discovery and negotiation system,
allowing the application to dynamically adapt to different API providers
based on their available features and capabilities.
"""

import logging
import json
import re
import os
from enum import Enum, auto
from typing import Dict, List, Set, Any, Optional, Union, Tuple

logger = logging.getLogger(__name__)

class CapabilityLevel(Enum):
    """Enum representing capability support levels."""
    REQUIRED = auto()     # Feature must be supported
    PREFERRED = auto()    # Feature is preferred but not required
    OPTIONAL = auto()     # Feature is optional
    UNSUPPORTED = auto()  # Feature is not supported


class APICapability:
    """
    Class representing an API capability with metadata.
    """
    
    def __init__(self, name: str, description: str = "", 
                level: CapabilityLevel = CapabilityLevel.OPTIONAL,
                version: Optional[str] = None,
                parameters: Optional[Dict[str, Any]] = None):
        """
        Initialize an API capability.
        
        Args:
            name: Name of the capability
            description: Description of the capability
            level: Support level for the capability
            version: Optional version information for the capability
            parameters: Optional parameters for the capability
        """
        self.name = name
        self.description = description
        self.level = level
        self.version = version
        self.parameters = parameters or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the capability to a dictionary representation.
        
        Returns:
            Dictionary representation of the capability
        """
        return {
            "name": self.name,
            "description": self.description,
            "level": self.level.name,
            "version": self.version,
            "parameters": self.parameters
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'APICapability':
        """
        Create a capability from a dictionary representation.
        
        Args:
            data: Dictionary representation of a capability
            
        Returns:
            New APICapability instance
        """
        # Convert level string to enum
        level_str = data.get("level", "OPTIONAL")
        try:
            level = CapabilityLevel[level_str]
        except KeyError:
            logger.warning(f"Unknown capability level '{level_str}', defaulting to OPTIONAL")
            level = CapabilityLevel.OPTIONAL
        
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            level=level,
            version=data.get("version"),
            parameters=data.get("parameters", {})
        )
    
    def __eq__(self, other):
        """Compare capabilities by name."""
        if isinstance(other, APICapability):
            return self.name == other.name
        return False
    
    def __hash__(self):
        """Hash capability by name."""
        return hash(self.name)


class CapabilityRegistry:
    """
    Registry for API capabilities that manages capability definitions
    and capability set operations.
    """
    
    def __init__(self):
        """Initialize an empty capability registry."""
        self._capabilities: Dict[str, APICapability] = {}
    
    def register_capability(self, capability: APICapability) -> None:
        """
        Register a capability in the registry.
        
        Args:
            capability: The capability to register
        """
        self._capabilities[capability.name] = capability
        logger.debug(f"Registered capability: {capability.name}")
    
    def get_capability(self, name: str) -> Optional[APICapability]:
        """
        Get a capability by name.
        
        Args:
            name: Name of the capability to retrieve
            
        Returns:
            The capability if it exists, None otherwise
        """
        return self._capabilities.get(name)
    
    def list_capabilities(self) -> List[APICapability]:
        """
        Get a list of all registered capabilities.
        
        Returns:
            List of all capabilities
        """
        return list(self._capabilities.values())
    
    def get_capabilities_by_level(self, level: CapabilityLevel) -> List[APICapability]:
        """
        Get capabilities with the specified support level.
        
        Args:
            level: The capability level to filter by
            
        Returns:
            List of capabilities with the specified level
        """
        return [cap for cap in self._capabilities.values() if cap.level == level]
    
    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        """
        Convert the registry to a dictionary representation.
        
        Returns:
            Dictionary mapping capability names to capability dictionaries
        """
        return {name: cap.to_dict() for name, cap in self._capabilities.items()}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Dict[str, Any]]) -> 'CapabilityRegistry':
        """
        Create a registry from a dictionary representation.
        
        Args:
            data: Dictionary mapping capability names to capability dictionaries
            
        Returns:
            New CapabilityRegistry instance
        """
        registry = cls()
        for name, cap_data in data.items():
            # Ensure name in data matches key
            cap_data["name"] = name
            registry.register_capability(APICapability.from_dict(cap_data))
        return registry
    
    def clear(self) -> None:
        """Clear all capabilities from the registry."""
        self._capabilities.clear()


class CapabilitySet:
    """
    A set of API capabilities with operations for capability negotiation.
    """
    
    def __init__(self, capabilities: Optional[List[APICapability]] = None):
        """
        Initialize a capability set.
        
        Args:
            capabilities: Optional list of capabilities to include
        """
        self.capabilities: Set[APICapability] = set(capabilities or [])
    
    def add(self, capability: APICapability) -> None:
        """
        Add a capability to the set.
        
        Args:
            capability: The capability to add
        """
        self.capabilities.add(capability)
    
    def remove(self, capability_name: str) -> bool:
        """
        Remove a capability from the set.
        
        Args:
            capability_name: Name of the capability to remove
            
        Returns:
            True if the capability was removed, False if it wasn't in the set
        """
        for cap in self.capabilities:
            if cap.name == capability_name:
                self.capabilities.remove(cap)
                return True
        return False
    
    def contains(self, capability_name: str) -> bool:
        """
        Check if the set contains a capability.
        
        Args:
            capability_name: Name of the capability to check
            
        Returns:
            True if the capability is in the set, False otherwise
        """
        return any(cap.name == capability_name for cap in self.capabilities)
    
    def get(self, capability_name: str) -> Optional[APICapability]:
        """
        Get a capability from the set by name.
        
        Args:
            capability_name: Name of the capability to get
            
        Returns:
            The capability if found, None otherwise
        """
        for cap in self.capabilities:
            if cap.name == capability_name:
                return cap
        return None
    
    def get_names(self) -> Set[str]:
        """
        Get the set of capability names.
        
        Returns:
            Set of capability names
        """
        return {cap.name for cap in self.capabilities}
    
    def intersection(self, other: 'CapabilitySet') -> 'CapabilitySet':
        """
        Get the intersection of this set with another capability set.
        
        Args:
            other: The other capability set
            
        Returns:
            New capability set with capabilities in both sets
        """
        # Get the intersection of capability names
        common_names = self.get_names().intersection(other.get_names())
        
        # Create a new set with capabilities from this set that are in the intersection
        result = CapabilitySet()
        for cap in self.capabilities:
            if cap.name in common_names:
                result.add(cap)
        
        return result
    
    def union(self, other: 'CapabilitySet') -> 'CapabilitySet':
        """
        Get the union of this set with another capability set.
        
        Args:
            other: The other capability set
            
        Returns:
            New capability set with capabilities from both sets
        """
        result = CapabilitySet()
        
        # Add all capabilities from this set
        for cap in self.capabilities:
            result.add(cap)
        
        # Add capabilities from other set, overriding duplicates
        for cap in other.capabilities:
            if result.contains(cap.name):
                result.remove(cap.name)
            result.add(cap)
        
        return result
    
    def filter_by_level(self, level: CapabilityLevel) -> 'CapabilitySet':
        """
        Get a subset of capabilities with the specified level.
        
        Args:
            level: The capability level to filter by
            
        Returns:
            New capability set with capabilities of the specified level
        """
        result = CapabilitySet()
        for cap in self.capabilities:
            if cap.level == level:
                result.add(cap)
        return result
    
    def to_list(self) -> List[Dict[str, Any]]:
        """
        Convert the capability set to a list of dictionaries.
        
        Returns:
            List of capability dictionaries
        """
        return [cap.to_dict() for cap in self.capabilities]
    
    @classmethod
    def from_list(cls, data: List[Dict[str, Any]]) -> 'CapabilitySet':
        """
        Create a capability set from a list of dictionaries.
        
        Args:
            data: List of capability dictionaries
            
        Returns:
            New CapabilitySet instance
        """
        capabilities = [APICapability.from_dict(cap_data) for cap_data in data]
        return cls(capabilities)
    
    def __len__(self) -> int:
        """Get the number of capabilities in the set."""
        return len(self.capabilities)
    
    def __iter__(self):
        """Iterate over capabilities in the set."""
        return iter(self.capabilities)


class CapabilityNegotiator:
    """
    Negotiates API capabilities between the application and API providers.
    """
    
    def __init__(self, app_capabilities: Optional[CapabilitySet] = None,
                registry: Optional[CapabilityRegistry] = None):
        """
        Initialize a capability negotiator.
        
        Args:
            app_capabilities: Optional set of application capabilities
            registry: Optional capability registry
        """
        self.app_capabilities = app_capabilities or CapabilitySet()
        self.registry = registry or CapabilityRegistry()
        self.provider_capabilities: Dict[str, CapabilitySet] = {}
    
    def register_provider(self, provider_id: str, 
                         capabilities: CapabilitySet) -> None:
        """
        Register a provider's capabilities.
        
        Args:
            provider_id: Unique identifier for the provider
            capabilities: The provider's capability set
        """
        self.provider_capabilities[provider_id] = capabilities
        logger.info(f"Registered provider '{provider_id}' with {len(capabilities)} capabilities")
    
    def negotiate_capabilities(self, provider_id: str) -> Tuple[CapabilitySet, Dict[str, List[str]]]:
        """
        Negotiate capabilities with a provider.
        
        Args:
            provider_id: Identifier of the provider to negotiate with
            
        Returns:
            Tuple of (negotiated capability set, capability issues)
            
        Raises:
            ValueError: If the provider is not registered
        """
        if provider_id not in self.provider_capabilities:
            raise ValueError(f"Provider '{provider_id}' not registered")
        
        provider_caps = self.provider_capabilities[provider_id]
        
        # Get the intersection of app and provider capabilities
        common_caps = self.app_capabilities.intersection(provider_caps)
        
        # Track capability issues by level
        issues: Dict[str, List[str]] = {
            "missing_required": [],
            "missing_preferred": [],
            "additional": []
        }
        
        # Check for missing required capabilities
        required_caps = self.app_capabilities.filter_by_level(CapabilityLevel.REQUIRED)
        for cap in required_caps:
            if not provider_caps.contains(cap.name):
                issues["missing_required"].append(cap.name)
        
        # Check for missing preferred capabilities
        preferred_caps = self.app_capabilities.filter_by_level(CapabilityLevel.PREFERRED)
        for cap in preferred_caps:
            if not provider_caps.contains(cap.name):
                issues["missing_preferred"].append(cap.name)
        
        # Check for additional capabilities offered by the provider
        provider_names = provider_caps.get_names()
        app_names = self.app_capabilities.get_names()
        additional_names = provider_names - app_names
        issues["additional"] = list(additional_names)
        
        return common_caps, issues
    
    def find_compatible_providers(self, 
                                required_only: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Find providers compatible with the application's capabilities.
        
        Args:
            required_only: If True, only consider required capabilities
            
        Returns:
            Dictionary mapping provider IDs to compatibility information
        """
        results = {}
        
        # Filter app capabilities if only checking required ones
        app_caps = self.app_capabilities
        if required_only:
            app_caps = app_caps.filter_by_level(CapabilityLevel.REQUIRED)
        
        # Check each provider
        for provider_id, provider_caps in self.provider_capabilities.items():
            # Get common capabilities
            common_caps = app_caps.intersection(provider_caps)
            
            # Calculate compatibility score
            if len(app_caps) > 0:
                compatibility_score = len(common_caps) / len(app_caps)
            else:
                compatibility_score = 1.0
            
            # Check if all required capabilities are supported
            required_caps = self.app_capabilities.filter_by_level(CapabilityLevel.REQUIRED)
            missing_required = []
            for cap in required_caps:
                if not provider_caps.contains(cap.name):
                    missing_required.append(cap.name)
            
            results[provider_id] = {
                "compatibility_score": compatibility_score,
                "common_capabilities": len(common_caps),
                "total_app_capabilities": len(app_caps),
                "total_provider_capabilities": len(provider_caps),
                "missing_required": missing_required,
                "is_compatible": len(missing_required) == 0
            }
        
        return results
    
    def get_negotiated_parameters(self, provider_id: str,
                                capability_name: str) -> Dict[str, Any]:
        """
        Get negotiated parameters for a specific capability.
        
        Args:
            provider_id: Identifier of the provider
            capability_name: Name of the capability
            
        Returns:
            Dictionary of negotiated parameters
            
        Raises:
            ValueError: If the provider is not registered or the capability is not supported
        """
        if provider_id not in self.provider_capabilities:
            raise ValueError(f"Provider '{provider_id}' not registered")
        
        provider_caps = self.provider_capabilities[provider_id]
        provider_cap = provider_caps.get(capability_name)
        
        if not provider_cap:
            raise ValueError(f"Capability '{capability_name}' not supported by provider '{provider_id}'")
        
        app_cap = self.app_capabilities.get(capability_name)
        
        if not app_cap:
            raise ValueError(f"Capability '{capability_name}' not supported by application")
        
        # Start with application parameters
        params = app_cap.parameters.copy()
        
        # Override with provider parameters
        for key, value in provider_cap.parameters.items():
            params[key] = value
        
        return params
    
    def update_app_capabilities(self, capabilities: CapabilitySet) -> None:
        """
        Update the application's capabilities.
        
        Args:
            capabilities: New application capabilities
        """
        self.app_capabilities = capabilities
    
    def save_to_file(self, file_path: str) -> bool:
        """
        Save the negotiator state to a file.
        
        Args:
            file_path: Path to save the state to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            data = {
                "app_capabilities": self.app_capabilities.to_list(),
                "providers": {
                    provider_id: caps.to_list()
                    for provider_id, caps in self.provider_capabilities.items()
                },
                "registry": self.registry.to_dict()
            }
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"Failed to save capability negotiator to {file_path}: {e}")
            return False
    
    @classmethod
    def load_from_file(cls, file_path: str) -> Optional['CapabilityNegotiator']:
        """
        Load negotiator state from a file.
        
        Args:
            file_path: Path to load the state from
            
        Returns:
            New CapabilityNegotiator instance or None if loading failed
        """
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Create registry
            registry = CapabilityRegistry.from_dict(data.get("registry", {}))
            
            # Create app capabilities
            app_capabilities = CapabilitySet.from_list(data.get("app_capabilities", []))
            
            # Create negotiator
            negotiator = cls(app_capabilities, registry)
            
            # Add providers
            for provider_id, caps_list in data.get("providers", {}).items():
                negotiator.register_provider(
                    provider_id,
                    CapabilitySet.from_list(caps_list)
                )
            
            return negotiator
        except Exception as e:
            logger.error(f"Failed to load capability negotiator from {file_path}: {e}")
            return None


class APIDiscovery:
    """
    Discovers and registers API capabilities from providers.
    """
    
    def __init__(self, registry: Optional[CapabilityRegistry] = None,
                negotiator: Optional[CapabilityNegotiator] = None):
        """
        Initialize the API discovery system.
        
        Args:
            registry: Optional capability registry
            negotiator: Optional capability negotiator
        """
        self.registry = registry or CapabilityRegistry()
        self.negotiator = negotiator or CapabilityNegotiator(registry=self.registry)
    
    def discover_capabilities_from_endpoint(self, provider_id: str,
                                          url: str, headers: Optional[Dict[str, str]] = None,
                                          auth: Optional[Dict[str, str]] = None) -> bool:
        """
        Discover capabilities from a provider's discovery endpoint.
        
        Args:
            provider_id: Unique identifier for the provider
            url: URL of the discovery endpoint
            headers: Optional headers for the request
            auth: Optional authentication information
            
        Returns:
            True if discovery was successful, False otherwise
        """
        try:
            import requests
            
            # Prepare request
            request_headers = headers or {}
            request_auth = None
            
            if auth:
                if 'type' in auth and auth['type'] == 'basic':
                    request_auth = (auth.get('username', ''), auth.get('password', ''))
                else:
                    # API key auth
                    key_name = auth.get('key_name', 'Authorization')
                    key_value = auth.get('key_value', '')
                    key_prefix = auth.get('key_prefix', 'Bearer')
                    
                    if key_prefix:
                        request_headers[key_name] = f"{key_prefix} {key_value}"
                    else:
                        request_headers[key_name] = key_value
            
            # Make request
            response = requests.get(url, headers=request_headers, auth=request_auth)
            response.raise_for_status()
            
            # Parse response
            data = response.json()
            
            # Extract capabilities
            capabilities_data = data.get('capabilities', [])
            capabilities = CapabilitySet.from_list(capabilities_data)
            
            # Register provider
            self.negotiator.register_provider(provider_id, capabilities)
            
            return True
        except Exception as e:
            logger.error(f"Failed to discover capabilities from {url}: {e}")
            return False
    
    def discover_capabilities_from_file(self, provider_id: str,
                                      file_path: str) -> bool:
        """
        Discover capabilities from a JSON file.
        
        Args:
            provider_id: Unique identifier for the provider
            file_path: Path to the capability definition file
            
        Returns:
            True if discovery was successful, False otherwise
        """
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Extract capabilities
            capabilities_data = data.get('capabilities', [])
            capabilities = CapabilitySet.from_list(capabilities_data)
            
            # Register provider
            self.negotiator.register_provider(provider_id, capabilities)
            
            return True
        except Exception as e:
            logger.error(f"Failed to discover capabilities from {file_path}: {e}")
            return False
    
    def register_standard_capabilities(self) -> None:
        """Register standard capabilities in the registry."""
        # Text analysis capabilities
        self.registry.register_capability(APICapability(
            name="text_analysis",
            description="Ability to analyze text content",
            level=CapabilityLevel.REQUIRED,
            version="1.0",
            parameters={"max_text_length": 100000}
        ))
        
        self.registry.register_capability(APICapability(
            name="sentiment_analysis",
            description="Detect sentiment in text",
            level=CapabilityLevel.OPTIONAL,
            version="1.0",
            parameters={"languages": ["en"]}
        ))
        
        self.registry.register_capability(APICapability(
            name="entity_extraction",
            description="Extract named entities from text",
            level=CapabilityLevel.PREFERRED,
            version="1.0",
            parameters={"entity_types": ["person", "organization", "location", "date"]}
        ))
        
        self.registry.register_capability(APICapability(
            name="text_summarization",
            description="Generate summaries of text content",
            level=CapabilityLevel.PREFERRED,
            version="1.0",
            parameters={"max_summary_length": 1000}
        ))
        
        self.registry.register_capability(APICapability(
            name="text_classification",
            description="Classify text into categories",
            level=CapabilityLevel.OPTIONAL,
            version="1.0",
            parameters={"max_categories": 5}
        ))
        
        # Image analysis capabilities
        self.registry.register_capability(APICapability(
            name="image_analysis",
            description="Ability to analyze image content",
            level=CapabilityLevel.REQUIRED,
            version="1.0",
            parameters={"max_image_size": 10485760}  # 10MB
        ))
        
        self.registry.register_capability(APICapability(
            name="object_detection",
            description="Detect objects in images",
            level=CapabilityLevel.PREFERRED,
            version="1.0",
            parameters={"min_confidence": 0.6}
        ))
        
        self.registry.register_capability(APICapability(
            name="facial_recognition",
            description="Detect and recognize faces in images",
            level=CapabilityLevel.OPTIONAL,
            version="1.0",
            parameters={"detect_attributes": True}
        ))
        
        self.registry.register_capability(APICapability(
            name="image_ocr",
            description="Extract text from images",
            level=CapabilityLevel.PREFERRED,
            version="1.0",
            parameters={"languages": ["en"]}
        ))
        
        # Audio analysis capabilities
        self.registry.register_capability(APICapability(
            name="audio_analysis",
            description="Ability to analyze audio content",
            level=CapabilityLevel.OPTIONAL,
            version="1.0",
            parameters={"max_audio_length": 600}  # 10 minutes
        ))
        
        self.registry.register_capability(APICapability(
            name="speech_to_text",
            description="Convert speech to text",
            level=CapabilityLevel.OPTIONAL,
            version="1.0",
            parameters={"languages": ["en"]}
        ))
        
        # PDF processing capabilities
        self.registry.register_capability(APICapability(
            name="pdf_extraction",
            description="Extract content from PDF files",
            level=CapabilityLevel.REQUIRED,
            version="1.0",
            parameters={"extract_images": True}
        ))
        
        self.registry.register_capability(APICapability(
            name="pdf_ocr",
            description="OCR for image-based PDFs",
            level=CapabilityLevel.PREFERRED,
            version="1.0",
            parameters={"languages": ["en"]}
        ))
        
        # Vector operations
        self.registry.register_capability(APICapability(
            name="vector_embeddings",
            description="Generate vector embeddings for content",
            level=CapabilityLevel.OPTIONAL,
            version="1.0",
            parameters={"embedding_dimensions": 1536}
        ))
        
        self.registry.register_capability(APICapability(
            name="vector_search",
            description="Search for similar content using vectors",
            level=CapabilityLevel.OPTIONAL,
            version="1.0",
            parameters={"max_results": 10}
        ))
    
    def setup_default_app_capabilities(self) -> None:
        """Set up default application capabilities."""
        # Create capability set
        app_capabilities = CapabilitySet()
        
        # Add required capabilities
        for cap in self.registry.get_capabilities_by_level(CapabilityLevel.REQUIRED):
            app_capabilities.add(cap)
        
        # Add preferred capabilities
        for cap in self.registry.get_capabilities_by_level(CapabilityLevel.PREFERRED):
            app_capabilities.add(cap)
        
        # Add selected optional capabilities
        optional_capabilities = [
            "sentiment_analysis",
            "text_classification",
            "audio_analysis",
            "speech_to_text",
            "vector_embeddings"
        ]
        
        for cap_name in optional_capabilities:
            cap = self.registry.get_capability(cap_name)
            if cap:
                app_capabilities.add(cap)
        
        # Update negotiator
        self.negotiator.update_app_capabilities(app_capabilities)


# Initialize global capability registry and negotiator
DEFAULT_REGISTRY = CapabilityRegistry()
DEFAULT_NEGOTIATOR = CapabilityNegotiator(registry=DEFAULT_REGISTRY)
DEFAULT_DISCOVERY = APIDiscovery(DEFAULT_REGISTRY, DEFAULT_NEGOTIATOR)