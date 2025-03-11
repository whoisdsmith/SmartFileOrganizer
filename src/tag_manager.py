import os
import json
import sqlite3
import logging
from collections import defaultdict

logger = logging.getLogger("AIDocumentOrganizer")


class TagManager:
    """
    Class for managing document tags
    """

    def __init__(self, db_path=None):
        """
        Initialize the tag manager

        Args:
            db_path: Path to the SQLite database file (default: tags.db in user's home directory)
        """
        if db_path is None:
            home_dir = os.path.expanduser("~")
            app_dir = os.path.join(home_dir, ".ai_document_organizer")
            os.makedirs(app_dir, exist_ok=True)
            db_path = os.path.join(app_dir, "tags.db")

        self.db_path = db_path
        self._initialize_database()

    def _initialize_database(self):
        """
        Initialize the SQLite database schema
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Create tags table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE,
                    category TEXT,
                    color TEXT,
                    description TEXT,
                    parent_id INTEGER,
                    created_time REAL,
                    FOREIGN KEY (parent_id) REFERENCES tags (id) ON DELETE SET NULL
                )
            ''')

            # Create file_tags table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS file_tags (
                    file_path TEXT,
                    tag_id INTEGER,
                    added_time REAL,
                    confidence REAL,
                    is_ai_suggested BOOLEAN,
                    PRIMARY KEY (file_path, tag_id),
                    FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
                )
            ''')

            # Create indexes
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_tags_name ON tags (name)')
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_tags_category ON tags (category)')
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_file_tags_file_path ON file_tags (file_path)')
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_file_tags_tag_id ON file_tags (tag_id)')

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error initializing tag database: {str(e)}")
            raise

    def create_tag(self, name, category=None, color=None, description=None, parent_name=None):
        """
        Create a new tag

        Args:
            name: Tag name
            category: Tag category
            color: Tag color (hex code)
            description: Tag description
            parent_name: Parent tag name for hierarchical tags

        Returns:
            Tag ID if successful, None otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Check if tag already exists
            cursor.execute('SELECT id FROM tags WHERE name = ?', (name,))
            result = cursor.fetchone()

            if result:
                logger.warning(f"Tag '{name}' already exists")
                conn.close()
                return result[0]

            # Get parent ID if specified
            parent_id = None
            if parent_name:
                cursor.execute(
                    'SELECT id FROM tags WHERE name = ?', (parent_name,))
                parent_result = cursor.fetchone()

                if parent_result:
                    parent_id = parent_result[0]
                else:
                    logger.warning(f"Parent tag '{parent_name}' not found")

            # Insert new tag
            import time
            cursor.execute('''
                INSERT INTO tags (name, category, color, description, parent_id, created_time)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, category, color, description, parent_id, time.time()))

            tag_id = cursor.lastrowid
            conn.commit()
            conn.close()

            return tag_id
        except Exception as e:
            logger.error(f"Error creating tag '{name}': {str(e)}")
            return None

    def update_tag(self, tag_id, name=None, category=None, color=None, description=None, parent_name=None):
        """
        Update an existing tag

        Args:
            tag_id: Tag ID
            name: New tag name
            category: New tag category
            color: New tag color
            description: New tag description
            parent_name: New parent tag name

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Check if tag exists
            cursor.execute('SELECT id FROM tags WHERE id = ?', (tag_id,))
            if not cursor.fetchone():
                logger.warning(f"Tag with ID {tag_id} not found")
                conn.close()
                return False

            # Get parent ID if specified
            parent_id = None
            if parent_name:
                cursor.execute(
                    'SELECT id FROM tags WHERE name = ?', (parent_name,))
                parent_result = cursor.fetchone()

                if parent_result:
                    parent_id = parent_result[0]
                else:
                    logger.warning(f"Parent tag '{parent_name}' not found")

            # Build update query
            update_fields = []
            params = []

            if name is not None:
                update_fields.append('name = ?')
                params.append(name)

            if category is not None:
                update_fields.append('category = ?')
                params.append(category)

            if color is not None:
                update_fields.append('color = ?')
                params.append(color)

            if description is not None:
                update_fields.append('description = ?')
                params.append(description)

            if parent_name is not None:
                update_fields.append('parent_id = ?')
                params.append(parent_id)

            if not update_fields:
                logger.warning("No fields to update")
                conn.close()
                return False

            # Execute update
            query = f"UPDATE tags SET {', '.join(update_fields)} WHERE id = ?"
            params.append(tag_id)

            cursor.execute(query, params)
            conn.commit()
            conn.close()

            return True
        except Exception as e:
            logger.error(f"Error updating tag {tag_id}: {str(e)}")
            return False

    def delete_tag(self, tag_id):
        """
        Delete a tag

        Args:
            tag_id: Tag ID

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Check if tag exists
            cursor.execute('SELECT id FROM tags WHERE id = ?', (tag_id,))
            if not cursor.fetchone():
                logger.warning(f"Tag with ID {tag_id} not found")
                conn.close()
                return False

            # Delete tag
            cursor.execute('DELETE FROM tags WHERE id = ?', (tag_id,))

            # Delete file-tag associations
            cursor.execute('DELETE FROM file_tags WHERE tag_id = ?', (tag_id,))

            conn.commit()
            conn.close()

            return True
        except Exception as e:
            logger.error(f"Error deleting tag {tag_id}: {str(e)}")
            return False

    def get_all_tags(self):
        """
        Get all tags

        Returns:
            List of tag dictionaries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT t.id, t.name, t.category, t.color, t.description, t.parent_id, p.name as parent_name,
                       (SELECT COUNT(*) FROM file_tags WHERE tag_id = t.id) as file_count
                FROM tags t
                LEFT JOIN tags p ON t.parent_id = p.id
                ORDER BY t.category, t.name
            ''')

            tags = [dict(row) for row in cursor.fetchall()]
            conn.close()

            return tags
        except Exception as e:
            logger.error(f"Error getting tags: {str(e)}")
            return []

    def get_tag_by_id(self, tag_id):
        """
        Get tag by ID

        Args:
            tag_id: Tag ID

        Returns:
            Tag dictionary if found, None otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT t.id, t.name, t.category, t.color, t.description, t.parent_id, p.name as parent_name,
                       (SELECT COUNT(*) FROM file_tags WHERE tag_id = t.id) as file_count
                FROM tags t
                LEFT JOIN tags p ON t.parent_id = p.id
                WHERE t.id = ?
            ''', (tag_id,))

            result = cursor.fetchone()
            conn.close()

            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error getting tag {tag_id}: {str(e)}")
            return None

    def get_tag_by_name(self, tag_name):
        """
        Get tag by name

        Args:
            tag_name: Tag name

        Returns:
            Tag dictionary if found, None otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT t.id, t.name, t.category, t.color, t.description, t.parent_id, p.name as parent_name,
                       (SELECT COUNT(*) FROM file_tags WHERE tag_id = t.id) as file_count
                FROM tags t
                LEFT JOIN tags p ON t.parent_id = p.id
                WHERE t.name = ?
            ''', (tag_name,))

            result = cursor.fetchone()
            conn.close()

            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error getting tag '{tag_name}': {str(e)}")
            return None

    def get_tags_by_category(self, category):
        """
        Get tags by category

        Args:
            category: Tag category

        Returns:
            List of tag dictionaries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT t.id, t.name, t.category, t.color, t.description, t.parent_id, p.name as parent_name,
                       (SELECT COUNT(*) FROM file_tags WHERE tag_id = t.id) as file_count
                FROM tags t
                LEFT JOIN tags p ON t.parent_id = p.id
                WHERE t.category = ?
                ORDER BY t.name
            ''', (category,))

            tags = [dict(row) for row in cursor.fetchall()]
            conn.close()

            return tags
        except Exception as e:
            logger.error(
                f"Error getting tags for category '{category}': {str(e)}")
            return []

    def get_tag_hierarchy(self):
        """
        Get tag hierarchy

        Returns:
            Dictionary with tag hierarchy
        """
        try:
            tags = self.get_all_tags()

            # Build hierarchy
            hierarchy = defaultdict(list)
            root_tags = []

            for tag in tags:
                if tag['parent_id'] is None:
                    root_tags.append(tag)
                else:
                    hierarchy[tag['parent_id']].append(tag)

            # Recursive function to build tree
            def build_tree(tag):
                tag_id = tag['id']
                children = hierarchy.get(tag_id, [])

                result = tag.copy()
                if children:
                    result['children'] = [build_tree(
                        child) for child in children]

                return result

            return [build_tree(tag) for tag in root_tags]
        except Exception as e:
            logger.error(f"Error getting tag hierarchy: {str(e)}")
            return []

    def add_tag_to_file(self, file_path, tag_name, confidence=1.0, is_ai_suggested=False):
        """
        Add a tag to a file

        Args:
            file_path: Path to the file
            tag_name: Tag name
            confidence: Confidence score (0.0 to 1.0)
            is_ai_suggested: Whether the tag was suggested by AI

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get tag ID
            cursor.execute('SELECT id FROM tags WHERE name = ?', (tag_name,))
            result = cursor.fetchone()

            if not result:
                # Create tag if it doesn't exist
                tag_id = self.create_tag(tag_name)
                if not tag_id:
                    conn.close()
                    return False
            else:
                tag_id = result[0]

            # Check if file-tag association already exists
            cursor.execute(
                'SELECT 1 FROM file_tags WHERE file_path = ? AND tag_id = ?', (file_path, tag_id))
            if cursor.fetchone():
                # Update existing association
                cursor.execute('''
                    UPDATE file_tags SET confidence = ?, is_ai_suggested = ?, added_time = ?
                    WHERE file_path = ? AND tag_id = ?
                ''', (confidence, is_ai_suggested, time.time(), file_path, tag_id))
            else:
                # Add new association
                cursor.execute('''
                    INSERT INTO file_tags (file_path, tag_id, added_time, confidence, is_ai_suggested)
                    VALUES (?, ?, ?, ?, ?)
                ''', (file_path, tag_id, time.time(), confidence, is_ai_suggested))

            conn.commit()
            conn.close()

            return True
        except Exception as e:
            logger.error(
                f"Error adding tag '{tag_name}' to file '{file_path}': {str(e)}")
            return False

    def remove_tag_from_file(self, file_path, tag_name):
        """
        Remove a tag from a file

        Args:
            file_path: Path to the file
            tag_name: Tag name

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get tag ID
            cursor.execute('SELECT id FROM tags WHERE name = ?', (tag_name,))
            result = cursor.fetchone()

            if not result:
                logger.warning(f"Tag '{tag_name}' not found")
                conn.close()
                return False

            tag_id = result[0]

            # Remove file-tag association
            cursor.execute(
                'DELETE FROM file_tags WHERE file_path = ? AND tag_id = ?', (file_path, tag_id))

            conn.commit()
            conn.close()

            return True
        except Exception as e:
            logger.error(
                f"Error removing tag '{tag_name}' from file '{file_path}': {str(e)}")
            return False

    def get_file_tags(self, file_path):
        """
        Get tags for a file

        Args:
            file_path: Path to the file

        Returns:
            List of tag dictionaries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT t.id, t.name, t.category, t.color, t.description, ft.confidence, ft.is_ai_suggested
                FROM file_tags ft
                JOIN tags t ON ft.tag_id = t.id
                WHERE ft.file_path = ?
                ORDER BY t.category, t.name
            ''', (file_path,))

            tags = [dict(row) for row in cursor.fetchall()]
            conn.close()

            return tags
        except Exception as e:
            logger.error(
                f"Error getting tags for file '{file_path}': {str(e)}")
            return []

    def get_files_by_tag(self, tag_name):
        """
        Get files with a specific tag

        Args:
            tag_name: Tag name

        Returns:
            List of file paths
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get tag ID
            cursor.execute('SELECT id FROM tags WHERE name = ?', (tag_name,))
            result = cursor.fetchone()

            if not result:
                logger.warning(f"Tag '{tag_name}' not found")
                conn.close()
                return []

            tag_id = result[0]

            # Get files with tag
            cursor.execute(
                'SELECT file_path FROM file_tags WHERE tag_id = ?', (tag_id,))
            files = [row[0] for row in cursor.fetchall()]

            conn.close()

            return files
        except Exception as e:
            logger.error(f"Error getting files for tag '{tag_name}': {str(e)}")
            return []

    def get_tag_suggestions(self, file_info):
        """
        Get tag suggestions for a file based on its content and metadata

        Args:
            file_info: File information dictionary

        Returns:
            List of tag dictionaries with confidence scores
        """
        # This is a placeholder for AI-based tag suggestion
        # In a real implementation, this would use AI to analyze file content and metadata

        suggestions = []

        # Extract potential tags from content
        if 'content' in file_info and file_info['content']:
            # Simple keyword extraction (placeholder)
            content = file_info['content'].lower()

            # Get all existing tags
            all_tags = self.get_all_tags()
            tag_names = [tag['name'].lower() for tag in all_tags]

            # Check if any existing tag appears in the content
            for tag in all_tags:
                tag_name = tag['name'].lower()
                if tag_name in content:
                    # Calculate a simple confidence score based on frequency
                    count = content.count(tag_name)
                    # Max 0.9 for keyword matches
                    confidence = min(0.5 + (count * 0.1), 0.9)

                    suggestions.append({
                        'id': tag['id'],
                        'name': tag['name'],
                        'confidence': confidence,
                        'reason': f"Keyword appears {count} times in content"
                    })

        # Extract potential tags from metadata
        if 'metadata' in file_info and file_info['metadata']:
            for key, value in file_info['metadata'].items():
                if value and isinstance(value, str):
                    # Check if any metadata value could be a tag
                    value = value.lower()
                    if len(value) > 2 and len(value) < 20:  # Reasonable tag length
                        suggestions.append({
                            'name': value.title(),  # Capitalize for tag name
                            'confidence': 0.7,
                            'reason': f"Extracted from metadata field '{key}'"
                        })

        # Extract potential tags from filename
        if 'path' in file_info:
            filename = os.path.basename(file_info['path'])
            name, _ = os.path.splitext(filename)

            # Split filename by common separators
            parts = re.split(r'[-_\s]', name)
            for part in parts:
                if len(part) > 2 and len(part) < 20:  # Reasonable tag length
                    suggestions.append({
                        'name': part.title(),  # Capitalize for tag name
                        'confidence': 0.6,
                        'reason': "Extracted from filename"
                    })

        # Remove duplicates and sort by confidence
        unique_suggestions = {}
        for suggestion in suggestions:
            name = suggestion['name'].lower()
            if name not in unique_suggestions or suggestion['confidence'] > unique_suggestions[name]['confidence']:
                unique_suggestions[name] = suggestion

        return sorted(unique_suggestions.values(), key=lambda x: x['confidence'], reverse=True)

    def import_tags(self, json_file):
        """
        Import tags from a JSON file

        Args:
            json_file: Path to JSON file

        Returns:
            Dictionary with import results
        """
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)

            if not isinstance(data, list):
                return {'success': False, 'error': 'Invalid JSON format, expected a list of tags'}

            imported = 0
            errors = 0

            for tag_data in data:
                if not isinstance(tag_data, dict) or 'name' not in tag_data:
                    errors += 1
                    continue

                tag_id = self.create_tag(
                    name=tag_data['name'],
                    category=tag_data.get('category'),
                    color=tag_data.get('color'),
                    description=tag_data.get('description'),
                    parent_name=tag_data.get('parent_name')
                )

                if tag_id:
                    imported += 1
                else:
                    errors += 1

            return {
                'success': True,
                'imported': imported,
                'errors': errors,
                'total': len(data)
            }
        except Exception as e:
            logger.error(f"Error importing tags from '{json_file}': {str(e)}")
            return {'success': False, 'error': str(e)}

    def export_tags(self, json_file):
        """
        Export tags to a JSON file

        Args:
            json_file: Path to JSON file

        Returns:
            True if successful, False otherwise
        """
        try:
            tags = self.get_all_tags()

            # Convert to export format
            export_data = []
            for tag in tags:
                export_data.append({
                    'name': tag['name'],
                    'category': tag['category'],
                    'color': tag['color'],
                    'description': tag['description'],
                    'parent_name': tag['parent_name']
                })

            with open(json_file, 'w') as f:
                json.dump(export_data, f, indent=2)

            return True
        except Exception as e:
            logger.error(f"Error exporting tags to '{json_file}': {str(e)}")
            return False
