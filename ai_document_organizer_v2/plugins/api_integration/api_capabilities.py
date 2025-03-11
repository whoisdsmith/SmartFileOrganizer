"""
API Capabilities Module for External API Integration Framework.

This module provides classes and utilities for runtime API capabilities discovery 
and negotiation, allowing the application to adapt to different API versions
and feature sets at runtime.
"""

import logging
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from enum import Enum

logger = logging.getLogger(__name__)


class CapabilityCategory(Enum):
    """Enumeration of API capability categories."""
    AUTHENTICATION = "authentication"
    DATA_FORMAT = "data_format"
    OPERATIONS = "operations"
    PERFORMANCE = "performance"
    INTEGRATION = "integration"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    EXTENSION = "extension"


class APICapability:
    """
    Represents a single API capability with its properties and requirements.
    """
    
    def __init__(self, 
                name: str, 
                category: Union[CapabilityCategory, str],
                description: str = "",
                version_introduced: Optional[str] = None,
                version_deprecated: Optional[str] = None,
                required_capabilities: Optional[List[str]] = None,
                properties: Optional[Dict[str, Any]] = None):
        """
        Initialize an API capability.
        
        Args:
            name: Unique identifier for the capability
            category: Category of the capability
            description: Human-readable description of the capability
            version_introduced: API version where this capability was introduced
            version_deprecated: API version where this capability was deprecated
            required_capabilities: List of other capabilities required by this one
            properties: Additional properties describing the capability
        """
        self.name = name
        
        if isinstance(category, str):
            try:
                self.category = CapabilityCategory(category)
            except ValueError:
                self.category = CapabilityCategory.EXTENSION
                logger.warning(f"Unknown capability category '{category}', using EXTENSION")
        else:
            self.category = category
            
        self.description = description
        self.version_introduced = version_introduced
        self.version_deprecated = version_deprecated
        self.required_capabilities = required_capabilities or []
        self.properties = properties or {}
    
    def is_available_in_version(self, version: str) -> bool:
        """
        Check if the capability is available in the specified API version.
        
        Args:
            version: API version to check against
            
        Returns:
            True if the capability is available in the specified version
        """
        if not self.version_introduced:
            return True
            
        if not version:
            return False
            
        # Simple version comparison - can be enhanced with semver
        if self.version_introduced and version < self.version_introduced:
            return False
            
        if self.version_deprecated and version >= self.version_deprecated:
            return False
            
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the capability to a dictionary representation.
        
        Returns:
            Dictionary representation of the capability
        """
        return {
            'name': self.name,
            'category': self.category.value,
            'description': self.description,
            'version_introduced': self.version_introduced,
            'version_deprecated': self.version_deprecated,
            'required_capabilities': self.required_capabilities,
            'properties': self.properties
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'APICapability':
        """
        Create a capability from a dictionary representation.
        
        Args:
            data: Dictionary representation of the capability
            
        Returns:
            New APICapability instance
        """
        return cls(
            name=data.get('name', ''),
            category=data.get('category', CapabilityCategory.EXTENSION.value),
            description=data.get('description', ''),
            version_introduced=data.get('version_introduced'),
            version_deprecated=data.get('version_deprecated'),
            required_capabilities=data.get('required_capabilities', []),
            properties=data.get('properties', {})
        )
    
    def __str__(self) -> str:
        """String representation of the capability."""
        return f"{self.name} ({self.category.value})"
    
    def __eq__(self, other) -> bool:
        """Check if two capabilities are equal."""
        if not isinstance(other, APICapability):
            return False
        return self.name == other.name and self.category == other.category
    
    def __hash__(self) -> int:
        """Hash function for the capability."""
        return hash((self.name, self.category))


class APICapabilityRegistry:
    """
    Registry for tracking and managing API capabilities.
    """
    
    def __init__(self):
        """Initialize the API capability registry."""
        self.capabilities = {}  # type: Dict[str, APICapability]
        self.standard_capabilities = self._create_standard_capabilities()
        
        # Register standard capabilities
        for cap in self.standard_capabilities:
            self.register_capability(cap)
    
    def _create_standard_capabilities(self) -> List[APICapability]:
        """
        Create a list of standard capabilities common across many APIs.
        
        Returns:
            List of standard APICapability instances
        """
        return [
            # Authentication capabilities
            APICapability(
                name="auth:api_key",
                category=CapabilityCategory.AUTHENTICATION,
                description="API Key Authentication"
            ),
            APICapability(
                name="auth:oauth2",
                category=CapabilityCategory.AUTHENTICATION,
                description="OAuth 2.0 Authentication"
            ),
            APICapability(
                name="auth:jwt",
                category=CapabilityCategory.AUTHENTICATION,
                description="JWT Authentication"
            ),
            
            # Data format capabilities
            APICapability(
                name="format:json",
                category=CapabilityCategory.DATA_FORMAT,
                description="JSON Data Format"
            ),
            APICapability(
                name="format:xml",
                category=CapabilityCategory.DATA_FORMAT,
                description="XML Data Format"
            ),
            APICapability(
                name="format:binary",
                category=CapabilityCategory.DATA_FORMAT,
                description="Binary Data Format"
            ),
            
            # Integration capabilities
            APICapability(
                name="integration:webhooks",
                category=CapabilityCategory.INTEGRATION,
                description="Webhook Support"
            ),
            APICapability(
                name="integration:streaming",
                category=CapabilityCategory.INTEGRATION,
                description="Streaming Data Support"
            ),
            APICapability(
                name="integration:batch",
                category=CapabilityCategory.INTEGRATION,
                description="Batch Operation Support"
            ),
            
            # Performance capabilities
            APICapability(
                name="performance:caching",
                category=CapabilityCategory.PERFORMANCE,
                description="Response Caching Support"
            ),
            APICapability(
                name="performance:rate_limited",
                category=CapabilityCategory.PERFORMANCE,
                description="API is rate limited"
            ),
            
            # Security capabilities
            APICapability(
                name="security:request_signing",
                category=CapabilityCategory.SECURITY,
                description="Request Signing Support"
            ),
            APICapability(
                name="security:encryption",
                category=CapabilityCategory.SECURITY,
                description="Payload Encryption Support"
            )
        ]
    
    def register_capability(self, capability: APICapability) -> bool:
        """
        Register a capability with the registry.
        
        Args:
            capability: APICapability instance to register
            
        Returns:
            True if registration was successful, False otherwise
        """
        if not isinstance(capability, APICapability):
            logger.error(f"Cannot register non-APICapability object: {capability}")
            return False
            
        self.capabilities[capability.name] = capability
        return True
    
    def unregister_capability(self, capability_name: str) -> bool:
        """
        Unregister a capability from the registry.
        
        Args:
            capability_name: Name of the capability to unregister
            
        Returns:
            True if unregistration was successful, False otherwise
        """
        if capability_name in self.capabilities:
            del self.capabilities[capability_name]
            return True
        return False
    
    def get_capability(self, capability_name: str) -> Optional[APICapability]:
        """
        Get a capability by name.
        
        Args:
            capability_name: Name of the capability to retrieve
            
        Returns:
            APICapability instance or None if not found
        """
        return self.capabilities.get(capability_name)
    
    def get_capabilities_by_category(self, category: Union[CapabilityCategory, str]) -> List[APICapability]:
        """
        Get all capabilities in a specific category.
        
        Args:
            category: Category to filter by
            
        Returns:
            List of APICapability instances in the specified category
        """
        if isinstance(category, str):
            try:
                category = CapabilityCategory(category)
            except ValueError:
                logger.warning(f"Unknown capability category '{category}'")
                return []
                
        return [cap for cap in self.capabilities.values() if cap.category == category]
    
    def get_all_capabilities(self) -> List[APICapability]:
        """
        Get all registered capabilities.
        
        Returns:
            List of all registered APICapability instances
        """
        return list(self.capabilities.values())
    
    def filter_capabilities_by_version(self, version: str) -> List[APICapability]:
        """
        Filter capabilities by API version.
        
        Args:
            version: API version to filter by
            
        Returns:
            List of APICapability instances available in the specified version
        """
        return [
            cap for cap in self.capabilities.values() 
            if cap.is_available_in_version(version)
        ]
    
    def clear(self) -> None:
        """Clear all registered capabilities."""
        self.capabilities.clear()
        
        # Re-register standard capabilities
        for cap in self.standard_capabilities:
            self.register_capability(cap)


class CapabilitySet:
    """
    Represents a set of capabilities supported by an API or required by a client.
    Used for capability negotiation.
    """
    
    def __init__(self, capabilities: Optional[List[Union[str, APICapability]]] = None):
        """
        Initialize a capability set.
        
        Args:
            capabilities: Optional list of capabilities or capability names
        """
        self.capability_names = set()  # type: Set[str]
        
        if capabilities:
            for cap in capabilities:
                if isinstance(cap, APICapability):
                    self.capability_names.add(cap.name)
                elif isinstance(cap, str):
                    self.capability_names.add(cap)
                else:
                    logger.warning(f"Ignoring invalid capability type: {type(cap)}")
    
    def add_capability(self, capability: Union[str, APICapability]) -> bool:
        """
        Add a capability to the set.
        
        Args:
            capability: Capability or capability name to add
            
        Returns:
            True if the capability was added, False otherwise
        """
        if isinstance(capability, APICapability):
            self.capability_names.add(capability.name)
            return True
        elif isinstance(capability, str):
            self.capability_names.add(capability)
            return True
        else:
            logger.warning(f"Cannot add invalid capability type: {type(capability)}")
            return False
    
    def remove_capability(self, capability: Union[str, APICapability]) -> bool:
        """
        Remove a capability from the set.
        
        Args:
            capability: Capability or capability name to remove
            
        Returns:
            True if the capability was removed, False otherwise
        """
        name = capability.name if isinstance(capability, APICapability) else capability
        
        if name in self.capability_names:
            self.capability_names.remove(name)
            return True
        return False
    
    def has_capability(self, capability: Union[str, APICapability]) -> bool:
        """
        Check if the set contains a specific capability.
        
        Args:
            capability: Capability or capability name to check
            
        Returns:
            True if the capability is in the set, False otherwise
        """
        name = capability.name if isinstance(capability, APICapability) else capability
        return name in self.capability_names
    
    def get_capability_names(self) -> List[str]:
        """
        Get a list of capability names in the set.
        
        Returns:
            List of capability names
        """
        return list(self.capability_names)
    
    def get_capabilities(self, registry: APICapabilityRegistry) -> List[APICapability]:
        """
        Get a list of capability objects in the set.
        
        Args:
            registry: APICapabilityRegistry to resolve capability names
            
        Returns:
            List of APICapability objects
        """
        result = []
        for name in self.capability_names:
            cap = registry.get_capability(name)
            if cap:
                result.append(cap)
            else:
                logger.warning(f"Unknown capability '{name}' not found in registry")
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the capability set to a dictionary representation.
        
        Returns:
            Dictionary representation of the capability set
        """
        return {
            'capabilities': list(self.capability_names)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CapabilitySet':
        """
        Create a capability set from a dictionary representation.
        
        Args:
            data: Dictionary representation of the capability set
            
        Returns:
            New CapabilitySet instance
        """
        return cls(capabilities=data.get('capabilities', []))
    
    def is_compatible_with(self, required_set: 'CapabilitySet') -> bool:
        """
        Check if this capability set is compatible with a required set.
        
        Args:
            required_set: CapabilitySet containing required capabilities
            
        Returns:
            True if this set contains all capabilities in the required set
        """
        return required_set.capability_names.issubset(self.capability_names)
    
    def get_missing_capabilities(self, required_set: 'CapabilitySet') -> List[str]:
        """
        Get a list of capability names that are in the required set but not in this set.
        
        Args:
            required_set: CapabilitySet containing required capabilities
            
        Returns:
            List of missing capability names
        """
        return list(required_set.capability_names - self.capability_names)
    
    def __str__(self) -> str:
        """String representation of the capability set."""
        return f"CapabilitySet({sorted(list(self.capability_names))})"
    
    def __len__(self) -> int:
        """Number of capabilities in the set."""
        return len(self.capability_names)


class APICapabilityNegotiator:
    """
    Handles discovery and negotiation of API capabilities between client and service.
    """
    
    def __init__(self, registry: Optional[APICapabilityRegistry] = None):
        """
        Initialize the capability negotiator.
        
        Args:
            registry: Optional capability registry to use
        """
        self.registry = registry or APICapabilityRegistry()
    
    def negotiate_capabilities(self, 
                             available_capabilities: CapabilitySet,
                             required_capabilities: CapabilitySet) -> Tuple[bool, CapabilitySet, List[str]]:
        """
        Negotiate capabilities between what's available and what's required.
        
        Args:
            available_capabilities: Set of capabilities available to the API
            required_capabilities: Set of capabilities required by the client
            
        Returns:
            Tuple containing:
            - Boolean indicating if negotiation was successful
            - CapabilitySet of negotiated capabilities (intersection)
            - List of missing capability names
        """
        # Check if all required capabilities are available
        if available_capabilities.is_compatible_with(required_capabilities):
            # Create a new set with only the capabilities that are required
            negotiated = CapabilitySet(required_capabilities.get_capability_names())
            return True, negotiated, []
        
        # Get the missing capabilities
        missing = required_capabilities.get_missing_capabilities(available_capabilities)
        
        # Create a set with the intersection of available and required capabilities
        negotiated_names = set(required_capabilities.capability_names) - set(missing)
        negotiated = CapabilitySet(list(negotiated_names))
        
        return False, negotiated, missing
    
    def discover_api_capabilities(self, plugin_name: str, api_gateway) -> Optional[CapabilitySet]:
        """
        Discover capabilities of an API through its plugin.
        
        Args:
            plugin_name: Name of the plugin to query
            api_gateway: APIGateway instance for plugin access
            
        Returns:
            CapabilitySet of discovered capabilities or None on failure
        """
        plugin = api_gateway.get_plugin(plugin_name)
        
        if not plugin:
            logger.error(f"Plugin {plugin_name} is not registered")
            return None
            
        try:
            # Get capability set from plugin
            capabilities = self._get_plugin_capabilities(plugin)
            return capabilities
            
        except Exception as e:
            logger.error(f"Error discovering capabilities for plugin {plugin_name}: {e}")
            return None
    
    def discover_capabilities_from_api(self, 
                                     plugin_name: str, 
                                     api_gateway,
                                     capability_endpoint: str = '/capabilities') -> Optional[CapabilitySet]:
        """
        Discover capabilities by making a request to the API's capability endpoint.
        
        Args:
            plugin_name: Name of the plugin to use
            api_gateway: APIGateway instance for plugin access
            capability_endpoint: API endpoint for capability discovery
            
        Returns:
            CapabilitySet of discovered capabilities or None on failure
        """
        plugin = api_gateway.get_plugin(plugin_name)
        
        if not plugin:
            logger.error(f"Plugin {plugin_name} is not registered")
            return None
            
        try:
            # Make a request to the capability endpoint
            result = api_gateway.execute_request(
                plugin_name=plugin_name,
                endpoint=capability_endpoint,
                method='GET'
            )
            
            if not result.get('success', False):
                logger.error(f"Failed to discover capabilities from API: {result.get('error')}")
                
                # Fall back to plugin capabilities
                logger.info("Falling back to plugin capability declarations")
                return self._get_plugin_capabilities(plugin)
            
            # Parse the capabilities from the response
            capabilities_data = result.get('data', {}).get('capabilities', [])
            capabilities = CapabilitySet(capabilities_data)
            
            return capabilities
            
        except Exception as e:
            logger.error(f"Error discovering capabilities from API: {e}")
            
            # Fall back to plugin capabilities
            logger.info("Falling back to plugin capability declarations due to error")
            return self._get_plugin_capabilities(plugin)
    
    def _get_plugin_capabilities(self, plugin) -> CapabilitySet:
        """
        Extract capabilities from a plugin instance.
        
        Args:
            plugin: APIPluginBase instance
            
        Returns:
            CapabilitySet of plugin capabilities
        """
        capabilities = CapabilitySet()
        
        # Add authentication capabilities
        for auth_method in plugin.supported_auth_methods:
            capabilities.add_capability(f"auth:{auth_method}")
        
        # Add common capabilities based on plugin properties
        self._add_common_capabilities(plugin, capabilities)
        
        # Add protocol/format capabilities
        capabilities.add_capability("format:json")  # Most APIs support JSON
        
        # Add operation-specific capabilities
        for operation in plugin.available_operations:
            capabilities.add_capability(f"operation:{operation}")
        
        return capabilities
    
    def _add_common_capabilities(self, plugin, capabilities: CapabilitySet) -> None:
        """
        Add common capabilities based on plugin properties.
        
        Args:
            plugin: APIPluginBase instance
            capabilities: CapabilitySet to add capabilities to
        """
        # Integration capabilities
        if plugin.supports_webhooks:
            capabilities.add_capability("integration:webhooks")
            
        if plugin.supports_streaming:
            capabilities.add_capability("integration:streaming")
            
        if plugin.supports_batch_operations:
            capabilities.add_capability("integration:batch")
        
        # Performance capabilities
        if plugin.supports_caching:
            capabilities.add_capability("performance:caching")
            
        if plugin.requires_rate_limiting:
            capabilities.add_capability("performance:rate_limited")


# Create a global instance for convenience
default_capability_registry = APICapabilityRegistry()