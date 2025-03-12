"""
Test module for API capability discovery and negotiation.
"""

import unittest
from unittest.mock import MagicMock, patch

from ..plugins.api_integration.api_capabilities import (
    APICapability, APICapabilityRegistry, CapabilitySet, APICapabilityNegotiator,
    CapabilityCategory
)
from ..plugins.api_integration.api_plugin_base import APIPluginBase
from ..plugins.api_integration.api_gateway import APIGateway

class TestCapabilityBasics(unittest.TestCase):
    """Test the basic functionality of capability classes."""
    
    def test_capability_creation(self):
        """Test creating and manipulating capabilities."""
        # Create a capability
        cap = APICapability(
            name="test:capability",
            category=CapabilityCategory.OPERATIONS,
            description="Test capability",
            version_introduced="1.0",
            version_deprecated="2.0"
        )
        
        # Check basic properties
        self.assertEqual(cap.name, "test:capability")
        self.assertEqual(cap.category, CapabilityCategory.OPERATIONS)
        self.assertEqual(cap.description, "Test capability")
        self.assertEqual(cap.version_introduced, "1.0")
        self.assertEqual(cap.version_deprecated, "2.0")
        
        # Test version checks
        self.assertTrue(cap.is_available_in_version("1.5"))
        self.assertFalse(cap.is_available_in_version("0.9"))
        self.assertFalse(cap.is_available_in_version("2.0"))
        
        # Test conversion to dict and back
        cap_dict = cap.to_dict()
        cap2 = APICapability.from_dict(cap_dict)
        self.assertEqual(cap.name, cap2.name)
        self.assertEqual(cap.category, cap2.category)

    def test_capability_registry(self):
        """Test registering and retrieving capabilities."""
        registry = APICapabilityRegistry()
        
        # Create a test capability
        cap = APICapability(
            name="test:capability",
            category=CapabilityCategory.OPERATIONS,
            description="Test capability"
        )
        
        # Register and retrieve
        self.assertTrue(registry.register_capability(cap))
        retrieved_cap = registry.get_capability("test:capability")
        self.assertEqual(cap.name, retrieved_cap.name)
        
        # Check category filtering
        caps_in_category = registry.get_capabilities_by_category(CapabilityCategory.OPERATIONS)
        self.assertIn(cap, caps_in_category)
        
        # Test unregistration
        self.assertTrue(registry.unregister_capability("test:capability"))
        self.assertIsNone(registry.get_capability("test:capability"))
        
        # Check default capabilities
        auth_caps = registry.get_capabilities_by_category(CapabilityCategory.AUTHENTICATION)
        self.assertGreater(len(auth_caps), 0)
        
    def test_capability_set(self):
        """Test capability sets for negotiation."""
        # Create a capability set
        cap_set = CapabilitySet(["auth:api_key", "format:json", "operation:get_user"])
        
        # Check membership
        self.assertTrue(cap_set.has_capability("auth:api_key"))
        self.assertFalse(cap_set.has_capability("auth:oauth2"))
        
        # Add and remove capabilities
        cap_set.add_capability("auth:oauth2")
        self.assertTrue(cap_set.has_capability("auth:oauth2"))
        cap_set.remove_capability("auth:oauth2")
        self.assertFalse(cap_set.has_capability("auth:oauth2"))
        
        # Create another set for compatibility testing
        required_set = CapabilitySet(["auth:api_key", "format:json"])
        excess_set = CapabilitySet(["auth:api_key", "format:json", "integration:webhooks"])
        
        # Test compatibility
        self.assertTrue(cap_set.is_compatible_with(required_set))
        self.assertFalse(cap_set.is_compatible_with(excess_set))
        
        # Test getting missing capabilities
        missing = cap_set.get_missing_capabilities(excess_set)
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0], "integration:webhooks")

class TestCapabilityNegotiator(unittest.TestCase):
    """Test the capability negotiation process."""
    
    def setUp(self):
        self.registry = APICapabilityRegistry()
        self.negotiator = APICapabilityNegotiator(self.registry)
        
    def test_negotiation(self):
        """Test negotiating capabilities between sets."""
        # Create capability sets
        available = CapabilitySet([
            "auth:api_key", 
            "format:json", 
            "operation:get_user",
            "integration:batch"
        ])
        
        required = CapabilitySet([
            "auth:api_key",
            "format:json",
            "operation:get_user"
        ])
        
        incompatible = CapabilitySet([
            "auth:api_key",
            "auth:oauth2",
            "format:xml"
        ])
        
        # Test successful negotiation
        success, negotiated, missing = self.negotiator.negotiate_capabilities(
            available, required
        )
        
        self.assertTrue(success)
        self.assertEqual(len(missing), 0)
        self.assertEqual(len(negotiated.capability_names), 3)
        
        # Test basic negotiation with simple sets where we know the answer
        # IMPORTANT: In the implementation, the first argument represents available capabilities
        # and the second argument represents required capabilities
        available = CapabilitySet(["cap1", "cap2"])
        required = CapabilitySet(["cap3"])  # This capability does not exist in available
        
        # Since the required "cap3" is not in available, negotiation will fail
        success, negotiated, missing = self.negotiator.negotiate_capabilities(
            available, required
        )
        
        # We know cap3 should be missing - it's in required but not in available
        # get_missing_capabilities returns list(required_set.capability_names - available.capability_names)
        # which is list(["cap3"] - ["cap1", "cap2"]) = ["cap3"]
        self.assertFalse(success)
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0], "cap3")

class TestAPIGatewayCapabilities(unittest.TestCase):
    """Test API Gateway capability discovery and negotiation."""
    
    def setUp(self):
        self.gateway = APIGateway()
        
        # Create a mock plugin
        self.plugin = MagicMock(spec=APIPluginBase)
        self.plugin.__class__.__name__ = "MockPlugin"
        self.plugin.api_name = "MockAPI"
        self.plugin.api_version = "1.0"
        self.plugin.supported_auth_methods = ["api_key"]
        self.plugin.requires_rate_limiting = True
        self.plugin.supports_webhooks = True
        self.plugin.is_authenticated = True
        self.plugin.available_operations = ["get_data", "update_data"]
        
        # Mock get_capabilities
        cap_set = CapabilitySet([
            "auth:api_key",
            "format:json",
            "operation:get_data",
            "operation:update_data",
            "integration:webhooks"
        ])
        self.plugin.get_capabilities.return_value = cap_set
        self.plugin.discover_remote_capabilities.return_value = None
        
        # Register the plugin
        self.gateway.register_plugin(self.plugin)
        
    def test_discover_capabilities(self):
        """Test discovering plugin capabilities."""
        capabilities = self.gateway.discover_plugin_capabilities("MockPlugin")
        
        self.assertIsNotNone(capabilities)
        self.assertEqual(len(capabilities.capability_names), 5)
        self.assertTrue(capabilities.has_capability("auth:api_key"))
        self.assertTrue(capabilities.has_capability("integration:webhooks"))
        
    def test_negotiate_capabilities(self):
        """Test negotiating capabilities with a plugin."""
        # Create a set of required capabilities
        required = CapabilitySet([
            "auth:api_key",
            "format:json"
        ])
        
        # Test successful negotiation
        result = self.gateway.negotiate_capabilities("MockPlugin", required)
        
        self.assertTrue(result["success"])
        self.assertEqual(len(result["supported"]), 2)
        self.assertEqual(len(result["missing"]), 0)
        
        # Testing the case with capabilities that aren't provided by the plugin
        # First, get the current plugin capabilities to understand what's available
        available_caps = self.gateway.discover_plugin_capabilities("MockPlugin")
        self.assertIsNotNone(available_caps)
        
        # Create a required capability set with something not in the mock plugin
        # Based on our mock plugin setup, it doesn't have 'auth:oauth2'
        required_missing = CapabilitySet([
            "auth:oauth2"  # This capability isn't in our mock plugin's capabilities
        ])
        
        result = self.gateway.negotiate_capabilities("MockPlugin", required_missing)
        
        # The negotiation should fail since the required capability isn't available
        self.assertFalse(result["success"])
        
        # There should be exactly one missing capability
        self.assertEqual(len(result["missing"]), 1)
        
        # The missing capability should be 'auth:oauth2'
        missing_capabilities = result["missing"]
        self.assertIn("auth:oauth2", missing_capabilities)
                
        # There should be alternatives suggested
        self.assertTrue("alternatives" in result)
        
    def test_find_plugins_with_capability(self):
        """Test finding plugins with a specific capability."""
        plugins = self.gateway.find_plugins_with_capability("auth:api_key")
        
        self.assertEqual(len(plugins), 1)
        self.assertEqual(plugins[0], "MockPlugin")
        
        plugins = self.gateway.find_plugins_with_capability("auth:oauth2")
        self.assertEqual(len(plugins), 0)
        
    def test_capability_cache(self):
        """Test capability caching and clearing."""
        # Initial capability retrieval should call get_capabilities
        self.gateway.discover_plugin_capabilities("MockPlugin")
        self.plugin.get_capabilities.assert_called_once()
        
        # Second retrieval should use cache
        self.plugin.get_capabilities.reset_mock()
        self.gateway.discover_plugin_capabilities("MockPlugin")
        self.plugin.get_capabilities.assert_not_called()
        
        # Force refresh should call get_capabilities again
        self.plugin.get_capabilities.reset_mock()
        self.gateway.discover_plugin_capabilities("MockPlugin", force_refresh=True)
        self.plugin.get_capabilities.assert_called_once()
        
        # Clear cache and verify get_capabilities is called again
        self.plugin.get_capabilities.reset_mock()
        self.gateway.clear_capability_cache()
        self.gateway.discover_plugin_capabilities("MockPlugin")
        self.plugin.get_capabilities.assert_called_once()

if __name__ == "__main__":
    unittest.main()