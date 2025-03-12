"""
Code file models for the Code Analyzer Plugin.
"""

import time
from typing import Any, Dict, List, Optional, Set


class CodeMetrics:
    """
    Represents metrics for a code file.
    """
    
    def __init__(self,
                lines_of_code: int = 0,
                comment_lines: int = 0,
                blank_lines: int = 0,
                complexity: float = 0.0,
                dependency_count: int = 0,
                class_count: int = 0,
                function_count: int = 0,
                maintainability_index: float = 0.0):
        """
        Initialize code metrics.
        
        Args:
            lines_of_code: Total lines of code
            comment_lines: Number of comment lines
            blank_lines: Number of blank lines
            complexity: Cyclomatic complexity
            dependency_count: Number of dependencies
            class_count: Number of classes defined
            function_count: Number of functions defined
            maintainability_index: Maintainability index (0-100)
        """
        self.lines_of_code = lines_of_code
        self.comment_lines = comment_lines
        self.blank_lines = blank_lines
        self.complexity = complexity
        self.dependency_count = dependency_count
        self.class_count = class_count
        self.function_count = function_count
        self.maintainability_index = maintainability_index
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.
        
        Returns:
            Dictionary representation of code metrics
        """
        return {
            "lines_of_code": self.lines_of_code,
            "comment_lines": self.comment_lines,
            "blank_lines": self.blank_lines,
            "complexity": self.complexity,
            "dependency_count": self.dependency_count,
            "class_count": self.class_count,
            "function_count": self.function_count,
            "maintainability_index": self.maintainability_index
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CodeMetrics':
        """
        Create from dictionary.
        
        Args:
            data: Dictionary with code metrics data
            
        Returns:
            CodeMetrics instance
        """
        return cls(
            lines_of_code=data.get("lines_of_code", 0),
            comment_lines=data.get("comment_lines", 0),
            blank_lines=data.get("blank_lines", 0),
            complexity=data.get("complexity", 0.0),
            dependency_count=data.get("dependency_count", 0),
            class_count=data.get("class_count", 0),
            function_count=data.get("function_count", 0),
            maintainability_index=data.get("maintainability_index", 0.0)
        )


class CodeFile:
    """
    Represents a code file with analysis results.
    """
    
    def __init__(self,
                file_path: str,
                language: str,
                code_file_id: Optional[str] = None,
                metrics: Optional[CodeMetrics] = None,
                classes: Optional[List[Dict[str, Any]]] = None,
                functions: Optional[List[Dict[str, Any]]] = None,
                imports: Optional[List[str]] = None,
                dependencies: Optional[List[str]] = None,
                documentation_ratio: float = 0.0,
                issues: Optional[List[Dict[str, Any]]] = None,
                summary: Optional[str] = None,
                analyzed_at: Optional[float] = None):
        """
        Initialize a code file.
        
        Args:
            file_path: Path to the code file
            language: Programming language
            code_file_id: Optional ID for the code file (defaults to file path)
            metrics: Optional code metrics
            classes: Optional list of classes defined in the file
            functions: Optional list of functions defined in the file
            imports: Optional list of imports
            dependencies: Optional list of dependency IDs
            documentation_ratio: Documentation ratio (0-1)
            issues: Optional list of issues found
            summary: Optional AI-generated summary
            analyzed_at: Optional timestamp when analysis was performed
        """
        self.file_path = file_path
        self.language = language
        self.code_file_id = code_file_id or file_path
        self.metrics = metrics or CodeMetrics()
        self.classes = classes or []
        self.functions = functions or []
        self.imports = imports or []
        self.dependencies = dependencies or []
        self.documentation_ratio = documentation_ratio
        self.issues = issues or []
        self.summary = summary
        self.analyzed_at = analyzed_at or time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.
        
        Returns:
            Dictionary representation of code file
        """
        return {
            "file_path": self.file_path,
            "language": self.language,
            "code_file_id": self.code_file_id,
            "metrics": self.metrics.to_dict(),
            "classes": self.classes,
            "functions": self.functions,
            "imports": self.imports,
            "dependencies": self.dependencies,
            "documentation_ratio": self.documentation_ratio,
            "issues": self.issues,
            "summary": self.summary,
            "analyzed_at": self.analyzed_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CodeFile':
        """
        Create from dictionary.
        
        Args:
            data: Dictionary with code file data
            
        Returns:
            CodeFile instance
        """
        metrics = CodeMetrics.from_dict(data.get("metrics", {}))
        
        return cls(
            file_path=data.get("file_path", ""),
            language=data.get("language", "unknown"),
            code_file_id=data.get("code_file_id"),
            metrics=metrics,
            classes=data.get("classes", []),
            functions=data.get("functions", []),
            imports=data.get("imports", []),
            dependencies=data.get("dependencies", []),
            documentation_ratio=data.get("documentation_ratio", 0.0),
            issues=data.get("issues", []),
            summary=data.get("summary"),
            analyzed_at=data.get("analyzed_at", time.time())
        )
    
    def add_class(self, class_info: Dict[str, Any]) -> None:
        """
        Add a class to the code file.
        
        Args:
            class_info: Class information dictionary
        """
        self.classes.append(class_info)
        self.metrics.class_count += 1
    
    def add_function(self, function_info: Dict[str, Any]) -> None:
        """
        Add a function to the code file.
        
        Args:
            function_info: Function information dictionary
        """
        self.functions.append(function_info)
        self.metrics.function_count += 1
    
    def add_import(self, import_name: str) -> None:
        """
        Add an import to the code file.
        
        Args:
            import_name: Import name
        """
        if import_name not in self.imports:
            self.imports.append(import_name)
    
    def add_dependency(self, dependency_id: str) -> None:
        """
        Add a dependency to the code file.
        
        Args:
            dependency_id: Dependency ID
        """
        if dependency_id not in self.dependencies:
            self.dependencies.append(dependency_id)
            self.metrics.dependency_count += 1
    
    def add_issue(self, issue: Dict[str, Any]) -> None:
        """
        Add an issue to the code file.
        
        Args:
            issue: Issue information dictionary
        """
        self.issues.append(issue)
    
    def update_metrics(self, metrics: CodeMetrics) -> None:
        """
        Update code metrics.
        
        Args:
            metrics: New code metrics
        """
        self.metrics = metrics