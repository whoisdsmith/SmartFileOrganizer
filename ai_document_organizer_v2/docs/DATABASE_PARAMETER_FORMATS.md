# Database Parameter Format Support

This document describes the parameter format support in the AI Document Organizer V2 database connector system.

## Overview

The database connector system supports multiple parameter formats for query execution, providing flexibility and convenience for developers using different coding styles and database operations.

## Supported Parameter Formats

The database connector interface supports the following parameter formats:

### 1. Positional Parameters (using question mark placeholders)

Positional parameters use question marks (`?`) as placeholders in SQL queries. The parameter values are provided as a tuple or list in the same order as the placeholders.

**Using a tuple:**
```python
connector.execute_query(
    "INSERT INTO users (name, age, active) VALUES (?, ?, ?)",
    ("John Doe", 30, True)
)
```

**Using a list:**
```python
connector.execute_query(
    "SELECT * FROM users WHERE age > ? AND active = ?",
    [25, True]
)
```

### 2. Named Parameters (using colon placeholders)

Named parameters use colon-prefixed names (`:param_name`) as placeholders in SQL queries. The parameter values are provided as a dictionary with keys matching the placeholder names.

```python
connector.execute_query(
    "INSERT INTO users (name, age, active) VALUES (:name, :age, :status)",
    {"name": "Jane Smith", "age": 28, "status": True}
)
```

```python
connector.execute_query(
    "SELECT * FROM users WHERE age > :min_age AND active = :is_active",
    {"min_age": 25, "is_active": True}
)
```

## Batch Operations

Batch operations support mixed parameter formats. Each query in the batch can use a different parameter format as needed:

```python
queries = [
    "INSERT INTO products (name, price) VALUES (?, ?)",
    "UPDATE categories SET name = :name WHERE id = :id"
]

params_list = [
    ("New Product", 29.99),  # Tuple (positional params)
    {"name": "Updated Category", "id": 5}  # Dictionary (named params)
]

results = connector.execute_batch(queries, params_list)
```

## Transaction Support

All parameter formats are fully supported within transactions:

```python
with connector.transaction():
    # Using positional parameters
    connector.execute_query(
        "UPDATE accounts SET balance = balance - ? WHERE id = ?",
        (100.00, 1)
    )
    
    # Using named parameters
    connector.execute_query(
        "UPDATE accounts SET balance = balance + :amount WHERE id = :account_id",
        {"amount": 100.00, "account_id": 2}
    )
```

## Implementation Notes

- Parameter format detection is handled automatically by the connector
- The SQLite connector passes parameters directly to the underlying SQLite API, which natively supports both formats
- For other database backends, appropriate parameter format conversion may be performed
- All parameter types that the database supports (strings, numbers, booleans, dates, etc.) can be used with both formats

## Type Safety

The database connector interface uses Python's type hints to ensure type safety:

```python
def execute_query(self, query: str, 
                 params: Optional[Union[Dict[str, Any], List[Any], Tuple[Any, ...]]] = None) -> Dict[str, Any]:
```

This ensures proper IDE and static analysis tool support while providing flexibility for different parameter formats.