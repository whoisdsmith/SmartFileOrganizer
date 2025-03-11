import os
import re
import sqlite3
import time
from datetime import datetime
import logging
from pathlib import Path

logger = logging.getLogger("AIDocumentOrganizer")


class SearchEngine:
    """
    Class for indexing and searching files
    """

    def __init__(self, db_path=None):
        """
        Initialize the search engine

        Args:
            db_path: Path to the SQLite database file (default: search_index.db in user's home directory)
        """
        if db_path is None:
            home_dir = os.path.expanduser("~")
            app_dir = os.path.join(home_dir, ".ai_document_organizer")
            os.makedirs(app_dir, exist_ok=True)
            db_path = os.path.join(app_dir, "search_index.db")

        self.db_path = db_path
        self.progress_callback = None
        self._initialize_database()

    def _initialize_database(self):
        """
        Initialize the SQLite database schema
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Create files table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY,
                    path TEXT UNIQUE,
                    filename TEXT,
                    extension TEXT,
                    size INTEGER,
                    created_time REAL,
                    modified_time REAL,
                    indexed_time REAL,
                    category TEXT,
                    content_hash TEXT
                )
            ''')

            # Create content table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS content (
                    file_id INTEGER,
                    content TEXT,
                    FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE
                )
            ''')

            # Create metadata table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS metadata (
                    file_id INTEGER,
                    key TEXT,
                    value TEXT,
                    FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE
                )
            ''')

            # Create tags table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tags (
                    file_id INTEGER,
                    tag TEXT,
                    FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE
                )
            ''')

            # Create indexes for faster searching
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_files_path ON files (path)')
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_files_filename ON files (filename)')
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_files_extension ON files (extension)')
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_files_category ON files (category)')
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_metadata_key ON metadata (key)')
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_metadata_value ON metadata (value)')
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags (tag)')

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            raise

    def index_files(self, file_info_list, callback=None):
        """
        Index files in the database

        Args:
            file_info_list: List of file information dictionaries
            callback: Optional callback function for progress updates

        Returns:
            Dictionary with indexing results
        """
        self.progress_callback = callback

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        total_files = len(file_info_list)
        indexed_count = 0
        updated_count = 0
        error_count = 0

        for idx, file_info in enumerate(file_info_list):
            if self.progress_callback:
                self.progress_callback(
                    idx + 1, total_files, os.path.basename(file_info['path']))

            try:
                # Check if file already exists in the database
                cursor.execute(
                    'SELECT id, modified_time FROM files WHERE path = ?', (file_info['path'],))
                result = cursor.fetchone()

                file_id = None
                is_update = False

                if result:
                    file_id, db_modified_time = result
                    file_modified_time = file_info.get('modified_time', 0)

                    # Update only if file has been modified
                    if file_modified_time > db_modified_time:
                        is_update = True
                        # Delete existing content and metadata
                        cursor.execute(
                            'DELETE FROM content WHERE file_id = ?', (file_id,))
                        cursor.execute(
                            'DELETE FROM metadata WHERE file_id = ?', (file_id,))
                        cursor.execute(
                            'DELETE FROM tags WHERE file_id = ?', (file_id,))

                        # Update file information
                        cursor.execute('''
                            UPDATE files SET
                                filename = ?,
                                size = ?,
                                modified_time = ?,
                                indexed_time = ?,
                                category = ?
                            WHERE id = ?
                        ''', (
                            os.path.basename(file_info['path']),
                            file_info.get('file_size', 0),
                            file_info.get('modified_time', 0),
                            time.time(),
                            file_info.get('category', ''),
                            file_id
                        ))

                        updated_count += 1
                    else:
                        # Skip files that haven't been modified
                        continue
                else:
                    # Insert new file
                    cursor.execute('''
                        INSERT INTO files (
                            path, filename, extension, size, created_time, modified_time, indexed_time, category, content_hash
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        file_info['path'],
                        os.path.basename(file_info['path']),
                        os.path.splitext(file_info['path'])[1].lower(),
                        file_info.get('file_size', 0),
                        file_info.get('created_time', 0),
                        file_info.get('modified_time', 0),
                        time.time(),
                        file_info.get('category', ''),
                        file_info.get('content_hash', '')
                    ))

                    file_id = cursor.lastrowid
                    indexed_count += 1

                # Insert content
                if 'content' in file_info and file_info['content']:
                    cursor.execute('INSERT INTO content (file_id, content) VALUES (?, ?)',
                                   (file_id, file_info['content']))

                # Insert metadata
                if 'metadata' in file_info and file_info['metadata']:
                    for key, value in file_info['metadata'].items():
                        if value is not None:
                            cursor.execute('INSERT INTO metadata (file_id, key, value) VALUES (?, ?, ?)',
                                           (file_id, key, str(value)))

                # Insert tags
                if 'tags' in file_info and file_info['tags']:
                    for tag in file_info['tags']:
                        cursor.execute('INSERT INTO tags (file_id, tag) VALUES (?, ?)',
                                       (file_id, tag))

                # Commit every 100 files to avoid large transactions
                if (idx + 1) % 100 == 0:
                    conn.commit()

            except Exception as e:
                logger.error(
                    f"Error indexing file {file_info['path']}: {str(e)}")
                error_count += 1

        # Final commit
        conn.commit()
        conn.close()

        return {
            "total": total_files,
            "indexed": indexed_count,
            "updated": updated_count,
            "errors": error_count
        }

    def remove_missing_files(self, existing_paths):
        """
        Remove files from the index that no longer exist

        Args:
            existing_paths: List of existing file paths

        Returns:
            Number of files removed from the index
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all indexed file paths
        cursor.execute('SELECT id, path FROM files')
        indexed_files = cursor.fetchall()

        # Convert existing_paths to a set for faster lookups
        existing_paths_set = set(existing_paths)

        removed_count = 0

        for file_id, file_path in indexed_files:
            if file_path not in existing_paths_set:
                # File no longer exists, remove from index
                cursor.execute('DELETE FROM files WHERE id = ?', (file_id,))
                removed_count += 1

        conn.commit()
        conn.close()

        return removed_count

    def search(self, query, filters=None, sort_by="relevance", page=1, page_size=20):
        """
        Search for files matching the query and filters

        Args:
            query: Search query string
            filters: Dictionary with filters (file_type, category, date_range, size_range, tags)
            sort_by: Sort results by ('relevance', 'date', 'size', 'name')
            page: Page number (1-based)
            page_size: Number of results per page

        Returns:
            Dictionary with search results and pagination info
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        cursor = conn.cursor()

        # Parse query for special operators
        parsed_query = self._parse_query(query)

        # Build the SQL query
        sql_query = '''
            SELECT DISTINCT f.id, f.path, f.filename, f.extension, f.size,
                   f.created_time, f.modified_time, f.category
            FROM files f
            LEFT JOIN content c ON f.id = c.file_id
            LEFT JOIN metadata m ON f.id = m.file_id
            LEFT JOIN tags t ON f.id = t.file_id
            WHERE 1=1
        '''

        params = []

        # Add search conditions
        if parsed_query['terms']:
            search_conditions = []
            for term in parsed_query['terms']:
                if term.startswith('-'):
                    # Exclude term
                    term = term[1:]
                    search_conditions.append('''
                        f.id NOT IN (
                            SELECT file_id FROM content WHERE content LIKE ?
                            UNION
                            SELECT file_id FROM metadata WHERE value LIKE ?
                            UNION
                            SELECT id FROM files WHERE filename LIKE ?
                        )
                    ''')
                    params.extend([f'%{term}%', f'%{term}%', f'%{term}%'])
                else:
                    # Include term
                    search_conditions.append('''
                        (c.content LIKE ? OR m.value LIKE ? OR f.filename LIKE ?)
                    ''')
                    params.extend([f'%{term}%', f'%{term}%', f'%{term}%'])

            if search_conditions:
                sql_query += ' AND ' + ' AND '.join(search_conditions)

        # Add filters
        if filters:
            if 'file_type' in filters and filters['file_type']:
                if isinstance(filters['file_type'], list):
                    placeholders = ', '.join(
                        ['?' for _ in filters['file_type']])
                    sql_query += f' AND f.extension IN ({placeholders})'
                    params.extend(filters['file_type'])
                else:
                    sql_query += ' AND f.extension = ?'
                    params.append(filters['file_type'])

            if 'category' in filters and filters['category']:
                if isinstance(filters['category'], list):
                    placeholders = ', '.join(
                        ['?' for _ in filters['category']])
                    sql_query += f' AND f.category IN ({placeholders})'
                    params.extend(filters['category'])
                else:
                    sql_query += ' AND f.category = ?'
                    params.append(filters['category'])

            if 'date_range' in filters and filters['date_range']:
                if 'start' in filters['date_range'] and filters['date_range']['start']:
                    start_timestamp = self._date_to_timestamp(
                        filters['date_range']['start'])
                    sql_query += ' AND f.modified_time >= ?'
                    params.append(start_timestamp)

                if 'end' in filters['date_range'] and filters['date_range']['end']:
                    end_timestamp = self._date_to_timestamp(
                        filters['date_range']['end'])
                    sql_query += ' AND f.modified_time <= ?'
                    params.append(end_timestamp)

            if 'size_range' in filters and filters['size_range']:
                if 'min' in filters['size_range'] and filters['size_range']['min'] is not None:
                    sql_query += ' AND f.size >= ?'
                    params.append(filters['size_range']['min'])

                if 'max' in filters['size_range'] and filters['size_range']['max'] is not None:
                    sql_query += ' AND f.size <= ?'
                    params.append(filters['size_range']['max'])

            if 'tags' in filters and filters['tags']:
                if isinstance(filters['tags'], list):
                    tag_conditions = []
                    for tag in filters['tags']:
                        tag_conditions.append('t.tag = ?')
                        params.append(tag)

                    sql_query += ' AND (' + ' OR '.join(tag_conditions) + ')'
                else:
                    sql_query += ' AND t.tag = ?'
                    params.append(filters['tags'])

        # Add sorting
        if sort_by == 'date':
            sql_query += ' ORDER BY f.modified_time DESC'
        elif sort_by == 'size':
            sql_query += ' ORDER BY f.size DESC'
        elif sort_by == 'name':
            sql_query += ' ORDER BY f.filename ASC'
        else:  # relevance - default
            # For relevance sorting, we need to count matches
            # This is a simplified approach - a real implementation would use full-text search
            if parsed_query['terms']:
                sql_query = f'''
                    SELECT *, (
                        {' + '.join(['(CASE WHEN c.content LIKE ? THEN 1 ELSE 0 END)' for _ in parsed_query['terms']])} +
                        {' + '.join(['(CASE WHEN m.value LIKE ? THEN 1 ELSE 0 END)' for _ in parsed_query['terms']])} +
                        {' + '.join(['(CASE WHEN f.filename LIKE ? THEN 2 ELSE 0 END)' for _ in parsed_query['terms']])}
                    ) as relevance
                    FROM ({sql_query})
                    ORDER BY relevance DESC
                '''
                for term in parsed_query['terms']:
                    if not term.startswith('-'):
                        params.extend([f'%{term}%', f'%{term}%', f'%{term}%'])

        # Add pagination
        offset = (page - 1) * page_size
        sql_query += ' LIMIT ? OFFSET ?'
        params.extend([page_size, offset])

        # Execute the query
        cursor.execute(sql_query, params)
        results = [dict(row) for row in cursor.fetchall()]

        # Get total count for pagination
        count_query = f'''
            SELECT COUNT(DISTINCT f.id) as total
            FROM files f
            LEFT JOIN content c ON f.id = c.file_id
            LEFT JOIN metadata m ON f.id = m.file_id
            LEFT JOIN tags t ON f.id = t.file_id
            WHERE 1=1
        '''

        # Add the same conditions as the main query (without ORDER BY and LIMIT)
        if parsed_query['terms'] or filters:
            count_params = params[:-2]  # Remove LIMIT and OFFSET params
            cursor.execute(count_query + sql_query.split('ORDER BY')
                           [0].split('LIMIT')[0], count_params)
        else:
            cursor.execute(count_query)

        total_count = cursor.fetchone()['total']

        # Fetch additional information for each result
        for result in results:
            # Get metadata
            cursor.execute(
                'SELECT key, value FROM metadata WHERE file_id = ?', (result['id'],))
            result['metadata'] = {row['key']: row['value']
                                  for row in cursor.fetchall()}

            # Get tags
            cursor.execute(
                'SELECT tag FROM tags WHERE file_id = ?', (result['id'],))
            result['tags'] = [row['tag'] for row in cursor.fetchall()]

            # Format dates
            if 'created_time' in result and result['created_time']:
                result['created_time_formatted'] = datetime.fromtimestamp(
                    result['created_time']).strftime('%Y-%m-%d %H:%M:%S')

            if 'modified_time' in result and result['modified_time']:
                result['modified_time_formatted'] = datetime.fromtimestamp(
                    result['modified_time']).strftime('%Y-%m-%d %H:%M:%S')

            # Format file size
            if 'size' in result and result['size']:
                result['size_formatted'] = self._format_file_size(
                    result['size'])

        conn.close()

        return {
            'results': results,
            'total': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size,
            'query': query,
            'filters': filters,
            'sort_by': sort_by
        }

    def _parse_query(self, query):
        """
        Parse search query string into components

        Args:
            query: Search query string

        Returns:
            Dictionary with parsed query components
        """
        result = {
            'terms': [],
            'exact_phrases': [],
            'file_types': [],
            'date_range': None,
            'size_range': None,
            'tags': [],
            'exclude_tags': []
        }

        if not query or not query.strip():
            return result

        # Extract exact phrases (quoted text)
        exact_phrases = re.findall(r'"([^"]+)"', query)
        for phrase in exact_phrases:
            result['exact_phrases'].append(phrase)
            # Remove the phrase from the query
            query = query.replace(f'"{phrase}"', '', 1)

        # Extract file type filters
        file_type_matches = re.findall(r'type:(\w+)', query)
        for file_type in file_type_matches:
            result['file_types'].append(file_type.lower())
            # Remove the file type filter from the query
            query = query.replace(f'type:{file_type}', '', 1)

        # Extract date range filters
        date_range_match = re.search(
            r'date:(\d{4}-\d{2}-\d{2})\.\.(\d{4}-\d{2}-\d{2})', query)
        if date_range_match:
            start_date = date_range_match.group(1)
            end_date = date_range_match.group(2)
            result['date_range'] = (start_date, end_date)
            # Remove the date range filter from the query
            query = query.replace(f'date:{start_date}..{end_date}', '', 1)
        else:
            # Check for single date filter
            date_match = re.search(r'date:(\d{4}-\d{2}-\d{2})', query)
            if date_match:
                date = date_match.group(1)
                result['date_range'] = (date, date)
                # Remove the date filter from the query
                query = query.replace(f'date:{date}', '', 1)

        # Extract size range filters (in KB, MB, or GB)
        size_pattern = r'size:(\d+(?:\.\d+)?(?:kb|mb|gb)?)\.\.(\d+(?:\.\d+)?(?:kb|mb|gb)?)'
        size_range_match = re.search(size_pattern, query, re.IGNORECASE)
        if size_range_match:
            min_size = self._parse_size(size_range_match.group(1))
            max_size = self._parse_size(size_range_match.group(2))
            result['size_range'] = (min_size, max_size)
            # Remove the size range filter from the query
            query = query.replace(size_range_match.group(0), '', 1)
        else:
            # Check for single size filter
            size_match = re.search(
                r'size:([><]?)(\d+(?:\.\d+)?(?:kb|mb|gb)?)', query, re.IGNORECASE)
            if size_match:
                operator = size_match.group(1)
                size = self._parse_size(size_match.group(2))

                if operator == '>':
                    result['size_range'] = (size, None)
                elif operator == '<':
                    result['size_range'] = (None, size)
                else:
                    # Exact size match with a small range
                    result['size_range'] = (size * 0.95, size * 1.05)

                # Remove the size filter from the query
                query = query.replace(size_match.group(0), '', 1)

        # Extract tag filters
        tag_matches = re.findall(r'tag:([^\s]+)', query)
        for tag in tag_matches:
            if tag.startswith('-'):
                result['exclude_tags'].append(tag[1:])
            else:
                result['tags'].append(tag)
            # Remove the tag filter from the query
            query = query.replace(f'tag:{tag}', '', 1)

        # Process remaining terms
        terms = query.split()
        for term in terms:
            if term.strip():
                result['terms'].append(term.strip())

        return result

    def _parse_size(self, size_str):
        """
        Parse size string to bytes

        Args:
            size_str: Size string (e.g., "10kb", "5.2mb", "1gb")

        Returns:
            Size in bytes
        """
        size_str = size_str.lower()

        # Extract numeric value and unit
        match = re.match(r'(\d+(?:\.\d+)?)([kmg]?b)?', size_str)
        if not match:
            return 0

        value = float(match.group(1))
        unit = match.group(2) or 'b'

        # Convert to bytes
        if unit == 'kb':
            return value * 1024
        elif unit == 'mb':
            return value * 1024 * 1024
        elif unit == 'gb':
            return value * 1024 * 1024 * 1024
        else:  # bytes
            return value

    def _date_to_timestamp(self, date_str):
        """
        Convert date string to timestamp

        Args:
            date_str: Date string in format YYYY-MM-DD

        Returns:
            Timestamp
        """
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            return dt.timestamp()
        except:
            return 0

    def _format_file_size(self, size_bytes):
        """
        Format file size in human-readable format

        Args:
            size_bytes: File size in bytes

        Returns:
            Formatted file size string
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
