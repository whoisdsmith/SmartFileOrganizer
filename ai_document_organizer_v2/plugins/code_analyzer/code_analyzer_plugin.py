"""
Code Analyzer Plugin for AI Document Organizer V2.
"""

import json
import logging
import os
import re
import time
import ast
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from ai_document_organizer_v2.core.plugin_base import PluginBase
from ai_document_organizer_v2.plugins.code_analyzer.models.code_file import CodeFile, CodeMetrics
from ai_document_organizer_v2.plugins.code_analyzer.models.dependency import Dependency


logger = logging.getLogger(__name__)


class CodeAnalyzerPlugin(PluginBase):
    """
    Code Analyzer Plugin for AI Document Organizer V2.
    
    This plugin provides:
    - Code structure analysis
    - Metrics calculation
    - Dependency tracking
    - Documentation analysis
    - Code quality assessment
    - Language detection
    """
    
    plugin_name = "code_analyzer"
    plugin_version = "1.0.0"
    plugin_description = "Advanced code analysis and metrics calculation"
    plugin_author = "AI Document Organizer Team"
    
    # Language file extensions
    LANGUAGE_EXTENSIONS = {
        "py": "Python",
        "js": "JavaScript",
        "ts": "TypeScript",
        "jsx": "JavaScript (React)",
        "tsx": "TypeScript (React)",
        "java": "Java",
        "c": "C",
        "cpp": "C++",
        "h": "C/C++ Header",
        "hpp": "C++ Header",
        "cs": "C#",
        "go": "Go",
        "rb": "Ruby",
        "php": "PHP",
        "swift": "Swift",
        "kt": "Kotlin",
        "rs": "Rust",
        "scala": "Scala",
        "m": "Objective-C",
        "mm": "Objective-C++",
        "pl": "Perl",
        "sh": "Shell",
        "html": "HTML",
        "css": "CSS",
        "scss": "SCSS",
        "less": "LESS",
        "sql": "SQL",
        "r": "R",
        "dart": "Dart",
        "lua": "Lua",
        "jl": "Julia",
        "ex": "Elixir",
        "exs": "Elixir Script",
        "elm": "Elm",
        "clj": "Clojure",
        "erl": "Erlang",
        "hrl": "Erlang Header",
        "hs": "Haskell",
        "fs": "F#",
        "fsx": "F# Script",
        "vb": "Visual Basic",
        "groovy": "Groovy",
        "ps1": "PowerShell",
        "yaml": "YAML",
        "yml": "YAML",
        "json": "JSON",
        "xml": "XML",
        "md": "Markdown",
        "rst": "reStructuredText",
        "tex": "LaTeX",
        "toml": "TOML",
        "ini": "INI",
        "cfg": "Configuration",
        "conf": "Configuration",
        "bat": "Batch",
        "cmd": "Batch",
        "dockerfile": "Dockerfile",
        "vue": "Vue",
        "svelte": "Svelte"
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the code analyzer plugin.
        
        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        
        # Configuration
        self.config = config or {}
        self.data_dir = self.config.get("data_dir", "data/code_analysis")
        
        # State
        self.code_files = {}  # file_path -> CodeFile
        self.dependencies = {}  # dependency_id -> Dependency
        
        # AI analysis settings
        self.use_ai_analysis = self.config.get("use_ai_analysis", True)
        self.ai_confidence_threshold = self.config.get("ai_confidence_threshold", 0.7)
        
        # Analysis settings
        self.min_documentation_ratio = self.config.get("min_documentation_ratio", 0.1)
        self.analyze_imports = self.config.get("analyze_imports", True)
        self.track_dependencies = self.config.get("track_dependencies", True)
        
        # Cache
        self.language_detection_cache = {}  # file_path -> language
    
    def initialize(self) -> bool:
        """
        Initialize the plugin.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        logger.info("Initializing CodeAnalyzerPlugin")
        
        # Create data directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Load code files and dependencies
        self._load_code_files()
        self._load_dependencies()
        
        return True
    
    def activate(self) -> bool:
        """
        Activate the plugin.
        
        Returns:
            True if activation was successful, False otherwise
        """
        logger.info("Activating CodeAnalyzerPlugin")
        return True
    
    def deactivate(self) -> bool:
        """
        Deactivate the plugin.
        
        Returns:
            True if deactivation was successful, False otherwise
        """
        logger.info("Deactivating CodeAnalyzerPlugin")
        return True
    
    def shutdown(self) -> bool:
        """
        Shutdown the plugin and clean up resources.
        
        Returns:
            True if shutdown was successful, False otherwise
        """
        logger.info("Shutting down CodeAnalyzerPlugin")
        
        # Save code files and dependencies
        self._save_code_files()
        self._save_dependencies()
        
        return True
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get information about the plugin.
        
        Returns:
            Dictionary with plugin information
        """
        info = super().get_info()
        info.update({
            "code_files_count": len(self.code_files),
            "dependencies_count": len(self.dependencies),
            "use_ai_analysis": self.use_ai_analysis,
            "supported_languages": len(self.LANGUAGE_EXTENSIONS)
        })
        return info
    
    def get_type(self) -> str:
        """
        Get the plugin type.
        
        Returns:
            Plugin type
        """
        return "code_analyzer"
    
    def get_capabilities(self) -> List[str]:
        """
        Get the plugin capabilities.
        
        Returns:
            List of capabilities
        """
        return [
            "code_structure_analysis",
            "metrics_calculation",
            "dependency_tracking",
            "documentation_analysis",
            "quality_assessment",
            "language_detection"
        ]
    
    def _load_code_files(self) -> None:
        """Load code files from file."""
        code_file = os.path.join(self.data_dir, 'code_files.json')
        if os.path.exists(code_file):
            try:
                with open(code_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.code_files = {}
                for code_file_data in data.get('code_files', []):
                    code_file_obj = CodeFile.from_dict(code_file_data)
                    self.code_files[code_file_obj.file_path] = code_file_obj
                
                logger.info(f"Loaded {len(self.code_files)} code files")
            except Exception as e:
                logger.error(f"Error loading code files: {e}")
                self.code_files = {}
        else:
            logger.info("No code files file found, starting with empty code files")
            self.code_files = {}
    
    def _save_code_files(self) -> None:
        """Save code files to file."""
        os.makedirs(self.data_dir, exist_ok=True)
        
        code_file = os.path.join(self.data_dir, 'code_files.json')
        try:
            data = {
                'code_files': [code_file.to_dict() for code_file in self.code_files.values()]
            }
            
            with open(code_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(self.code_files)} code files")
        except Exception as e:
            logger.error(f"Error saving code files: {e}")
    
    def _load_dependencies(self) -> None:
        """Load dependencies from file."""
        dependency_file = os.path.join(self.data_dir, 'dependencies.json')
        if os.path.exists(dependency_file):
            try:
                with open(dependency_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.dependencies = {}
                for dependency_data in data.get('dependencies', []):
                    dependency = Dependency.from_dict(dependency_data)
                    self.dependencies[dependency.dependency_id] = dependency
                
                logger.info(f"Loaded {len(self.dependencies)} dependencies")
            except Exception as e:
                logger.error(f"Error loading dependencies: {e}")
                self.dependencies = {}
        else:
            logger.info("No dependencies file found, starting with empty dependencies")
            self.dependencies = {}
    
    def _save_dependencies(self) -> None:
        """Save dependencies to file."""
        os.makedirs(self.data_dir, exist_ok=True)
        
        dependency_file = os.path.join(self.data_dir, 'dependencies.json')
        try:
            data = {
                'dependencies': [dependency.to_dict() for dependency in self.dependencies.values()]
            }
            
            with open(dependency_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(self.dependencies)} dependencies")
        except Exception as e:
            logger.error(f"Error saving dependencies: {e}")
    
    def detect_language(self, file_path: str, content: Optional[str] = None) -> str:
        """
        Detect the programming language of a file.
        
        Args:
            file_path: Path to the file
            content: Optional file content
            
        Returns:
            Detected language
        """
        # Check cache first
        if file_path in self.language_detection_cache:
            return self.language_detection_cache[file_path]
        
        # Try to determine from file extension
        _, ext = os.path.splitext(file_path)
        ext = ext.lstrip('.').lower()
        
        # Special handling for some files
        basename = os.path.basename(file_path).lower()
        if basename == 'dockerfile':
            language = 'Dockerfile'
        elif basename == 'makefile':
            language = 'Makefile'
        elif basename in ['gemfile', 'rakefile']:
            language = 'Ruby'
        elif ext in self.LANGUAGE_EXTENSIONS:
            language = self.LANGUAGE_EXTENSIONS[ext]
        else:
            # Try content-based detection if available
            if content:
                language = self._detect_language_from_content(content)
            else:
                language = 'Unknown'
        
        # Cache the result
        self.language_detection_cache[file_path] = language
        
        return language
    
    def _detect_language_from_content(self, content: str) -> str:
        """
        Detect programming language from file content.
        
        Args:
            content: File content
            
        Returns:
            Detected language
        """
        # Simple heuristics for content-based detection
        if content.startswith('#!/usr/bin/env python') or content.startswith('#!/usr/bin/python'):
            return 'Python'
        elif content.startswith('#!/usr/bin/env node') or content.startswith('#!/usr/bin/node'):
            return 'JavaScript'
        elif content.startswith('#!/bin/sh') or content.startswith('#!/bin/bash'):
            return 'Shell'
        
        # Check for language-specific patterns
        if '<?php' in content:
            return 'PHP'
        elif 'function' in content and '{' in content and '}' in content:
            if 'import React' in content or 'from "react"' in content:
                if 'interface ' in content or ': ' in content:
                    return 'TypeScript (React)'
                return 'JavaScript (React)'
            elif 'interface ' in content or 'type ' in content and ': ' in content:
                return 'TypeScript'
            else:
                return 'JavaScript'
        elif 'def ' in content and ':' in content and ('import ' in content or 'class ' in content):
            return 'Python'
        elif 'public class ' in content or 'private class ' in content:
            if '@interface' in content or '@implementation' in content:
                return 'Objective-C'
            else:
                return 'Java'
        elif '#include' in content and ('{' in content and '}' in content):
            return 'C/C++'
        
        # Default to unknown
        return 'Unknown'
    
    def analyze_file(self, 
                   file_path: str, 
                   content: Optional[str] = None,
                   use_ai: Optional[bool] = None) -> Dict[str, Any]:
        """
        Analyze a code file.
        
        Args:
            file_path: Path to the code file
            content: Optional file content (read from file if not provided)
            use_ai: Whether to use AI for analysis (default: config setting)
            
        Returns:
            Dictionary with analysis results
        """
        # Default use_ai to config setting
        if use_ai is None:
            use_ai = self.use_ai_analysis
        
        # Read content if not provided
        if content is None:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {e}")
                return {"error": f"Error reading file: {str(e)}"}
        
        # Detect language
        language = self.detect_language(file_path, content)
        
        # Create metrics
        metrics = self._calculate_metrics(content, language)
        
        # Extract classes and functions
        classes, functions = self._extract_code_structure(content, language)
        
        # Extract imports and dependencies
        imports, dependencies = self._extract_dependencies(content, language, file_path)
        
        # Calculate documentation ratio
        documentation_ratio = self._calculate_documentation_ratio(content, language)
        
        # Identify issues
        issues = self._identify_issues(content, language, metrics, documentation_ratio)
        
        # Generate summary using AI if enabled
        summary = None
        if use_ai:
            summary = self._generate_summary(content, language)
        
        # Create code file object
        code_file = CodeFile(
            file_path=file_path,
            language=language,
            metrics=metrics,
            classes=classes,
            functions=functions,
            imports=imports,
            dependencies=dependencies,
            documentation_ratio=documentation_ratio,
            issues=issues,
            summary=summary
        )
        
        # Store in code files
        self.code_files[file_path] = code_file
        
        # Save
        self._save_code_files()
        
        return code_file.to_dict()
    
    def analyze_files(self,
                    file_paths: List[str],
                    use_ai: Optional[bool] = None,
                    callback: Optional[callable] = None) -> List[Dict[str, Any]]:
        """
        Analyze multiple code files.
        
        Args:
            file_paths: List of file paths to analyze
            use_ai: Whether to use AI for analysis (default: config setting)
            callback: Optional progress callback function
            
        Returns:
            List of analysis results
        """
        results = []
        
        for i, file_path in enumerate(file_paths):
            if callback:
                callback(i, len(file_paths), file_path)
            
            result = self.analyze_file(file_path, use_ai=use_ai)
            results.append(result)
        
        return results
    
    def get_code_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Get a code file by path.
        
        Args:
            file_path: Path to the code file
            
        Returns:
            Dictionary with code file information or None if not found
        """
        if file_path not in self.code_files:
            return None
        
        return self.code_files[file_path].to_dict()
    
    def get_all_code_files(self) -> List[Dict[str, Any]]:
        """
        Get all code files.
        
        Returns:
            List of code file dictionaries
        """
        return [code_file.to_dict() for code_file in self.code_files.values()]
    
    def get_code_files_by_language(self, language: str) -> List[Dict[str, Any]]:
        """
        Get code files by language.
        
        Args:
            language: Programming language
            
        Returns:
            List of code file dictionaries
        """
        return [code_file.to_dict() for code_file in self.code_files.values()
                if code_file.language.lower() == language.lower()]
    
    def get_dependency(self, dependency_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a dependency by ID.
        
        Args:
            dependency_id: Dependency ID
            
        Returns:
            Dictionary with dependency information or None if not found
        """
        if dependency_id not in self.dependencies:
            return None
        
        return self.dependencies[dependency_id].to_dict()
    
    def get_all_dependencies(self) -> List[Dict[str, Any]]:
        """
        Get all dependencies.
        
        Returns:
            List of dependency dictionaries
        """
        return [dependency.to_dict() for dependency in self.dependencies.values()]
    
    def get_dependencies_by_language(self, language: str) -> List[Dict[str, Any]]:
        """
        Get dependencies by language.
        
        Args:
            language: Programming language
            
        Returns:
            List of dependency dictionaries
        """
        return [dependency.to_dict() for dependency in self.dependencies.values()
                if dependency.language and dependency.language.lower() == language.lower()]
    
    def get_project_metrics(self) -> Dict[str, Any]:
        """
        Get aggregated metrics for the entire project.
        
        Returns:
            Dictionary with project metrics
        """
        if not self.code_files:
            return {
                "total_files": 0,
                "total_lines": 0,
                "languages": {},
                "avg_complexity": 0.0,
                "avg_documentation_ratio": 0.0
            }
        
        # Aggregate metrics
        total_files = len(self.code_files)
        total_lines = sum(cf.metrics.lines_of_code for cf in self.code_files.values())
        total_complexity = sum(cf.metrics.complexity for cf in self.code_files.values())
        total_doc_ratio = sum(cf.documentation_ratio for cf in self.code_files.values())
        
        # Language distribution
        languages = {}
        for code_file in self.code_files.values():
            if code_file.language not in languages:
                languages[code_file.language] = 0
            languages[code_file.language] += 1
        
        # Calculate averages
        avg_complexity = total_complexity / total_files if total_files > 0 else 0.0
        avg_doc_ratio = total_doc_ratio / total_files if total_files > 0 else 0.0
        
        return {
            "total_files": total_files,
            "total_lines": total_lines,
            "languages": languages,
            "avg_complexity": avg_complexity,
            "avg_documentation_ratio": avg_doc_ratio,
            "total_dependencies": len(self.dependencies),
            "dependency_distribution": self._get_dependency_distribution()
        }
    
    def _get_dependency_distribution(self) -> Dict[str, int]:
        """
        Get distribution of dependencies by language.
        
        Returns:
            Dictionary mapping languages to dependency counts
        """
        distribution = {}
        for dependency in self.dependencies.values():
            if dependency.language:
                if dependency.language not in distribution:
                    distribution[dependency.language] = 0
                distribution[dependency.language] += 1
        
        return distribution
    
    def _calculate_metrics(self, content: str, language: str) -> CodeMetrics:
        """
        Calculate code metrics for a file.
        
        Args:
            content: File content
            language: Programming language
            
        Returns:
            CodeMetrics object
        """
        # Count lines of code, comment lines, and blank lines
        loc, comment_lines, blank_lines = self._count_lines(content, language)
        
        # Calculate cyclomatic complexity (simplified)
        complexity = self._calculate_complexity(content, language)
        
        # Create metrics
        metrics = CodeMetrics(
            lines_of_code=loc,
            comment_lines=comment_lines,
            blank_lines=blank_lines,
            complexity=complexity,
            dependency_count=0,  # To be updated later
            class_count=0,  # To be updated later
            function_count=0,  # To be updated later
            maintainability_index=self._calculate_maintainability_index(loc, complexity, comment_lines)
        )
        
        return metrics
    
    def _count_lines(self, content: str, language: str) -> Tuple[int, int, int]:
        """
        Count lines of code, comment lines, and blank lines.
        
        Args:
            content: File content
            language: Programming language
            
        Returns:
            Tuple of (lines of code, comment lines, blank lines)
        """
        lines = content.splitlines()
        loc = 0
        comment_lines = 0
        blank_lines = 0
        
        # Define comment patterns based on language
        if language in ['Python', 'Ruby', 'Shell', 'R', 'Perl']:
            single_comment = '#'
            multi_start = '"""' if language == 'Python' else None
            multi_end = '"""' if language == 'Python' else None
        elif language in ['JavaScript', 'TypeScript', 'Java', 'C', 'C++', 'C#', 'Go', 'Swift', 'Kotlin', 'PHP']:
            single_comment = '//'
            multi_start = '/*'
            multi_end = '*/'
        elif language == 'HTML' or language == 'XML':
            single_comment = None
            multi_start = '<!--'
            multi_end = '-->'
        elif language == 'SQL':
            single_comment = '--'
            multi_start = '/*'
            multi_end = '*/'
        else:
            # Default for unknown languages
            single_comment = '#'
            multi_start = None
            multi_end = None
        
        # Parse lines
        in_multi_comment = False
        for line in lines:
            stripped = line.strip()
            
            # Check for blank lines
            if not stripped:
                blank_lines += 1
                continue
            
            # Check for comments
            if in_multi_comment:
                comment_lines += 1
                if multi_end and multi_end in stripped:
                    in_multi_comment = False
                continue
            
            if multi_start and multi_start in stripped:
                comment_lines += 1
                if multi_end and multi_end in stripped[stripped.find(multi_start) + len(multi_start):]:
                    # Multi-line comment on a single line
                    pass
                else:
                    in_multi_comment = True
                continue
            
            if single_comment and stripped.startswith(single_comment):
                comment_lines += 1
                continue
            
            # If not blank or comment, it's code
            loc += 1
        
        return loc, comment_lines, blank_lines
    
    def _calculate_complexity(self, content: str, language: str) -> float:
        """
        Calculate cyclomatic complexity (simplified).
        
        Args:
            content: File content
            language: Programming language
            
        Returns:
            Complexity score
        """
        # Base complexity
        complexity = 1.0
        
        # Language-specific patterns for complexity
        if language in ['Python', 'JavaScript', 'TypeScript', 'Java', 'C#', 'PHP']:
            # Count decision points
            complexity += content.count(' if ') + content.count(' elif ') + content.count(' else ') + \
                         content.count(' for ') + content.count(' while ') + content.count(' case ') + \
                         content.count(' catch ') + content.count(' ? ') + content.count(' && ') + \
                         content.count(' || ')
        elif language in ['C', 'C++', 'Go']:
            # Count decision points
            complexity += content.count(' if ') + content.count(' else ') + \
                         content.count(' for ') + content.count(' while ') + content.count(' case ') + \
                         content.count(' catch ') + content.count(' ? ') + content.count(' && ') + \
                         content.count(' || ')
        else:
            # Generic complexity for other languages (just count common keywords)
            complexity += content.count(' if ') + content.count(' else ') + \
                         content.count(' for ') + content.count(' while ')
        
        return complexity
    
    def _calculate_maintainability_index(self, loc: int, complexity: float, comment_lines: int) -> float:
        """
        Calculate maintainability index.
        
        Args:
            loc: Lines of code
            complexity: Cyclomatic complexity
            comment_lines: Number of comment lines
            
        Returns:
            Maintainability index (0-100)
        """
        # Simplified maintainability index formula
        # Higher is better, scale is 0-100
        if loc == 0:
            return 100.0
        
        # Calculate comment ratio
        comment_ratio = comment_lines / (loc + comment_lines) if (loc + comment_lines) > 0 else 0
        
        # Use simplified formula
        mi = 100 - (0.1 * loc) - (0.2 * complexity) + (20 * comment_ratio)
        
        # Clamp to 0-100 range
        return max(0, min(100, mi))
    
    def _extract_code_structure(self, content: str, language: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Extract classes and functions from code.
        
        Args:
            content: File content
            language: Programming language
            
        Returns:
            Tuple of (classes, functions)
        """
        classes = []
        functions = []
        
        # Language-specific parsers
        if language == 'Python':
            try:
                tree = ast.parse(content)
                
                # Extract classes
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        class_info = {
                            "name": node.name,
                            "line_start": node.lineno,
                            "line_end": self._find_end_line(content, node.lineno),
                            "methods": [],
                            "attributes": []
                        }
                        
                        # Extract methods
                        for child in node.body:
                            if isinstance(child, ast.FunctionDef):
                                method_info = {
                                    "name": child.name,
                                    "line_start": child.lineno,
                                    "line_end": self._find_end_line(content, child.lineno),
                                    "is_method": True,
                                    "parent_class": node.name
                                }
                                class_info["methods"].append(method_info["name"])
                                functions.append(method_info)
                            elif isinstance(child, ast.Assign):
                                for target in child.targets:
                                    if isinstance(target, ast.Name):
                                        class_info["attributes"].append(target.id)
                        
                        classes.append(class_info)
                
                # Extract standalone functions
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and not any(
                        isinstance(parent, ast.ClassDef) for parent in [n for n in ast.walk(tree) if node in getattr(n, 'body', [])]
                    ):
                        function_info = {
                            "name": node.name,
                            "line_start": node.lineno,
                            "line_end": self._find_end_line(content, node.lineno),
                            "is_method": False,
                            "parent_class": None
                        }
                        functions.append(function_info)
            except SyntaxError:
                # Handle syntax errors in Python files
                logger.warning(f"Syntax error in Python file, using fallback extraction")
                classes, functions = self._extract_code_structure_with_regex(content, language)
        else:
            # Fallback to regex-based extraction for other languages
            classes, functions = self._extract_code_structure_with_regex(content, language)
        
        return classes, functions
    
    def _find_end_line(self, content: str, start_line: int) -> int:
        """
        Find the end line of a code block starting at start_line.
        
        Args:
            content: File content
            start_line: Starting line number
            
        Returns:
            End line number
        """
        lines = content.splitlines()
        if start_line > len(lines):
            return start_line
        
        # Simple indentation-based detection for Python-like languages
        if start_line >= len(lines):
            return start_line
        
        target_indent = len(lines[start_line - 1]) - len(lines[start_line - 1].lstrip())
        
        for i in range(start_line, len(lines)):
            line = lines[i]
            if line.strip() and len(line) - len(line.lstrip()) <= target_indent:
                return i
        
        return len(lines)
    
    def _extract_code_structure_with_regex(self, content: str, language: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Extract classes and functions using regex (fallback method).
        
        Args:
            content: File content
            language: Programming language
            
        Returns:
            Tuple of (classes, functions)
        """
        classes = []
        functions = []
        
        # Define regex patterns based on language
        if language in ['Python']:
            class_pattern = r'class\s+([A-Za-z0-9_]+)'
            function_pattern = r'def\s+([A-Za-z0-9_]+)'
        elif language in ['JavaScript', 'TypeScript']:
            class_pattern = r'class\s+([A-Za-z0-9_]+)'
            function_pattern = r'function\s+([A-Za-z0-9_]+)'
        elif language in ['Java', 'C#']:
            class_pattern = r'class\s+([A-Za-z0-9_]+)'
            function_pattern = r'(public|private|protected|internal|static)?\s+[A-Za-z0-9_<>[\]]+\s+([A-Za-z0-9_]+)\s*\('
        elif language in ['C', 'C++']:
            class_pattern = r'class\s+([A-Za-z0-9_]+)'
            function_pattern = r'[A-Za-z0-9_*<>[\]]+\s+([A-Za-z0-9_]+)\s*\('
        else:
            # Generic patterns for other languages
            class_pattern = r'class\s+([A-Za-z0-9_]+)'
            function_pattern = r'function\s+([A-Za-z0-9_]+)|def\s+([A-Za-z0-9_]+)'
        
        # Extract classes
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            class_info = {
                "name": class_name,
                "line_start": content[:match.start()].count('\n') + 1,
                "line_end": content[:match.end()].count('\n') + 1,
                "methods": [],
                "attributes": []
            }
            classes.append(class_info)
        
        # Extract functions
        for match in re.finditer(function_pattern, content):
            if hasattr(match, 'group') and match.group(1) if len(match.groups()) == 1 else (match.group(2) if len(match.groups()) > 1 else None):
                function_name = match.group(1) if len(match.groups()) == 1 else match.group(2)
                function_info = {
                    "name": function_name,
                    "line_start": content[:match.start()].count('\n') + 1,
                    "line_end": content[:match.end()].count('\n') + 1,
                    "is_method": False,  # Simplified: can't determine if it's a method using regex
                    "parent_class": None
                }
                functions.append(function_info)
        
        return classes, functions
    
    def _extract_dependencies(self, content: str, language: str, file_path: str) -> Tuple[List[str], List[str]]:
        """
        Extract imports and dependencies from code.
        
        Args:
            content: File content
            language: Programming language
            file_path: Path to the file
            
        Returns:
            Tuple of (imports, dependency_ids)
        """
        imports = []
        dependency_ids = []
        
        # Language-specific import patterns
        if language == 'Python':
            # Extract Python imports
            import_patterns = [
                r'import\s+([A-Za-z0-9_.]+)',
                r'from\s+([A-Za-z0-9_.]+)\s+import'
            ]
            
            for pattern in import_patterns:
                for match in re.finditer(pattern, content):
                    module = match.group(1)
                    imports.append(module)
                    
                    if self.track_dependencies:
                        # Add dependency
                        dependency_id = f"python_{module.split('.')[0]}"
                        dependency_ids.append(dependency_id)
                        
                        if dependency_id not in self.dependencies:
                            # Create new dependency
                            self.dependencies[dependency_id] = Dependency(
                                name=module.split('.')[0],
                                dependency_id=dependency_id,
                                dependency_type="package",
                                language="Python"
                            )
                        
                        # Add source file
                        self.dependencies[dependency_id].add_source_file(file_path)
        
        elif language in ['JavaScript', 'TypeScript', 'TypeScript (React)', 'JavaScript (React)']:
            # Extract JS/TS imports
            import_patterns = [
                r'import\s+.*\s+from\s+[\'"]([@A-Za-z0-9_/.-]+)[\'"]',
                r'require\s*\(\s*[\'"]([@A-Za-z0-9_/.-]+)[\'"]\s*\)',
                r'import\s+[\'"]([@A-Za-z0-9_/.-]+)[\'"]'
            ]
            
            for pattern in import_patterns:
                for match in re.finditer(pattern, content):
                    module = match.group(1)
                    imports.append(module)
                    
                    if self.track_dependencies:
                        # Add dependency
                        module_name = module.split('/')[0]
                        if module_name.startswith('@'):
                            # Scoped package
                            scope_parts = module.split('/')
                            if len(scope_parts) > 1:
                                module_name = f"{scope_parts[0]}/{scope_parts[1]}"
                            
                        dependency_id = f"js_{module_name.replace('@', '')}"
                        dependency_ids.append(dependency_id)
                        
                        if dependency_id not in self.dependencies:
                            # Create new dependency
                            self.dependencies[dependency_id] = Dependency(
                                name=module_name,
                                dependency_id=dependency_id,
                                dependency_type="package",
                                language="JavaScript" if language.startswith('JavaScript') else "TypeScript"
                            )
                        
                        # Add source file
                        self.dependencies[dependency_id].add_source_file(file_path)
        
        elif language in ['Java']:
            # Extract Java imports
            import_pattern = r'import\s+([A-Za-z0-9_.]+);'
            
            for match in re.finditer(import_pattern, content):
                module = match.group(1)
                imports.append(module)
                
                if self.track_dependencies:
                    # Add dependency
                    top_level = module.split('.')[0]
                    dependency_id = f"java_{top_level}"
                    dependency_ids.append(dependency_id)
                    
                    if dependency_id not in self.dependencies:
                        # Create new dependency
                        self.dependencies[dependency_id] = Dependency(
                            name=top_level,
                            dependency_id=dependency_id,
                            dependency_type="package",
                            language="Java"
                        )
                    
                    # Add source file
                    self.dependencies[dependency_id].add_source_file(file_path)
        
        # For other languages, we use simpler heuristics or leave empty
        
        return imports, dependency_ids
    
    def _calculate_documentation_ratio(self, content: str, language: str) -> float:
        """
        Calculate documentation ratio for a file.
        
        Args:
            content: File content
            language: Programming language
            
        Returns:
            Documentation ratio (0-1)
        """
        lines = content.splitlines()
        
        total_lines = len(lines)
        if total_lines == 0:
            return 0.0
        
        # Count comment lines (this is a simplification)
        _, comment_lines, _ = self._count_lines(content, language)
        
        # Calculate ratio (comments / total)
        doc_ratio = comment_lines / total_lines
        
        return doc_ratio
    
    def _identify_issues(self, 
                      content: str, 
                      language: str, 
                      metrics: CodeMetrics, 
                      documentation_ratio: float) -> List[Dict[str, Any]]:
        """
        Identify potential issues in the code.
        
        Args:
            content: File content
            language: Programming language
            metrics: Code metrics
            documentation_ratio: Documentation ratio
            
        Returns:
            List of issues
        """
        issues = []
        
        # Check for low documentation
        if documentation_ratio < self.min_documentation_ratio:
            issues.append({
                "type": "low_documentation",
                "severity": "warning",
                "message": f"Low documentation ratio ({documentation_ratio:.2f})",
                "details": f"The code has a documentation ratio of {documentation_ratio:.2f}, "
                         f"which is below the minimum threshold of {self.min_documentation_ratio}."
            })
        
        # Check for high complexity
        if metrics.complexity > 20:
            issues.append({
                "type": "high_complexity",
                "severity": "warning",
                "message": f"High complexity ({metrics.complexity:.1f})",
                "details": "The code has high cyclomatic complexity, which may make it difficult to maintain."
            })
        elif metrics.complexity > 10:
            issues.append({
                "type": "medium_complexity",
                "severity": "info",
                "message": f"Medium complexity ({metrics.complexity:.1f})",
                "details": "The code has medium cyclomatic complexity."
            })
        
        # Check for low maintainability index
        if metrics.maintainability_index < 30:
            issues.append({
                "type": "low_maintainability",
                "severity": "warning",
                "message": f"Low maintainability index ({metrics.maintainability_index:.1f})",
                "details": "The code has a low maintainability index, which may make it difficult to maintain."
            })
        elif metrics.maintainability_index < 50:
            issues.append({
                "type": "medium_maintainability",
                "severity": "info",
                "message": f"Medium maintainability index ({metrics.maintainability_index:.1f})",
                "details": "The code has a medium maintainability index."
            })
        
        # Check for large file
        if metrics.lines_of_code > 500:
            issues.append({
                "type": "large_file",
                "severity": "warning",
                "message": f"Large file ({metrics.lines_of_code} lines)",
                "details": "The file is very large, which may make it difficult to understand and maintain."
            })
        elif metrics.lines_of_code > 200:
            issues.append({
                "type": "medium_file",
                "severity": "info",
                "message": f"Medium-sized file ({metrics.lines_of_code} lines)",
                "details": "The file is medium-sized."
            })
        
        # Add language-specific checks
        if language == 'Python':
            # Check for common Python issues
            if 'except:' in content or 'except Exception:' in content:
                issues.append({
                    "type": "broad_exception",
                    "severity": "warning",
                    "message": "Broad exception handling",
                    "details": "The code uses broad exception handling, which may hide bugs."
                })
            
            if 'import *' in content:
                issues.append({
                    "type": "wildcard_import",
                    "severity": "info",
                    "message": "Wildcard import",
                    "details": "The code uses wildcard imports, which may pollute the namespace."
                })
        
        elif language in ['JavaScript', 'TypeScript']:
            # Check for common JS/TS issues
            if 'eval(' in content:
                issues.append({
                    "type": "eval_usage",
                    "severity": "warning",
                    "message": "Usage of eval()",
                    "details": "The code uses eval(), which may be a security risk."
                })
            
            if 'any' in content and language == 'TypeScript':
                issues.append({
                    "type": "any_type",
                    "severity": "info",
                    "message": "Usage of 'any' type",
                    "details": "The code uses the 'any' type, which defeats the purpose of TypeScript's type checking."
                })
        
        return issues
    
    def _generate_summary(self, content: str, language: str) -> Optional[str]:
        """
        Generate a summary of the code using AI.
        
        Args:
            content: File content
            language: Programming language
            
        Returns:
            Summary string or None if AI is not available
        """
        # This is a placeholder for AI integration
        # In a real implementation, this would:
        # 1. Truncate content if it's too long
        # 2. Send to AI service for summarization
        # 3. Return the generated summary
        
        # For now, return a basic summary
        lines = content.splitlines()
        num_lines = len(lines)
        
        if num_lines == 0:
            return "Empty file"
        
        # Look for module docstring in Python
        if language == 'Python' and num_lines > 1:
            if lines[0].startswith('"""') or lines[0].startswith("'''"):
                end_idx = 0
                for i, line in enumerate(lines[1:], 1):
                    if '"""' in line or "'''" in line:
                        end_idx = i
                        break
                
                if end_idx > 0:
                    docstring = '\n'.join(lines[:end_idx+1])
                    # Clean up docstring
                    docstring = docstring.replace('"""', '').replace("'''", '').strip()
                    if docstring:
                        return docstring
        
        # For other languages or if no docstring was found
        return f"{language} file with {num_lines} lines."