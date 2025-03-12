# API Capability Negotiation System

## Overview

The API Capability Negotiation System is a crucial component of the AI Document Organizer V2's API Integration Framework. It enables dynamic discovery and automatic negotiation of features between the application and various API integrations, allowing the application to adapt to different API versions and feature sets at runtime.

## Key Components

### 1. API Capability

The `APICapability` class represents a single API capability with properties and requirements:

```python
APICapability(
    name="auth:oauth2",
    category=CapabilityCategory.AUTHENTICATION,
    description="OAuth 2.0 Authentication",
    version_introduced="1.0",
    version_deprecated=None,
    required_capabilities=["auth:base"],
    properties={"flow_types": ["authorization_code", "client_credentials"]}
)
```

Key attributes:
- **name**: Unique identifier for the capability (format: "category:feature")
- **category**: Group the capability belongs to (authentication, data_format, etc.)
- **description**: Human-readable description
- **version_introduced/deprecated**: Version tracking for availability
- **required_capabilities**: Dependencies on other capabilities
- **properties**: Additional metadata describing the capability

### 2. Capability Set

The `CapabilitySet` class represents a collection of capabilities, either:
- Capabilities supported by an API plugin
- Capabilities required by a client component

```python
# API capabilities
api_capabilities = CapabilitySet([
    "auth:api_key", 
    "format:json", 
    "integration:batch"
])

# Client requirements
required_capabilities = CapabilitySet([
    "auth:api_key", 
    "format:json"
])
```

Key methods:
- **add_capability()**: Add a capability to the set
- **remove_capability()**: Remove a capability from the set
- **has_capability()**: Check if a specific capability exists
- **get_missing_capabilities()**: Get capabilities missing from this set compared to another
- **is_compatible_with()**: Check if this set contains all capabilities in another set

### 3. Capability Registry

The `APICapabilityRegistry` manages a collection of API capabilities and provides lookup functions:

```python
registry = APICapabilityRegistry()
cap = registry.get_capability("auth:oauth2")
auth_caps = registry.get_capabilities_by_category(CapabilityCategory.AUTHENTICATION)
```

Key features:
- Pre-registered standard capabilities for common API features
- Capability lookup by name or category
- Version-based capability filtering

### 4. Capability Negotiator

The `APICapabilityNegotiator` handles the runtime negotiation process between available and required capabilities:

```python
negotiator = APICapabilityNegotiator()
success, negotiated, missing = negotiator.negotiate_capabilities(available_caps, required_caps)
```

## Capability Negotiation Process

The negotiation process involves several steps:

1. **Discovery**: The system queries the API plugin to discover its supported capabilities
2. **Requirement Definition**: Client components define their required capabilities
3. **Negotiation**: The negotiator compares available vs. required capabilities
4. **Result Processing**: The system adapts based on negotiation results

### Negotiation Logic

The `negotiate_capabilities` method implements the core negotiation logic:

```python
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
    missing = available_capabilities.get_missing_capabilities(required_capabilities)
    
    # Create a set with the intersection of available and required capabilities
    negotiated_names = required_capabilities.capability_names.intersection(available_capabilities.capability_names)
    negotiated = CapabilitySet(list(negotiated_names))
    
    return False, negotiated, missing
```

The result of negotiation is a tuple containing:
1. Success indicator (boolean)
2. Negotiated capabilities (intersection of available and required)
3. List of missing capabilities

## API Gateway Integration

The API Gateway exposes the `negotiate_capabilities` method that provides a user-friendly interface to the negotiation system:

```python
result = api_gateway.negotiate_capabilities("WeatherAPI", required_capabilities)

if result["success"]:
    # All capabilities are supported
    print(f"Supported capabilities: {result['supported']}")
else:
    # Some capabilities are missing
    print(f"Missing capabilities: {result['missing']}")
    print(f"Alternative capabilities: {result['alternatives']}")
```

The gateway method returns a dictionary with:
- **success**: Boolean indicating if all required capabilities are available
- **supported**: List of supported capability names
- **missing**: List of missing capability names
- **alternatives**: Dictionary mapping missing capabilities to alternative options
- **plugin_capabilities**: Complete list of all plugin capabilities

## Usage Examples

### 1. Basic Capability Check

```python
# Define required capabilities
required_caps = CapabilitySet(["auth:api_key", "format:json"])

# Negotiate with plugin
result = api_gateway.negotiate_capabilities("WeatherAPI", required_caps)

if result["success"]:
    # All required capabilities are supported
    weather_api = api_gateway.get_plugin("WeatherAPI")
    temperature = weather_api.get_temperature(location="New York")
else:
    # Handle missing capabilities
    logger.error(f"Weather API missing required capabilities: {result['missing']}")
```

### 2. Adaptive Feature Usage

```python
# Define optional capabilities
required_caps = CapabilitySet(["auth:api_key", "format:json"])
optional_caps = CapabilitySet(["integration:batch"])

# Negotiate with plugin
result = api_gateway.negotiate_capabilities("WeatherAPI", required_caps)

if result["success"]:
    weather_api = api_gateway.get_plugin("WeatherAPI")
    
    # Check if batch processing is supported
    if "integration:batch" in result["supported"]:
        # Use batch processing
        batch_result = weather_api.batch_process([
            {"operation": "get_temperature", "location": "New York"},
            {"operation": "get_forecast", "location": "Boston"}
        ])
    else:
        # Fall back to individual requests
        temp_ny = weather_api.get_temperature(location="New York")
        forecast_boston = weather_api.get_forecast(location="Boston")
```

### 3. Alternative Capability Selection

```python
# Prefer OAuth but accept API key
required_caps = CapabilitySet(["auth:oauth2", "format:json"])

# Negotiate with plugin
result = api_gateway.negotiate_capabilities("WeatherAPI", required_caps)

if not result["success"] and "auth:oauth2" in result["missing"]:
    # Check for alternative authentication methods
    alternatives = result["alternatives"].get("auth:oauth2", [])
    
    if "auth:api_key" in alternatives:
        # Use API key authentication instead
        print("Using API key authentication as fallback")
        alt_caps = CapabilitySet(["auth:api_key", "format:json"])
        alt_result = api_gateway.negotiate_capabilities("WeatherAPI", alt_caps)
        
        if alt_result["success"]:
            # Proceed with API key authentication
            weather_api = api_gateway.get_plugin("WeatherAPI")
            temperature = weather_api.get_temperature(location="New York")
```

## Benefits and Best Practices

### Benefits

1. **Runtime Adaptability**: Applications can adapt to different API versions and capabilities at runtime
2. **Graceful Degradation**: Allows for fallback strategies when preferred capabilities are unavailable
3. **Feature Discovery**: Enables exploration of available API features
4. **Consistent Interface**: Provides a unified interface for capability negotiation across different APIs
5. **Error Prevention**: Prevents runtime errors from using unavailable features

### Best Practices

1. **Essential vs. Optional**: Distinguish between essential and optional capabilities
2. **Alternative Paths**: Implement alternative code paths for different capability sets
3. **Capability Naming**: Use a consistent naming convention (category:feature)
4. **Documentation**: Document required capabilities for each component
5. **Version Handling**: Include version information in capability definitions

## Conclusion

The API Capability Negotiation System provides a robust framework for dynamically discovering and adapting to API features. By implementing this system, the AI Document Organizer V2 gains flexibility in working with diverse external APIs, ensuring compatibility while leveraging the full range of available features.