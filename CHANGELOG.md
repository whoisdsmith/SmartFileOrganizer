# Changelog

All notable changes to the AI Document Organizer project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.1] - 2025-03-11

### Dependencies and Error Resilience Improvements

#### File Parsing Module
- Added proper dependency checks for DOCX parsing with graceful fallbacks
- Improved PDF parser with PyPDF2 availability verification
- Enhanced image parsing with PIL availability checks
- Implemented structured exception handling across all parser methods
- Added appropriate logging for dependency availability issues

#### Duplicate Detection Module
- Fixed path joining issues with None values in DuplicateDetector
- Added PIL availability checks in DuplicateDetector class for image processing
- Implemented graceful fallbacks for image duplicate detection when PIL is unavailable
- Enhanced cache directory handling with proper error checks
- Ensured vector search functionality works with mock implementation for testing

#### General Improvements
- Standardized approach to dependency checking across multiple modules
- Ensured consistent error messaging for missing optional dependencies
- Maintained full interface compatibility while eliminating heavy dependencies
- Added robust error handling to prevent crashes from missing libraries
- Verified initialization and basic functionality works even with missing dependencies

## [1.0.0] - 2025-03-10

### Features (from git history)

#### Duplicate Detection (commit afcce8c)
- Added comprehensive duplicate detection using multiple strategies:
  - Perceptual image hashing for image-based similarity
  - Content-based text similarity analysis
  - OCR-based PDF comparison
  - Binary file hash comparison
- Integrated vector search for semantic similarity detection
- Implemented configurable detection thresholds and caching
- Enhanced file type detection and grouping
- Added robust error handling and logging for duplicate detection

#### OCR Support (commit 25f8c71)
- Integrated OCR capabilities for PDF and image files
- Added OCR configuration with comprehensive settings
- Updated FileParser and FileAnalyzer with OCR text extraction
- Implemented OCR caching and confidence threshold mechanisms
- Added multi-language OCR support and preprocessing options

#### PDF Support (commit e79a298)
- Added PyPDF2 integration for PDF file parsing
- Implemented PDF text extraction and metadata parsing
- Extended file type detection for PDF documents
- Improved content parsing across multiple file formats

#### Search Engine Enhancement (commit 557d4be)
- Implemented hybrid semantic and keyword search
- Added vector-based document similarity
- Enhanced search indexing and query processing

#### File Organization (commit e86d547)
- Enhanced file organization with advanced rules
- Added image analysis capabilities
- Improved categorization and metadata extraction

### Initial Release
- Core AI document analysis engine
- Multi-file type support (PDF, JSON, XML)
- Advanced machine learning organization algorithms
- Multi-model AI integration (Gemini, OpenAI)
- Comprehensive document processing framework with intelligent duplicate detection