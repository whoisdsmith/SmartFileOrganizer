import os
import hashlib
import difflib
from collections import defaultdict
import logging

logger = logging.getLogger("AIDocumentOrganizer")


class DuplicateDetector:
    """
    Class for detecting duplicate and near-duplicate files
    """

    def __init__(self):
        self.progress_callback = None
        self.similarity_threshold = 0.9  # Default similarity threshold for near-duplicates

    def find_duplicates(self, file_list, method="hash", similarity_threshold=None, callback=None):
        """
        Find duplicate files in the given list of files

        Args:
            file_list: List of file paths to check for duplicates
            method: Method to use for duplicate detection ('hash' for exact, 'content' for near-duplicates)
            similarity_threshold: Threshold for content similarity (0.0 to 1.0)
            callback: Optional callback function for progress updates

        Returns:
            Dictionary with duplicate groups
        """
        self.progress_callback = callback

        if similarity_threshold is not None:
            self.similarity_threshold = similarity_threshold

        if method == "hash":
            return self._find_exact_duplicates(file_list)
        elif method == "content":
            return self._find_near_duplicates(file_list)
        else:
            raise ValueError(
                f"Unsupported duplicate detection method: {method}")

    def _find_exact_duplicates(self, file_list):
        """
        Find exact duplicate files using hash-based comparison

        Args:
            file_list: List of file paths to check

        Returns:
            Dictionary with hash as key and list of duplicate files as value
        """
        hash_dict = defaultdict(list)
        total_files = len(file_list)

        for idx, file_path in enumerate(file_list):
            if self.progress_callback:
                self.progress_callback(
                    idx + 1, total_files, os.path.basename(file_path))

            try:
                file_hash = self._calculate_file_hash(file_path)
                hash_dict[file_hash].append(file_path)
            except Exception as e:
                logger.error(
                    f"Error calculating hash for {file_path}: {str(e)}")

        # Filter out unique files (no duplicates)
        return {hash_val: files for hash_val, files in hash_dict.items() if len(files) > 1}

    def _find_near_duplicates(self, file_list):
        """
        Find near-duplicate files using content-based similarity

        Args:
            file_list: List of file paths to check

        Returns:
            Dictionary with group ID as key and list of similar files as value
        """
        # First, group by file size to reduce comparison space
        size_groups = defaultdict(list)
        for file_path in file_list:
            try:
                file_size = os.path.getsize(file_path)
                # Only group files with similar sizes (within 10%)
                size_key = file_size // 1024  # Group by KB
                size_groups[size_key].append(file_path)
            except Exception as e:
                logger.error(f"Error getting size for {file_path}: {str(e)}")

        # Now compare content within each size group
        similarity_groups = {}
        group_id = 0

        total_groups = len(size_groups)
        current_group = 0

        for size_key, files in size_groups.items():
            current_group += 1

            if len(files) < 2:
                continue  # Skip groups with only one file

            if self.progress_callback:
                self.progress_callback(
                    current_group, total_groups, f"Comparing size group {size_key}KB")

            # Compare each file with every other file in the group
            for i in range(len(files)):
                # Skip files already in a similarity group
                if any(files[i] in group for group in similarity_groups.values()):
                    continue

                current_group = [files[i]]

                for j in range(i + 1, len(files)):
                    # Skip files already in a similarity group
                    if any(files[j] in group for group in similarity_groups.values()):
                        continue

                    similarity = self._calculate_content_similarity(
                        files[i], files[j])

                    if similarity >= self.similarity_threshold:
                        current_group.append(files[j])

                if len(current_group) > 1:
                    similarity_groups[group_id] = current_group
                    group_id += 1

        return similarity_groups

    def _calculate_file_hash(self, file_path, algorithm="md5", chunk_size=8192):
        """
        Calculate hash for a file

        Args:
            file_path: Path to the file
            algorithm: Hash algorithm to use ('md5', 'sha1', 'sha256')
            chunk_size: Size of chunks to read

        Returns:
            Hexadecimal hash string
        """
        if algorithm == "md5":
            hasher = hashlib.md5()
        elif algorithm == "sha1":
            hasher = hashlib.sha1()
        elif algorithm == "sha256":
            hasher = hashlib.sha256()
        else:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")

        with open(file_path, 'rb') as f:
            chunk = f.read(chunk_size)
            while chunk:
                hasher.update(chunk)
                chunk = f.read(chunk_size)

        return hasher.hexdigest()

    def _calculate_content_similarity(self, file1, file2, max_size=100000):
        """
        Calculate content similarity between two files

        Args:
            file1: Path to first file
            file2: Path to second file
            max_size: Maximum number of bytes to compare

        Returns:
            Similarity ratio (0.0 to 1.0)
        """
        try:
            # For very large files, only compare a sample
            size1 = os.path.getsize(file1)
            size2 = os.path.getsize(file2)

            # If files are very different in size, they're probably not similar
            if max(size1, size2) > min(size1, size2) * 2:
                return 0.0

            # Read content (or sample for large files)
            with open(file1, 'rb') as f1:
                content1 = f1.read(min(size1, max_size))

            with open(file2, 'rb') as f2:
                content2 = f2.read(min(size2, max_size))

            # For binary files, compare as bytes
            if b'\0' in content1[:1024] or b'\0' in content2[:1024]:
                # Simple byte-by-byte comparison for binary files
                min_len = min(len(content1), len(content2))
                if min_len == 0:
                    return 0.0

                matches = sum(1 for i in range(min_len)
                              if content1[i] == content2[i])
                return matches / min_len
            else:
                # For text files, use difflib
                try:
                    text1 = content1.decode('utf-8', errors='ignore')
                    text2 = content2.decode('utf-8', errors='ignore')
                    return difflib.SequenceMatcher(None, text1, text2).ratio()
                except:
                    # Fallback to byte comparison if decoding fails
                    min_len = min(len(content1), len(content2))
                    if min_len == 0:
                        return 0.0

                    matches = sum(1 for i in range(min_len)
                                  if content1[i] == content2[i])
                    return matches / min_len
        except Exception as e:
            logger.error(f"Error comparing {file1} and {file2}: {str(e)}")
            return 0.0

    def handle_duplicates(self, duplicate_groups, action="report", target_dir=None, keep_strategy="newest"):
        """
        Handle duplicate files according to the specified action

        Args:
            duplicate_groups: Dictionary with duplicate groups
            action: Action to take ('report', 'move', 'delete')
            target_dir: Target directory for moving duplicates
            keep_strategy: Strategy for keeping files ('newest', 'oldest', 'largest', 'smallest')

        Returns:
            Dictionary with results of the operation
        """
        results = {
            "total_groups": len(duplicate_groups),
            "total_duplicates": sum(len(files) - 1 for files in duplicate_groups.values()),
            "space_savings": 0,
            "actions": []
        }

        if action not in ["report", "move", "delete"]:
            raise ValueError(f"Unsupported action: {action}")

        if action in ["move", "delete"] and keep_strategy not in ["newest", "oldest", "largest", "smallest"]:
            raise ValueError(f"Unsupported keep strategy: {keep_strategy}")

        for group_id, files in duplicate_groups.items():
            if len(files) <= 1:
                continue

            # Determine which file to keep based on the strategy
            if keep_strategy == "newest":
                files_with_time = [(f, os.path.getmtime(f)) for f in files]
                files_with_time.sort(key=lambda x: x[1], reverse=True)
                keep_file = files_with_time[0][0]
            elif keep_strategy == "oldest":
                files_with_time = [(f, os.path.getmtime(f)) for f in files]
                files_with_time.sort(key=lambda x: x[1])
                keep_file = files_with_time[0][0]
            elif keep_strategy == "largest":
                files_with_size = [(f, os.path.getsize(f)) for f in files]
                files_with_size.sort(key=lambda x: x[1], reverse=True)
                keep_file = files_with_size[0][0]
            elif keep_strategy == "smallest":
                files_with_size = [(f, os.path.getsize(f)) for f in files]
                files_with_size.sort(key=lambda x: x[1])
                keep_file = files_with_size[0][0]
            else:
                keep_file = files[0]  # Default to first file

            # Process duplicates (all files except the one to keep)
            duplicates = [f for f in files if f != keep_file]

            for dup_file in duplicates:
                file_size = os.path.getsize(dup_file)
                results["space_savings"] += file_size

                action_result = {
                    "file": dup_file,
                    "size": file_size,
                    "keep_file": keep_file,
                    "action": action,
                    "status": "pending"
                }

                if action == "report":
                    action_result["status"] = "reported"
                elif action == "move":
                    if target_dir is None:
                        raise ValueError(
                            "Target directory is required for move action")

                    try:
                        # Create target directory if it doesn't exist
                        os.makedirs(target_dir, exist_ok=True)

                        # Move file to target directory
                        filename = os.path.basename(dup_file)
                        target_path = os.path.join(target_dir, filename)

                        # Handle filename conflicts
                        if os.path.exists(target_path):
                            base, ext = os.path.splitext(filename)
                            target_path = os.path.join(
                                target_dir, f"{base}_dup_{group_id}{ext}")

                        shutil.move(dup_file, target_path)
                        action_result["status"] = "moved"
                        action_result["target_path"] = target_path
                    except Exception as e:
                        action_result["status"] = "error"
                        action_result["error"] = str(e)
                elif action == "delete":
                    try:
                        os.remove(dup_file)
                        action_result["status"] = "deleted"
                    except Exception as e:
                        action_result["status"] = "error"
                        action_result["error"] = str(e)

                results["actions"].append(action_result)

        return results
