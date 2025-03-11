"""
Response Transformation Pipeline for the API Integration Framework.

This module provides a flexible pipeline system for transforming API responses,
allowing operations like filtering, mapping, aggregation, and enrichment.
"""

import logging
import json
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Callable, Type
import copy

logger = logging.getLogger(__name__)


class TransformationStage(ABC):
    """
    Abstract base class for a transformation stage in the pipeline.
    
    A transformation stage processes incoming data and produces output data,
    which can be passed to the next stage in the pipeline.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the transformation stage.
        
        Args:
            config: Optional configuration for the stage
        """
        self.config = config or {}
        self.name = self.config.get('name') or self.__class__.__name__
        
    @abstractmethod
    def process(self, data: Any, context: Dict[str, Any]) -> Any:
        """
        Process the input data and return transformed output.
        
        Args:
            data: Input data to transform
            context: Context dictionary with pipeline metadata
            
        Returns:
            Transformed data
        """
        pass
        
    def __str__(self) -> str:
        """String representation of the transformation stage."""
        return f"{self.name}()"
        
    def __repr__(self) -> str:
        """Detailed representation of the transformation stage."""
        return f"{self.__class__.__name__}(config={self.config})"


class FilterStage(TransformationStage):
    """
    Filter data based on a predicate function or path filter.
    
    This stage can filter dictionary/list items, exclude/include fields,
    or apply a custom filter function.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the filter stage.
        
        Args:
            config: Configuration dictionary with filter settings:
                - mode: 'include', 'exclude', 'items', or 'custom'
                - fields: List of field paths to include/exclude
                - predicate: Custom function for 'items' or 'custom' mode
                - keep_structure: Whether to preserve structure for excluded fields
        """
        super().__init__(config)
        self.mode = self.config.get('mode', 'include')
        self.fields = self.config.get('fields', [])
        self.predicate = self.config.get('predicate')
        self.keep_structure = self.config.get('keep_structure', True)
        
    def process(self, data: Any, context: Dict[str, Any]) -> Any:
        """
        Process the input data by applying filters.
        
        Args:
            data: Input data to filter
            context: Context dictionary with pipeline metadata
            
        Returns:
            Filtered data
        """
        try:
            if self.mode == 'include':
                return self._include_fields(data)
            elif self.mode == 'exclude':
                return self._exclude_fields(data)
            elif self.mode == 'items':
                return self._filter_items(data)
            elif self.mode == 'custom':
                return self._custom_filter(data, context)
            else:
                logger.warning(f"Unknown filter mode: {self.mode}, returning data unchanged")
                return data
        except Exception as e:
            logger.error(f"Error in filter stage: {e}")
            if self.config.get('fail_silently', True):
                return data
            raise
            
    def _include_fields(self, data: Any) -> Any:
        """
        Include only specified fields from the data.
        
        Args:
            data: Input data
            
        Returns:
            Data with only included fields
        """
        if not isinstance(data, dict):
            return data
            
        if not self.fields:
            return data
            
        result = {}
        
        for field_path in self.fields:
            # Support dot notation for nested fields
            parts = field_path.split('.')
            value = data
            
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    value = None
                    break
                    
            if value is not None:
                # Set the value in the result
                current = result
                for i, part in enumerate(parts):
                    if i == len(parts) - 1:
                        current[part] = value
                    else:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
                        
        return result
        
    def _exclude_fields(self, data: Any) -> Any:
        """
        Exclude specified fields from the data.
        
        Args:
            data: Input data
            
        Returns:
            Data with excluded fields removed
        """
        if not isinstance(data, dict):
            return data
            
        if not self.fields:
            return data
            
        # Make a copy to avoid modifying the original
        result = copy.deepcopy(data)
        
        for field_path in self.fields:
            # Support dot notation for nested fields
            parts = field_path.split('.')
            self._remove_field(result, parts)
                
        return result
        
    def _remove_field(self, data: Dict, parts: List[str]) -> None:
        """
        Remove a field from nested dictionaries.
        
        Args:
            data: Dictionary to modify
            parts: Path parts to the field to remove
        """
        if not isinstance(data, dict):
            return
            
        if len(parts) == 1:
            if parts[0] in data:
                del data[parts[0]]
        else:
            first, rest = parts[0], parts[1:]
            if first in data and isinstance(data[first], dict):
                self._remove_field(data[first], rest)
                
                # If the dict is now empty and we don't want to keep structure, remove it
                if not self.keep_structure and not data[first]:
                    del data[first]
                    
    def _filter_items(self, data: Any) -> Any:
        """
        Filter items in a list or dictionary using a predicate.
        
        Args:
            data: Input data
            
        Returns:
            Filtered data
        """
        if self.predicate is None:
            return data
            
        if isinstance(data, list):
            return [item for item in data if self.predicate(item)]
        elif isinstance(data, dict):
            return {k: v for k, v in data.items() if self.predicate(k, v)}
        else:
            return data
            
    def _custom_filter(self, data: Any, context: Dict[str, Any]) -> Any:
        """
        Apply a custom filter function to the data.
        
        Args:
            data: Input data
            context: Context dictionary
            
        Returns:
            Filtered data
        """
        if self.predicate is None:
            return data
            
        return self.predicate(data, context)


class MapStage(TransformationStage):
    """
    Map data by applying a transformation to each field or item.
    
    This stage can transform field values, rename fields, or apply
    custom mapping functions.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the map stage.
        
        Args:
            config: Configuration dictionary with mapping settings:
                - mode: 'rename', 'transform', 'custom', or 'template'
                - field_map: Dictionary mapping old field names to new ones
                - transformers: Dictionary mapping field names to transform functions
                - mapper: Custom mapping function
                - template: Template dictionary for restructuring data
        """
        super().__init__(config)
        self.mode = self.config.get('mode', 'transform')
        self.field_map = self.config.get('field_map', {})
        self.transformers = self.config.get('transformers', {})
        self.mapper = self.config.get('mapper')
        self.template = self.config.get('template')
        
    def process(self, data: Any, context: Dict[str, Any]) -> Any:
        """
        Process the input data by applying mapping transformations.
        
        Args:
            data: Input data to transform
            context: Context dictionary with pipeline metadata
            
        Returns:
            Transformed data
        """
        try:
            if self.mode == 'rename':
                return self._rename_fields(data)
            elif self.mode == 'transform':
                return self._transform_fields(data)
            elif self.mode == 'custom':
                return self._custom_map(data, context)
            elif self.mode == 'template':
                return self._apply_template(data)
            else:
                logger.warning(f"Unknown map mode: {self.mode}, returning data unchanged")
                return data
        except Exception as e:
            logger.error(f"Error in map stage: {e}")
            if self.config.get('fail_silently', True):
                return data
            raise
            
    def _rename_fields(self, data: Any) -> Any:
        """
        Rename fields in the data.
        
        Args:
            data: Input data
            
        Returns:
            Data with renamed fields
        """
        if not isinstance(data, dict):
            return data
            
        result = {}
        
        for key, value in data.items():
            # If the key is in the field map, use the new name
            new_key = self.field_map.get(key, key)
            
            # Recursively apply to nested dictionaries
            if isinstance(value, dict):
                result[new_key] = self._rename_fields(value)
            elif isinstance(value, list):
                result[new_key] = [
                    self._rename_fields(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                result[new_key] = value
                
        return result
        
    def _transform_fields(self, data: Any) -> Any:
        """
        Transform field values using transformer functions.
        
        Args:
            data: Input data
            
        Returns:
            Data with transformed field values
        """
        if not isinstance(data, dict):
            return data
            
        result = {}
        
        for key, value in data.items():
            # Check if we have a transformer for this field
            if key in self.transformers:
                transformer = self.transformers[key]
                result[key] = transformer(value)
            elif isinstance(value, dict):
                # Recursively apply to nested dictionaries
                result[key] = self._transform_fields(value)
            elif isinstance(value, list):
                # Apply to list items if they are dictionaries
                result[key] = [
                    self._transform_fields(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                result[key] = value
                
        return result
        
    def _custom_map(self, data: Any, context: Dict[str, Any]) -> Any:
        """
        Apply a custom mapping function to the data.
        
        Args:
            data: Input data
            context: Context dictionary
            
        Returns:
            Mapped data
        """
        if self.mapper is None:
            return data
            
        return self.mapper(data, context)
        
    def _apply_template(self, data: Any) -> Any:
        """
        Apply a template to restructure the data.
        
        Args:
            data: Input data
            
        Returns:
            Data restructured according to the template
        """
        if self.template is None:
            return data
            
        if not isinstance(data, dict):
            return data
            
        # Create a deep copy of the template
        result = copy.deepcopy(self.template)
        
        # Process each placeholder in the template
        self._fill_template(result, data)
        
        return result
        
    def _fill_template(self, template: Any, data: Dict[str, Any]) -> None:
        """
        Fill in a template with values from data.
        
        Args:
            template: Template to fill in (modified in-place)
            data: Data to use for filling
        """
        if isinstance(template, dict):
            for key, value in template.items():
                if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                    # Extract the data path
                    path = value[2:-1]
                    template[key] = self._get_path_value(data, path)
                elif isinstance(value, (dict, list)):
                    self._fill_template(value, data)
        elif isinstance(template, list):
            for i, value in enumerate(template):
                if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                    # Extract the data path
                    path = value[2:-1]
                    template[i] = self._get_path_value(data, path)
                elif isinstance(value, (dict, list)):
                    self._fill_template(value, data)
                    
    def _get_path_value(self, data: Dict[str, Any], path: str) -> Any:
        """
        Get a value from a nested dictionary using a dot-notation path.
        
        Args:
            data: Dictionary to get the value from
            path: Path to the value using dot notation
            
        Returns:
            Value at the specified path or None if not found
        """
        parts = path.split('.')
        current = data
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
                
        return current


class AggregateStage(TransformationStage):
    """
    Aggregate data from multiple sources or perform calculations.
    
    This stage can perform operations like count, sum, average, min, max,
    or apply custom aggregation functions.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the aggregate stage.
        
        Args:
            config: Configuration dictionary with aggregation settings:
                - mode: 'stats', 'group', or 'custom'
                - fields: Fields to aggregate (for 'stats' mode)
                - operations: Operations to perform on each field
                - group_by: Field to group by (for 'group' mode)
                - aggregator: Custom aggregation function
        """
        super().__init__(config)
        self.mode = self.config.get('mode', 'stats')
        self.fields = self.config.get('fields', [])
        self.operations = self.config.get('operations', {})
        self.group_by = self.config.get('group_by')
        self.aggregator = self.config.get('aggregator')
        
    def process(self, data: Any, context: Dict[str, Any]) -> Any:
        """
        Process the input data by applying aggregation operations.
        
        Args:
            data: Input data to aggregate
            context: Context dictionary with pipeline metadata
            
        Returns:
            Aggregated data
        """
        try:
            if self.mode == 'stats':
                return self._calculate_stats(data)
            elif self.mode == 'group':
                return self._group_data(data)
            elif self.mode == 'custom':
                return self._custom_aggregate(data, context)
            else:
                logger.warning(f"Unknown aggregate mode: {self.mode}, returning data unchanged")
                return data
        except Exception as e:
            logger.error(f"Error in aggregate stage: {e}")
            if self.config.get('fail_silently', True):
                return data
            raise
            
    def _calculate_stats(self, data: Any) -> Dict[str, Any]:
        """
        Calculate statistical aggregates on the data.
        
        Args:
            data: Input data
            
        Returns:
            Dictionary with calculated statistics
        """
        if not isinstance(data, (list, dict)):
            return {'value': data}
            
        result = {}
        
        # If data is a dictionary, use items for stats
        items = data.values() if isinstance(data, dict) else data
        
        # Handle case where we need stats on the whole array
        if not self.fields:
            # Perform operations on the entire array
            for op_name, op_func in self.operations.items():
                result[op_name] = op_func(items)
            return result
            
        # Handle stats on specific fields
        for field in self.fields:
            field_values = []
            
            # Extract values for the field from all items
            for item in items:
                if isinstance(item, dict) and field in item:
                    field_values.append(item[field])
                    
            # Apply operations to the field values
            field_stats = {}
            for op_name, op_func in self.operations.items():
                try:
                    field_stats[op_name] = op_func(field_values)
                except Exception as e:
                    logger.error(f"Error calculating {op_name} for field {field}: {e}")
                    field_stats[op_name] = None
                    
            result[field] = field_stats
            
        return result
        
    def _group_data(self, data: Any) -> Dict[str, Any]:
        """
        Group data by a specified field and calculate aggregates.
        
        Args:
            data: Input data
            
        Returns:
            Grouped and aggregated data
        """
        if not isinstance(data, (list, dict)) or not self.group_by:
            return data
            
        # Convert dict to list of items
        items = list(data.values()) if isinstance(data, dict) else data
        
        # Group items by the group_by field
        groups = {}
        
        for item in items:
            if not isinstance(item, dict):
                continue
                
            group_value = item.get(self.group_by)
            
            # Ensure the group value is hashable
            if isinstance(group_value, (list, dict)):
                group_value = str(group_value)
                
            # Add to existing group or create new one
            if group_value not in groups:
                groups[group_value] = []
                
            groups[group_value].append(item)
            
        # Calculate aggregates for each group
        result = {}
        
        for group_value, group_items in groups.items():
            group_result = {}
            
            for field in self.fields:
                field_values = [item.get(field) for item in group_items if field in item]
                
                # Apply operations to the field values
                field_stats = {}
                for op_name, op_func in self.operations.items():
                    try:
                        field_stats[op_name] = op_func(field_values)
                    except Exception as e:
                        logger.error(f"Error calculating {op_name} for field {field} in group {group_value}: {e}")
                        field_stats[op_name] = None
                        
                group_result[field] = field_stats
                
            # Add count of items in the group
            group_result['count'] = len(group_items)
            
            # Store the group result
            result[str(group_value)] = group_result
            
        return result
        
    def _custom_aggregate(self, data: Any, context: Dict[str, Any]) -> Any:
        """
        Apply a custom aggregation function to the data.
        
        Args:
            data: Input data
            context: Context dictionary
            
        Returns:
            Aggregated data
        """
        if self.aggregator is None:
            return data
            
        return self.aggregator(data, context)


class EnrichStage(TransformationStage):
    """
    Enrich data with additional information from external sources.
    
    This stage can add metadata, user information, or other contextual data
    to the response.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the enrich stage.
        
        Args:
            config: Configuration dictionary with enrichment settings:
                - mode: 'merge', 'metadata', or 'custom'
                - data: Static data to merge with the input
                - metadata: Metadata to add under a specified key
                - metadata_key: Key to use for metadata (default: '__metadata__')
                - enricher: Custom enrichment function
        """
        super().__init__(config)
        self.mode = self.config.get('mode', 'merge')
        self.data = self.config.get('data', {})
        self.metadata = self.config.get('metadata', {})
        self.metadata_key = self.config.get('metadata_key', '__metadata__')
        self.enricher = self.config.get('enricher')
        
    def process(self, data: Any, context: Dict[str, Any]) -> Any:
        """
        Process the input data by adding enrichment information.
        
        Args:
            data: Input data to enrich
            context: Context dictionary with pipeline metadata
            
        Returns:
            Enriched data
        """
        try:
            if self.mode == 'merge':
                return self._merge_data(data)
            elif self.mode == 'metadata':
                return self._add_metadata(data, context)
            elif self.mode == 'custom':
                return self._custom_enrich(data, context)
            else:
                logger.warning(f"Unknown enrich mode: {self.mode}, returning data unchanged")
                return data
        except Exception as e:
            logger.error(f"Error in enrich stage: {e}")
            if self.config.get('fail_silently', True):
                return data
            raise
            
    def _merge_data(self, data: Any) -> Any:
        """
        Merge static data with the input data.
        
        Args:
            data: Input data
            
        Returns:
            Merged data
        """
        if not isinstance(data, dict):
            return data
            
        if not self.data:
            return data
            
        # Make a copy to avoid modifying the original
        result = copy.deepcopy(data)
        
        # Merge in the static data
        self._deep_merge(result, self.data)
        
        return result
        
    def _deep_merge(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """
        Recursively merge source dictionary into target dictionary.
        
        Args:
            target: Target dictionary to merge into (modified in-place)
            source: Source dictionary to merge from
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                self._deep_merge(target[key], value)
            else:
                # Otherwise just overwrite
                target[key] = copy.deepcopy(value)
                
    def _add_metadata(self, data: Any, context: Dict[str, Any]) -> Any:
        """
        Add metadata to the data.
        
        Args:
            data: Input data
            context: Context dictionary
            
        Returns:
            Data with added metadata
        """
        if not isinstance(data, dict):
            # If data is not a dict, wrap it in one
            result = {'value': data}
        else:
            # Make a copy to avoid modifying the original
            result = copy.deepcopy(data)
            
        # Create metadata from static metadata and context
        metadata = copy.deepcopy(self.metadata)
        
        # Add pipeline context if configured
        if self.config.get('include_context', False):
            metadata['context'] = context
            
        # Add to the result
        result[self.metadata_key] = metadata
        
        return result
        
    def _custom_enrich(self, data: Any, context: Dict[str, Any]) -> Any:
        """
        Apply a custom enrichment function to the data.
        
        Args:
            data: Input data
            context: Context dictionary
            
        Returns:
            Enriched data
        """
        if self.enricher is None:
            return data
            
        return self.enricher(data, context)


class FormatStage(TransformationStage):
    """
    Format data into a specific structure or output format.
    
    This stage can convert data to JSON, XML, or other formats, and
    apply standardized formatting rules.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the format stage.
        
        Args:
            config: Configuration dictionary with formatting settings:
                - mode: 'json', 'xml', 'csv', or 'custom'
                - format_options: Options specific to the format
                - formatter: Custom formatting function
        """
        super().__init__(config)
        self.mode = self.config.get('mode', 'json')
        self.format_options = self.config.get('format_options', {})
        self.formatter = self.config.get('formatter')
        
    def process(self, data: Any, context: Dict[str, Any]) -> Any:
        """
        Process the input data by formatting it.
        
        Args:
            data: Input data to format
            context: Context dictionary with pipeline metadata
            
        Returns:
            Formatted data
        """
        try:
            if self.mode == 'json':
                return self._format_json(data)
            elif self.mode == 'xml':
                return self._format_xml(data)
            elif self.mode == 'csv':
                return self._format_csv(data)
            elif self.mode == 'custom':
                return self._custom_format(data, context)
            else:
                logger.warning(f"Unknown format mode: {self.mode}, returning data unchanged")
                return data
        except Exception as e:
            logger.error(f"Error in format stage: {e}")
            if self.config.get('fail_silently', True):
                return data
            raise
            
    def _format_json(self, data: Any) -> str:
        """
        Format data as JSON string.
        
        Args:
            data: Input data
            
        Returns:
            JSON string
        """
        indent = self.format_options.get('indent', 2)
        sort_keys = self.format_options.get('sort_keys', False)
        ensure_ascii = self.format_options.get('ensure_ascii', False)
        
        return json.dumps(
            data,
            indent=indent,
            sort_keys=sort_keys,
            ensure_ascii=ensure_ascii,
            default=str  # Use str for non-serializable objects
        )
        
    def _format_xml(self, data: Any) -> str:
        """
        Format data as XML string.
        
        Args:
            data: Input data
            
        Returns:
            XML string
        """
        try:
            import xml.dom.minidom as md
            from dicttoxml import dicttoxml
            
            root_name = self.format_options.get('root_name', 'root')
            item_name = self.format_options.get('item_name', 'item')
            attr_type = self.format_options.get('attr_type', False)
            
            xml_bytes = dicttoxml(
                data,
                custom_root=root_name,
                item_func=lambda x: item_name,
                attr_type=attr_type
            )
            
            # Pretty print if requested
            if self.format_options.get('pretty', True):
                dom = md.parseString(xml_bytes)
                return dom.toprettyxml(indent='  ')
            else:
                return xml_bytes.decode('utf-8')
                
        except ImportError:
            logger.error("dicttoxml package not installed, returning data unchanged")
            return str(data)
            
    def _format_csv(self, data: Any) -> str:
        """
        Format data as CSV string.
        
        Args:
            data: Input data
            
        Returns:
            CSV string
        """
        try:
            import csv
            import io
            
            delimiter = self.format_options.get('delimiter', ',')
            quotechar = self.format_options.get('quotechar', '"')
            header = self.format_options.get('header', True)
            
            # If data is a dict, convert to list
            if isinstance(data, dict):
                if all(isinstance(v, dict) for v in data.values()):
                    # Dictionary of dictionaries - convert to list of dicts
                    data = [{'id': k, **v} for k, v in data.items()]
                else:
                    # Simple key-value pairs - convert to list of dicts
                    data = [{'key': k, 'value': v} for k, v in data.items()]
                    
            # If data is not a list, wrap it
            if not isinstance(data, list):
                data = [data]
                
            # If empty list, return empty string
            if not data:
                return ""
                
            # Get field names
            if isinstance(data[0], dict):
                fieldnames = self.format_options.get('fieldnames')
                if fieldnames is None:
                    # Get all unique keys from all dictionaries
                    fieldnames = set()
                    for item in data:
                        if isinstance(item, dict):
                            fieldnames.update(item.keys())
                    fieldnames = sorted(fieldnames)
            else:
                # Data is a list of non-dict items
                fieldnames = ['value']
                data = [{'value': item} for item in data]
                
            # Write to CSV
            output = io.StringIO()
            writer = csv.DictWriter(
                output,
                fieldnames=fieldnames,
                delimiter=delimiter,
                quotechar=quotechar,
                quoting=csv.QUOTE_MINIMAL
            )
            
            if header:
                writer.writeheader()
                
            for item in data:
                if isinstance(item, dict):
                    writer.writerow({k: v for k, v in item.items() if k in fieldnames})
                    
            return output.getvalue()
            
        except ImportError:
            logger.error("csv module not available, returning data unchanged")
            return str(data)
            
    def _custom_format(self, data: Any, context: Dict[str, Any]) -> Any:
        """
        Apply a custom formatting function to the data.
        
        Args:
            data: Input data
            context: Context dictionary
            
        Returns:
            Formatted data
        """
        if self.formatter is None:
            return data
            
        return self.formatter(data, context)


class ErrorHandlingStage(TransformationStage):
    """
    Handle errors in the response or from previous stages.
    
    This stage can detect errors in responses, apply fallback values,
    and standardize error formats.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the error handling stage.
        
        Args:
            config: Configuration dictionary with error handling settings:
                - mode: 'detect', 'standardize', 'fallback', or 'custom'
                - error_paths: Paths to check for errors (for 'detect' mode)
                - error_template: Template for standardized errors
                - fallback_value: Value to use if error is detected
                - handler: Custom error handling function
        """
        super().__init__(config)
        self.mode = self.config.get('mode', 'detect')
        self.error_paths = self.config.get('error_paths', [])
        self.error_template = self.config.get('error_template', {})
        self.fallback_value = self.config.get('fallback_value')
        self.handler = self.config.get('handler')
        
    def process(self, data: Any, context: Dict[str, Any]) -> Any:
        """
        Process the input data by handling errors.
        
        Args:
            data: Input data to check for errors
            context: Context dictionary with pipeline metadata
            
        Returns:
            Data with errors handled
        """
        try:
            # Add error info from context
            has_error = context.get('error') is not None
            
            if self.mode == 'detect':
                has_error = has_error or self._detect_errors(data)
                if has_error and self.fallback_value is not None:
                    return self.fallback_value
                return data
            elif self.mode == 'standardize':
                if has_error:
                    return self._standardize_error(data, context)
                return data
            elif self.mode == 'fallback':
                if has_error:
                    return self.fallback_value
                return data
            elif self.mode == 'custom':
                return self._custom_handle(data, context)
            else:
                logger.warning(f"Unknown error handling mode: {self.mode}, returning data unchanged")
                return data
        except Exception as e:
            logger.error(f"Error in error handling stage: {e}")
            if self.config.get('fail_silently', True):
                return data
            raise
            
    def _detect_errors(self, data: Any) -> bool:
        """
        Detect errors in the data based on error paths.
        
        Args:
            data: Input data
            
        Returns:
            True if an error is detected, False otherwise
        """
        if not isinstance(data, dict):
            return False
            
        for path in self.error_paths:
            value = self._get_path_value(data, path)
            if value is not None:
                return True
                
        return False
        
    def _get_path_value(self, data: Dict[str, Any], path: str) -> Any:
        """
        Get a value from a nested dictionary using a dot-notation path.
        
        Args:
            data: Dictionary to get the value from
            path: Path to the value using dot notation
            
        Returns:
            Value at the specified path or None if not found
        """
        parts = path.split('.')
        current = data
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
                
        return current
        
    def _standardize_error(self, data: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Standardize error format using the error template.
        
        Args:
            data: Input data
            context: Context dictionary
            
        Returns:
            Standardized error response
        """
        # If no template, use a default one
        if not self.error_template:
            return {
                'error': True,
                'message': str(context.get('error', 'Unknown error')),
                'code': context.get('error_code', 500),
                'original_data': data
            }
            
        # Clone the template
        result = copy.deepcopy(self.error_template)
        
        # Fill in the template with error info from context
        if isinstance(result, dict):
            for key, value in result.items():
                if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                    # Extract the context path
                    path = value[2:-1]
                    if path == 'original_data':
                        result[key] = data
                    elif path in context:
                        result[key] = context[path]
                    elif '.' in path:
                        result[key] = self._get_path_value(context, path)
                        
        return result
        
    def _custom_handle(self, data: Any, context: Dict[str, Any]) -> Any:
        """
        Apply a custom error handling function to the data.
        
        Args:
            data: Input data
            context: Context dictionary
            
        Returns:
            Error-handled data
        """
        if self.handler is None:
            return data
            
        return self.handler(data, context)


class TransformationPipeline:
    """
    Pipeline for transforming API responses through multiple stages.
    
    This class manages the execution of a series of transformation stages
    on API response data.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the transformation pipeline.
        
        Args:
            config: Configuration dictionary for the pipeline
        """
        self.config = config or {}
        self.name = self.config.get('name', 'DefaultPipeline')
        self.description = self.config.get('description', '')
        self.stages = []  # type: List[TransformationStage]
        
        # Initialize stages from config
        stage_configs = self.config.get('stages', [])
        self._initialize_stages(stage_configs)
        
        logger.info(f"Transformation Pipeline '{self.name}' initialized with {len(self.stages)} stages")
        
    def _initialize_stages(self, stage_configs: List[Dict[str, Any]]) -> None:
        """
        Initialize transformation stages from configuration.
        
        Args:
            stage_configs: List of stage configuration dictionaries
        """
        stage_registry = {
            'filter': FilterStage,
            'map': MapStage,
            'aggregate': AggregateStage,
            'enrich': EnrichStage,
            'format': FormatStage,
            'error': ErrorHandlingStage
        }
        
        for stage_config in stage_configs:
            stage_type = stage_config.get('type')
            
            if stage_type not in stage_registry:
                logger.warning(f"Unknown stage type: {stage_type}, skipping")
                continue
                
            stage_class = stage_registry[stage_type]
            stage = stage_class(stage_config)
            self.stages.append(stage)
            
    def add_stage(self, stage: TransformationStage) -> 'TransformationPipeline':
        """
        Add a new stage to the pipeline.
        
        Args:
            stage: Transformation stage to add
            
        Returns:
            Self for method chaining
        """
        self.stages.append(stage)
        return self
        
    def remove_stage(self, index: int) -> Optional[TransformationStage]:
        """
        Remove a stage from the pipeline by index.
        
        Args:
            index: Index of the stage to remove
            
        Returns:
            Removed stage or None if index is invalid
        """
        if 0 <= index < len(self.stages):
            return self.stages.pop(index)
        return None
        
    def transform(self, data: Any, context: Optional[Dict[str, Any]] = None) -> Any:
        """
        Transform data by passing it through all stages in the pipeline.
        
        Args:
            data: Input data to transform
            context: Optional context dictionary with metadata
            
        Returns:
            Transformed data
        """
        context = context or {}
        result = data
        current_context = dict(context)
        
        # Add pipeline info to context
        current_context['pipeline'] = {
            'name': self.name,
            'stage_count': len(self.stages)
        }
        
        for i, stage in enumerate(self.stages):
            try:
                # Update context with stage info
                current_context['current_stage'] = {
                    'index': i,
                    'name': stage.name,
                    'type': stage.__class__.__name__
                }
                
                # Process the data through this stage
                result = stage.process(result, current_context)
                
                # Add transformation trace if enabled
                if self.config.get('trace_enabled', False):
                    if 'trace' not in current_context:
                        current_context['trace'] = []
                        
                    current_context['trace'].append({
                        'stage': stage.name,
                        'stage_index': i,
                        'stage_type': stage.__class__.__name__
                    })
                    
            except Exception as e:
                logger.error(f"Error in stage {i} ({stage.name}): {e}")
                
                # Handle error based on configuration
                if self.config.get('fail_fast', False):
                    # Stop processing on first error
                    current_context['error'] = str(e)
                    current_context['error_stage'] = i
                    current_context['error_stage_name'] = stage.name
                    
                    if self.config.get('throw_errors', False):
                        raise
                        
                    return self._handle_pipeline_error(result, current_context)
                else:
                    # Continue to next stage
                    current_context['error'] = str(e)
                    current_context['error_stage'] = i
                    current_context['error_stage_name'] = stage.name
                    
                    if self.config.get('log_errors', True):
                        logger.error(f"Pipeline error in stage {i} ({stage.name}): {e}")
                        
        return result
        
    def _handle_pipeline_error(self, data: Any, context: Dict[str, Any]) -> Any:
        """
        Handle an error that occurred during pipeline processing.
        
        Args:
            data: Current data
            context: Current context with error information
            
        Returns:
            Error result based on configuration
        """
        error_response = self.config.get('error_response')
        
        if error_response is None:
            # Return standard error response
            return {
                'error': True,
                'message': context.get('error', 'Unknown error'),
                'stage': context.get('error_stage'),
                'stage_name': context.get('error_stage_name')
            }
            
        if callable(error_response):
            # Call the error handler function
            return error_response(data, context)
            
        # Return configured error response
        return error_response


class TransformationManager:
    """
    Manages transformation pipelines for the API Integration Framework.
    
    This class provides a central registry for transformation pipelines
    and streamlines their configuration and application.
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the transformation manager.
        
        Args:
            config_dir: Optional directory for pipeline configuration files
        """
        # Set the configuration directory
        if config_dir is None:
            config_dir = os.path.join(
                os.path.dirname(__file__), '..', '..', 'config', 'transformations'
            )
        self.config_dir = os.path.abspath(config_dir)
        
        # Create the directory if it doesn't exist
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Initialize pipeline registry
        self.pipelines = {}  # type: Dict[str, TransformationPipeline]
        
        # Load pipelines from config files
        self._load_pipeline_configs()
        
    def _load_pipeline_configs(self) -> None:
        """
        Load pipeline configurations from JSON files in the config directory.
        """
        if not os.path.exists(self.config_dir):
            logger.warning(f"Config directory does not exist: {self.config_dir}")
            return
            
        config_files = [f for f in os.listdir(self.config_dir) if f.endswith('.json')]
        
        for file_name in config_files:
            try:
                file_path = os.path.join(self.config_dir, file_name)
                
                with open(file_path, 'r') as f:
                    config = json.load(f)
                    
                pipeline_name = config.get('name') or os.path.splitext(file_name)[0]
                self.register_pipeline(pipeline_name, config)
                
            except Exception as e:
                logger.error(f"Error loading pipeline config from {file_name}: {e}")
                
        logger.info(f"Loaded {len(self.pipelines)} transformation pipelines from config files")
        
    def register_pipeline(self, name: str, config: Dict[str, Any]) -> bool:
        """
        Register a new transformation pipeline.
        
        Args:
            name: Name for the pipeline
            config: Configuration dictionary for the pipeline
            
        Returns:
            True if registration was successful, False otherwise
        """
        try:
            # Set the name in the config
            config['name'] = name
            
            # Create and register the pipeline
            pipeline = TransformationPipeline(config)
            self.pipelines[name] = pipeline
            
            logger.info(f"Registered transformation pipeline: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering pipeline {name}: {e}")
            return False
            
    def unregister_pipeline(self, name: str) -> bool:
        """
        Unregister a transformation pipeline.
        
        Args:
            name: Name of the pipeline to unregister
            
        Returns:
            True if unregistration was successful, False otherwise
        """
        if name in self.pipelines:
            del self.pipelines[name]
            logger.info(f"Unregistered transformation pipeline: {name}")
            return True
            
        logger.warning(f"Pipeline not found: {name}")
        return False
        
    def get_pipeline(self, name: str) -> Optional[TransformationPipeline]:
        """
        Get a transformation pipeline by name.
        
        Args:
            name: Name of the pipeline to get
            
        Returns:
            TransformationPipeline instance or None if not found
        """
        return self.pipelines.get(name)
        
    def list_pipelines(self) -> List[Dict[str, Any]]:
        """
        Get a list of all registered pipelines with their metadata.
        
        Returns:
            List of pipeline information dictionaries
        """
        return [
            {
                'name': name,
                'description': pipeline.description,
                'stage_count': len(pipeline.stages),
                'stage_types': [stage.__class__.__name__ for stage in pipeline.stages]
            }
            for name, pipeline in self.pipelines.items()
        ]
        
    def transform(self, pipeline_name: str, data: Any, context: Optional[Dict[str, Any]] = None) -> Any:
        """
        Transform data using a named pipeline.
        
        Args:
            pipeline_name: Name of the pipeline to use
            data: Input data to transform
            context: Optional context dictionary with metadata
            
        Returns:
            Transformed data
        """
        pipeline = self.get_pipeline(pipeline_name)
        
        if pipeline is None:
            logger.error(f"Pipeline not found: {pipeline_name}")
            return data
            
        return pipeline.transform(data, context)
        
    def save_pipeline_config(self, name: str) -> bool:
        """
        Save a pipeline configuration to a JSON file.
        
        Args:
            name: Name of the pipeline to save
            
        Returns:
            True if save was successful, False otherwise
        """
        pipeline = self.get_pipeline(name)
        
        if pipeline is None:
            logger.error(f"Pipeline not found: {name}")
            return False
            
        try:
            file_path = os.path.join(self.config_dir, f"{name}.json")
            
            # Extract a serializable configuration
            config = {
                'name': pipeline.name,
                'description': pipeline.description,
                'stages': []
            }
            
            # Add stage configurations
            for stage in pipeline.stages:
                stage_config = stage.config.copy()
                stage_config['type'] = stage.__class__.__name__.lower().replace('stage', '')
                config['stages'].append(stage_config)
                
            # Save to file
            with open(file_path, 'w') as f:
                json.dump(config, f, indent=2)
                
            logger.info(f"Saved pipeline configuration: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving pipeline configuration: {e}")
            return False
            
    def create_default_pipelines(self) -> bool:
        """
        Create default transformation pipelines.
        
        Returns:
            True if creation was successful, False otherwise
        """
        try:
            # Standard JSON API response pipeline
            json_api_config = {
                'name': 'json_api_standard',
                'description': 'Standard transformation for JSON API responses',
                'stages': [
                    {
                        'type': 'filter',
                        'mode': 'exclude',
                        'fields': ['internal_id', 'debug_info', '_private']
                    },
                    {
                        'type': 'map',
                        'mode': 'rename',
                        'field_map': {
                            'id': 'id',
                            'type': 'type',
                            'attributes': 'attributes',
                            'relationships': 'relationships'
                        }
                    },
                    {
                        'type': 'error',
                        'mode': 'standardize',
                        'error_template': {
                            'errors': [{
                                'status': '${error_code}',
                                'title': '${error}',
                                'detail': '${error_detail}'
                            }]
                        }
                    }
                ]
            }
            
            # Simplified response pipeline
            simple_response_config = {
                'name': 'simplified_response',
                'description': 'Simplify complex API responses for easier consumption',
                'stages': [
                    {
                        'type': 'filter',
                        'mode': 'include',
                        'fields': ['id', 'name', 'description', 'created_at', 'updated_at', 'data']
                    },
                    {
                        'type': 'map',
                        'mode': 'template',
                        'template': {
                            'id': '${id}',
                            'title': '${name}',
                            'description': '${description}',
                            'metadata': {
                                'created': '${created_at}',
                                'updated': '${updated_at}'
                            },
                            'content': '${data}'
                        }
                    },
                    {
                        'type': 'enrich',
                        'mode': 'metadata',
                        'metadata': {
                            'version': '1.0',
                            'source': 'api',
                            'transformed': True
                        }
                    }
                ]
            }
            
            # Register the default pipelines
            self.register_pipeline('json_api_standard', json_api_config)
            self.register_pipeline('simplified_response', simple_response_config)
            
            # Save the configurations
            self.save_pipeline_config('json_api_standard')
            self.save_pipeline_config('simplified_response')
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating default pipelines: {e}")
            return False