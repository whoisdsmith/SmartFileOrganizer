import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import threading
import queue
import time
import logging

# Local imports
from .file_analyzer import FileAnalyzer
from .file_organizer import FileOrganizer
from .settings_manager import SettingsManager
from .ai_analyzer import AIAnalyzer
from .openai_analyzer import OpenAIAnalyzer
from .utils import get_readable_size, sanitize_filename
from .duplicate_detector import DuplicateDetector
from .search_engine import SearchEngine
from .tag_manager import TagManager

logger = logging.getLogger("AIDocumentOrganizer")


class DocumentOrganizerApp:
    def __init__(self, root):
        """Initialize the application"""
        self.root = root
        self.root.title("AI Document Organizer")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)

        # Set icon if available
        try:
            if os.name == 'nt':  # Windows
                self.root.iconbitmap(self._resource_path("assets/icon.ico"))
            else:  # macOS/Linux
                icon_img = tk.PhotoImage(
                    file=self._resource_path("assets/icon.png"))
                self.root.iconphoto(True, icon_img)
        except Exception as e:
            logger.warning(f"Could not set application icon: {e}")

        # Initialize components
        self.file_analyzer = FileAnalyzer()
        self.file_organizer = FileOrganizer()
        self.settings_manager = SettingsManager()
        self.duplicate_detector = DuplicateDetector()
        self.search_engine = SearchEngine()
        self.tag_manager = TagManager()

        # Load settings
        self.settings = self.settings_manager.load_settings()

        # Initialize variables
        self.source_dir = tk.StringVar(
            value=self.settings.get("last_source_dir", ""))
        self.target_dir = tk.StringVar(
            value=self.settings.get("last_target_dir", ""))
        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        self.progress_var = tk.DoubleVar(value=0)
        self.theme_var = tk.StringVar(
            value=self.settings.get("theme", "System"))
        self.batch_size_var = tk.StringVar(
            value=str(self.settings.get("batch_size", 5)))
        self.batch_delay_var = tk.StringVar(
            value=str(self.settings.get("batch_delay", 10.0)))
        self.log_to_file_only_var = tk.BooleanVar(
            value=self.settings.get("log_to_file_only", False))

        # Organization options
        self.create_category_folders_var = tk.BooleanVar(
            value=self.settings.get("create_category_folders", True))
        self.generate_summaries_var = tk.BooleanVar(
            value=self.settings.get("generate_summaries", True))
        self.include_metadata_var = tk.BooleanVar(
            value=self.settings.get("include_metadata", True))
        self.copy_instead_of_move_var = tk.BooleanVar(
            value=self.settings.get("copy_instead_of_move", True))

        # New options for Stage 1 features
        self.detect_duplicates_var = tk.BooleanVar(
            value=self.settings.get("detect_duplicates", False))
        self.duplicate_action_var = tk.StringVar(
            value=self.settings.get("duplicate_action", "report"))
        self.duplicate_strategy_var = tk.StringVar(
            value=self.settings.get("duplicate_strategy", "newest"))
        self.apply_tags_var = tk.BooleanVar(
            value=self.settings.get("apply_tags", False))
        self.suggest_tags_var = tk.BooleanVar(
            value=self.settings.get("suggest_tags", False))

        # Thread control
        self.queue = queue.Queue()
        self.running = False
        self.cancel_requested = False

        # Store analyzed files
        self.analyzed_files = []

        # Create widgets
        self._create_widgets()
        self._setup_layout()

        # Apply theme
        self.apply_theme()

        # Set up queue consumer
        self.root.after(100, self.consume_queue)

        logger.info("GUI initialized")

    def _create_widgets(self):
        """Create the GUI widgets"""
        # Create main frames
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.top_frame = ttk.Frame(self.main_frame, padding="5")
        self.middle_frame = ttk.Frame(self.main_frame, padding="5")
        self.bottom_frame = ttk.Frame(self.main_frame, padding="5")

        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.middle_frame)

        # Create tabs
        self.files_tab = ttk.Frame(self.notebook)
        self.duplicates_tab = ttk.Frame(self.notebook)
        self.search_tab = ttk.Frame(self.notebook)
        self.tags_tab = ttk.Frame(self.notebook)
        self.settings_tab = ttk.Frame(self.notebook)

        # Add tabs to notebook
        self.notebook.add(self.files_tab, text="Files")
        self.notebook.add(self.duplicates_tab, text="Duplicates")
        self.notebook.add(self.search_tab, text="Advanced Search")
        self.notebook.add(self.tags_tab, text="Tags")
        self.notebook.add(self.settings_tab, text="Settings")

        # Create directory selection frame
        self.dir_frame = ttk.LabelFrame(
            self.top_frame, text="Directories", padding="5")

        # Source directory
        self.source_label = ttk.Label(self.dir_frame, text="Source Directory:")
        self.source_entry = ttk.Entry(
            self.dir_frame, textvariable=self.source_dir, width=50)
        self.source_button = ttk.Button(
            self.dir_frame, text="Browse", command=self.browse_source)

        # Target directory
        self.target_label = ttk.Label(self.dir_frame, text="Target Directory:")
        self.target_entry = ttk.Entry(
            self.dir_frame, textvariable=self.target_dir, width=50)
        self.target_button = ttk.Button(
            self.dir_frame, text="Browse", command=self.browse_target)

        # Create options frame
        self.options_frame = ttk.LabelFrame(
            self.top_frame, text="Options", padding="5")

        # Batch size options
        self.batch_label = ttk.Label(self.options_frame, text="Batch Size:")
        self.batch_combobox = ttk.Combobox(self.options_frame, textvariable=self.batch_size_var,
                                           values=["5", "10", "20", "50", "100"], width=5)
        self.batch_combobox.current(0)  # Default to 5

        # Create action buttons frame
        self.action_frame = ttk.Frame(self.top_frame, padding="5")

        # Scan button
        self.scan_button = ttk.Button(
            self.action_frame, text="Scan Files", command=self.start_scan)

        # Organize button
        self.organize_button = ttk.Button(
            self.action_frame, text="Organize Files", command=self.organize_files)

        # Cancel button
        self.cancel_button = ttk.Button(
            self.action_frame, text="Cancel", command=self.cancel_operation)

        # Create status frame
        self.status_frame = ttk.LabelFrame(
            self.bottom_frame, text="Status", padding="5")

        # Status label
        self.status_label = ttk.Label(self.status_frame, text="Ready")

        # Progress bar
        self.progress_bar = ttk.Progressbar(
            self.status_frame, orient="horizontal", length=400, mode="determinate", variable=self.progress_var)

        # Progress details
        self.progress_details = ttk.Label(self.status_frame, text="")

        # Processed files
        self.processed_label = ttk.Label(self.status_frame, text="Files: 0")

        # Total files
        self.total_label = ttk.Label(self.status_frame, text="Total: 0")

        # Batch status
        self.batch_status_label = ttk.Label(self.status_frame, text="")

        # Create files tab content
        self.files_frame = ttk.Frame(self.files_tab, padding="5")

        # Search frame
        self.search_frame = ttk.Frame(self.files_frame, padding="5")
        self.search_label = ttk.Label(self.search_frame, text="Search:")
        self.search_entry = ttk.Entry(
            self.search_frame, textvariable=self.search_var, width=30)
        self.search_entry.bind("<KeyRelease>", self.search_files)

        # Create treeview for file list
        self.tree_frame = ttk.Frame(self.files_frame, padding="5")
        self.tree = ttk.Treeview(self.tree_frame, columns=(
            "Category", "Type", "Size"), show="headings")
        self.tree.heading("Category", text="Category")
        self.tree.heading("Type", text="Type")
        self.tree.heading("Size", text="Size")
        self.tree.column("Category", width=150)
        self.tree.column("Type", width=100)
        self.tree.column("Size", width=100)

        # Add scrollbars to treeview
        self.tree_yscroll = ttk.Scrollbar(
            self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.tree_yscroll.set)

        # Bind treeview selection
        self.tree.bind("<<TreeviewSelect>>", self.show_file_details)

        # Create details frame
        self.details_frame = ttk.LabelFrame(
            self.files_frame, text="File Details", padding="5")
        self.details_text = ScrolledText(
            self.details_frame, width=50, height=15, wrap=tk.WORD)
        self.details_text.config(state=tk.DISABLED)

        # Create duplicates tab content
        self.duplicates_frame = ttk.Frame(self.duplicates_tab, padding="5")

        # Duplicate detection options
        self.dup_options_frame = ttk.LabelFrame(
            self.duplicates_frame, text="Duplicate Detection Options", padding="5")

        # Enable duplicate detection
        self.detect_duplicates_check = ttk.Checkbutton(self.dup_options_frame, text="Detect duplicates during organization",
                                                       variable=self.detect_duplicates_var)

        # Duplicate action
        self.dup_action_label = ttk.Label(
            self.dup_options_frame, text="Action:")
        self.dup_action_combo = ttk.Combobox(self.dup_options_frame, textvariable=self.duplicate_action_var,
                                             values=["report", "move", "delete"], width=10)
        self.dup_action_combo.current(0)  # Default to "report"

        # Duplicate strategy
        self.dup_strategy_label = ttk.Label(
            self.dup_options_frame, text="Keep strategy:")
        self.dup_strategy_combo = ttk.Combobox(self.dup_options_frame, textvariable=self.duplicate_strategy_var,
                                               values=["newest", "oldest", "largest", "smallest"], width=10)
        self.dup_strategy_combo.current(0)  # Default to "newest"

        # Duplicate detection method
        self.dup_method_label = ttk.Label(
            self.dup_options_frame, text="Detection method:")
        self.dup_method_var = tk.StringVar(value="hash")
        self.dup_method_combo = ttk.Combobox(self.dup_options_frame, textvariable=self.dup_method_var,
                                             values=["hash", "content"], width=10)
        self.dup_method_combo.current(0)  # Default to "hash"

        # Similarity threshold
        self.similarity_label = ttk.Label(
            self.dup_options_frame, text="Similarity threshold:")
        self.similarity_var = tk.DoubleVar(value=0.9)
        self.similarity_scale = ttk.Scale(self.dup_options_frame, from_=0.5, to=1.0,
                                          variable=self.similarity_var, orient=tk.HORIZONTAL, length=200)
        self.similarity_value_label = ttk.Label(
            self.dup_options_frame, text="0.9")

        # Update similarity value label when scale changes
        def update_similarity_label(*args):
            self.similarity_value_label.config(
                text=f"{self.similarity_var.get():.2f}")
        self.similarity_var.trace_add("write", update_similarity_label)

        # Manual duplicate detection
        self.manual_dup_frame = ttk.LabelFrame(
            self.duplicates_frame, text="Manual Duplicate Detection", padding="5")

        # Directory selection
        self.dup_dir_label = ttk.Label(
            self.manual_dup_frame, text="Directory:")
        self.dup_dir_var = tk.StringVar()
        self.dup_dir_entry = ttk.Entry(
            self.manual_dup_frame, textvariable=self.dup_dir_var, width=40)
        self.dup_dir_button = ttk.Button(self.manual_dup_frame, text="Browse",
                                         command=lambda: self.browse_directory(self.dup_dir_var))

        # Scan for duplicates button
        self.scan_dup_button = ttk.Button(self.manual_dup_frame, text="Scan for Duplicates",
                                          command=self.scan_for_duplicates)

        # Duplicate results
        self.dup_results_frame = ttk.LabelFrame(
            self.duplicates_frame, text="Duplicate Results", padding="5")

        # Duplicate treeview
        self.dup_tree = ttk.Treeview(self.dup_results_frame, columns=(
            "Group", "Files", "Size"), show="headings")
        self.dup_tree.heading("Group", text="Group")
        self.dup_tree.heading("Files", text="Files")
        self.dup_tree.heading("Size", text="Size")
        self.dup_tree.column("Group", width=50)
        self.dup_tree.column("Files", width=300)
        self.dup_tree.column("Size", width=100)

        # Add scrollbars to duplicate treeview
        self.dup_tree_yscroll = ttk.Scrollbar(
            self.dup_results_frame, orient="vertical", command=self.dup_tree.yview)
        self.dup_tree.configure(yscrollcommand=self.dup_tree_yscroll.set)

        # Bind duplicate treeview selection
        self.dup_tree.bind("<<TreeviewSelect>>", self.show_duplicate_details)

        # Handle duplicates button
        self.handle_dup_button = ttk.Button(self.dup_results_frame, text="Handle Duplicates",
                                            command=self.handle_duplicates, state=tk.DISABLED)

        # Duplicate details
        self.dup_details_frame = ttk.LabelFrame(
            self.duplicates_frame, text="Duplicate Details", padding="5")
        self.dup_details_text = ScrolledText(
            self.dup_details_frame, width=50, height=10, wrap=tk.WORD)
        self.dup_details_text.config(state=tk.DISABLED)

        # Create advanced search tab content
        self.search_tab_frame = ttk.Frame(self.search_tab, padding="5")

        # Search options
        self.search_options_frame = ttk.LabelFrame(
            self.search_tab_frame, text="Search Options", padding="5")

        # Search query
        self.adv_search_label = ttk.Label(
            self.search_options_frame, text="Search query:")
        self.adv_search_var = tk.StringVar()
        self.adv_search_entry = ttk.Entry(
            self.search_options_frame, textvariable=self.adv_search_var, width=40)

        # File type filter
        self.file_type_label = ttk.Label(
            self.search_options_frame, text="File type:")
        self.file_type_var = tk.StringVar()
        self.file_type_combo = ttk.Combobox(self.search_options_frame, textvariable=self.file_type_var,
                                            values=["All", "PDF", "Word", "Excel", "Text", "HTML", "Markdown"], width=10)
        self.file_type_combo.current(0)  # Default to "All"

        # Category filter
        self.category_label = ttk.Label(
            self.search_options_frame, text="Category:")
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(self.search_options_frame, textvariable=self.category_var,
                                           values=["All"], width=15)
        self.category_combo.current(0)  # Default to "All"

        # Date range filter
        self.date_range_frame = ttk.Frame(self.search_options_frame)
        self.date_from_label = ttk.Label(
            self.date_range_frame, text="Date from:")
        self.date_from_var = tk.StringVar()
        self.date_from_entry = ttk.Entry(
            self.date_range_frame, textvariable=self.date_from_var, width=10)
        self.date_to_label = ttk.Label(self.date_range_frame, text="to:")
        self.date_to_var = tk.StringVar()
        self.date_to_entry = ttk.Entry(
            self.date_range_frame, textvariable=self.date_to_var, width=10)

        # Search button
        self.adv_search_button = ttk.Button(self.search_options_frame, text="Search",
                                            command=self.perform_advanced_search)

        # Index management
        self.index_frame = ttk.LabelFrame(
            self.search_tab_frame, text="Index Management", padding="5")

        # Directory selection
        self.index_dir_label = ttk.Label(
            self.index_frame, text="Directory to index:")
        self.index_dir_var = tk.StringVar()
        self.index_dir_entry = ttk.Entry(
            self.index_frame, textvariable=self.index_dir_var, width=40)
        self.index_dir_button = ttk.Button(self.index_frame, text="Browse",
                                           command=lambda: self.browse_directory(self.index_dir_var))

        # Index button
        self.index_button = ttk.Button(
            self.index_frame, text="Index Files", command=self.index_files)

        # Search results
        self.search_results_frame = ttk.LabelFrame(
            self.search_tab_frame, text="Search Results", padding="5")

        # Search results treeview
        self.search_tree = ttk.Treeview(self.search_results_frame,
                                        columns=("Filename", "Category", "Type", "Size"), show="headings")
        self.search_tree.heading("Filename", text="Filename")
        self.search_tree.heading("Category", text="Category")
        self.search_tree.heading("Type", text="Type")
        self.search_tree.heading("Size", text="Size")
        self.search_tree.column("Filename", width=200)
        self.search_tree.column("Category", width=150)
        self.search_tree.column("Type", width=100)
        self.search_tree.column("Size", width=100)

        # Add scrollbars to search treeview
        self.search_tree_yscroll = ttk.Scrollbar(self.search_results_frame, orient="vertical",
                                                 command=self.search_tree.yview)
        self.search_tree.configure(yscrollcommand=self.search_tree_yscroll.set)

        # Bind search treeview selection
        self.search_tree.bind("<<TreeviewSelect>>",
                              self.show_search_result_details)

        # Search result details
        self.search_details_frame = ttk.LabelFrame(
            self.search_tab_frame, text="Result Details", padding="5")
        self.search_details_text = ScrolledText(
            self.search_details_frame, width=50, height=10, wrap=tk.WORD)
        self.search_details_text.config(state=tk.DISABLED)

        # Create tags tab content
        self.tags_frame = ttk.Frame(self.tags_tab, padding="5")

        # Tag options
        self.tag_options_frame = ttk.LabelFrame(
            self.tags_frame, text="Tag Options", padding="5")

        # Enable tagging
        self.apply_tags_check = ttk.Checkbutton(self.tag_options_frame, text="Apply tags during organization",
                                                variable=self.apply_tags_var)

        # Suggest tags
        self.suggest_tags_check = ttk.Checkbutton(self.tag_options_frame, text="Suggest additional tags",
                                                  variable=self.suggest_tags_var)

        # Tag management
        self.tag_management_frame = ttk.LabelFrame(
            self.tags_frame, text="Tag Management", padding="5")

        # Tag list
        self.tag_list_frame = ttk.Frame(self.tag_management_frame)
        self.tag_list_label = ttk.Label(self.tag_list_frame, text="Tags:")
        self.tag_list = ttk.Treeview(self.tag_list_frame, columns=(
            "Category", "Count"), show="headings")
        self.tag_list.heading("Category", text="Category")
        self.tag_list.heading("Count", text="Count")
        self.tag_list.column("Category", width=150)
        self.tag_list.column("Count", width=50)

        # Add scrollbars to tag list
        self.tag_list_yscroll = ttk.Scrollbar(
            self.tag_list_frame, orient="vertical", command=self.tag_list.yview)
        self.tag_list.configure(yscrollcommand=self.tag_list_yscroll.set)

        # Tag actions
        self.tag_actions_frame = ttk.Frame(self.tag_management_frame)
        self.add_tag_button = ttk.Button(
            self.tag_actions_frame, text="Add Tag", command=self.add_tag)
        self.edit_tag_button = ttk.Button(
            self.tag_actions_frame, text="Edit Tag", command=self.edit_tag)
        self.delete_tag_button = ttk.Button(
            self.tag_actions_frame, text="Delete Tag", command=self.delete_tag)

        # Import/Export tags
        self.tag_io_frame = ttk.Frame(self.tag_management_frame)
        self.import_tags_button = ttk.Button(
            self.tag_io_frame, text="Import Tags", command=self.import_tags)
        self.export_tags_button = ttk.Button(
            self.tag_io_frame, text="Export Tags", command=self.export_tags)

        # Files by tag
        self.files_by_tag_frame = ttk.LabelFrame(
            self.tags_frame, text="Files by Tag", padding="5")

        # Tag selection
        self.tag_selection_frame = ttk.Frame(self.files_by_tag_frame)
        self.tag_selection_label = ttk.Label(
            self.tag_selection_frame, text="Select tag:")
        self.tag_selection_var = tk.StringVar()
        self.tag_selection_combo = ttk.Combobox(
            self.tag_selection_frame, textvariable=self.tag_selection_var, width=20)
        self.find_files_button = ttk.Button(
            self.tag_selection_frame, text="Find Files", command=self.find_files_by_tag)

        # Files with tag
        self.tagged_files_frame = ttk.Frame(self.files_by_tag_frame)
        self.tagged_files_tree = ttk.Treeview(
            self.tagged_files_frame, columns=("Path", "Type"), show="headings")
        self.tagged_files_tree.heading("Path", text="Path")
        self.tagged_files_tree.heading("Type", text="Type")
        self.tagged_files_tree.column("Path", width=350)
        self.tagged_files_tree.column("Type", width=100)

        # Add scrollbars to tagged files tree
        self.tagged_files_yscroll = ttk.Scrollbar(self.tagged_files_frame, orient="vertical",
                                                  command=self.tagged_files_tree.yview)
        self.tagged_files_tree.configure(
            yscrollcommand=self.tagged_files_yscroll.set)

        # Create settings tab content
        self._create_settings_widgets()

    def _setup_layout(self):
        """Set up the layout of the GUI widgets"""
        # Main frame
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Top frame
        self.top_frame.pack(fill=tk.X, pady=5)

        # Directory frame
        self.dir_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Source directory
        self.source_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.source_entry.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)
        self.source_button.grid(row=0, column=2, padx=5, pady=5)

        # Target directory
        self.target_label.grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.target_entry.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)
        self.target_button.grid(row=1, column=2, padx=5, pady=5)

        # Configure grid
        self.dir_frame.columnconfigure(1, weight=1)

        # Options frame
        self.options_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)

        # Batch size
        self.batch_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.batch_combobox.grid(row=0, column=1, padx=5, pady=5)

        # Action frame
        self.action_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)

        # Scan button
        self.scan_button.pack(fill=tk.X, pady=2)

        # Organize button
        self.organize_button.pack(fill=tk.X, pady=2)

        # Cancel button
        self.cancel_button.pack(fill=tk.X, pady=2)

        # Middle frame with notebook
        self.middle_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Files tab
        self.files_frame.pack(fill=tk.BOTH, expand=True)

        # Search frame
        self.search_frame.pack(fill=tk.X, pady=5)
        self.search_label.pack(side=tk.LEFT, padx=5)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Tree frame
        self.tree_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree_yscroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Details frame
        self.details_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.details_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Duplicates tab
        self.duplicates_frame.pack(fill=tk.BOTH, expand=True)

        # Duplicate options frame
        self.dup_options_frame.pack(fill=tk.X, pady=5)

        # Enable duplicate detection
        self.detect_duplicates_check.grid(
            row=0, column=0, columnspan=4, sticky=tk.W, padx=5, pady=5)

        # Duplicate action
        self.dup_action_label.grid(
            row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.dup_action_combo.grid(
            row=1, column=1, sticky=tk.W, padx=5, pady=5)

        # Duplicate strategy
        self.dup_strategy_label.grid(
            row=1, column=2, sticky=tk.W, padx=5, pady=5)
        self.dup_strategy_combo.grid(
            row=1, column=3, sticky=tk.W, padx=5, pady=5)

        # Duplicate detection method
        self.dup_method_label.grid(
            row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.dup_method_combo.grid(
            row=2, column=1, sticky=tk.W, padx=5, pady=5)

        # Similarity threshold
        self.similarity_label.grid(
            row=2, column=2, sticky=tk.W, padx=5, pady=5)
        self.similarity_scale.grid(
            row=2, column=3, sticky=tk.W, padx=5, pady=5)
        self.similarity_value_label.grid(
            row=2, column=4, sticky=tk.W, padx=5, pady=5)

        # Manual duplicate detection frame
        self.manual_dup_frame.pack(fill=tk.X, pady=5)

        # Directory selection
        self.dup_dir_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.dup_dir_entry.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)
        self.dup_dir_button.grid(row=0, column=2, padx=5, pady=5)

        # Scan for duplicates button
        self.scan_dup_button.grid(row=1, column=1, sticky=tk.E, padx=5, pady=5)

        # Configure grid
        self.manual_dup_frame.columnconfigure(1, weight=1)

        # Duplicate results frame
        self.dup_results_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Duplicate treeview
        self.dup_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.dup_tree_yscroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Handle duplicates button
        self.handle_dup_button.pack(side=tk.BOTTOM, pady=5)

        # Duplicate details frame
        self.dup_details_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.dup_details_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Advanced search tab
        self.search_tab_frame.pack(fill=tk.BOTH, expand=True)

        # Search options frame
        self.search_options_frame.pack(fill=tk.X, pady=5)

        # Search query
        self.adv_search_label.grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.adv_search_entry.grid(
            row=0, column=1, columnspan=3, sticky=tk.EW, padx=5, pady=5)

        # File type filter
        self.file_type_label.grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.file_type_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)

        # Category filter
        self.category_label.grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        self.category_combo.grid(row=1, column=3, sticky=tk.W, padx=5, pady=5)

        # Date range filter
        self.date_range_frame.grid(
            row=2, column=0, columnspan=4, sticky=tk.W, padx=5, pady=5)
        self.date_from_label.pack(side=tk.LEFT, padx=5)
        self.date_from_entry.pack(side=tk.LEFT, padx=5)
        self.date_to_label.pack(side=tk.LEFT, padx=5)
        self.date_to_entry.pack(side=tk.LEFT, padx=5)

        # Search button
        self.adv_search_button.grid(
            row=3, column=3, sticky=tk.E, padx=5, pady=5)

        # Configure grid
        self.search_options_frame.columnconfigure(1, weight=1)
        self.search_options_frame.columnconfigure(3, weight=1)

        # Index management frame
        self.index_frame.pack(fill=tk.X, pady=5)

        # Directory selection
        self.index_dir_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.index_dir_entry.grid(
            row=0, column=1, sticky=tk.EW, padx=5, pady=5)
        self.index_dir_button.grid(row=0, column=2, padx=5, pady=5)

        # Index button
        self.index_button.grid(row=1, column=1, sticky=tk.E, padx=5, pady=5)

        # Configure grid
        self.index_frame.columnconfigure(1, weight=1)

        # Search results frame
        self.search_results_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Search results treeview
        self.search_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.search_tree_yscroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Search result details frame
        self.search_details_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.search_details_text.pack(
            fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Tags tab
        self.tags_frame.pack(fill=tk.BOTH, expand=True)

        # Tag options frame
        self.tag_options_frame.pack(fill=tk.X, pady=5)

        # Enable tagging
        self.apply_tags_check.pack(anchor=tk.W, padx=5, pady=2)

        # Suggest tags
        self.suggest_tags_check.pack(anchor=tk.W, padx=5, pady=2)

        # Tag management frame
        self.tag_management_frame.pack(
            fill=tk.BOTH, expand=True, pady=5, side=tk.LEFT, padx=5)

        # Tag list
        self.tag_list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.tag_list_label.pack(anchor=tk.W, padx=5, pady=2)
        self.tag_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tag_list_yscroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Tag actions
        self.tag_actions_frame.pack(fill=tk.X, pady=5)
        self.add_tag_button.pack(side=tk.LEFT, padx=5)
        self.edit_tag_button.pack(side=tk.LEFT, padx=5)
        self.delete_tag_button.pack(side=tk.LEFT, padx=5)

        # Import/Export tags
        self.tag_io_frame.pack(fill=tk.X, pady=5)
        self.import_tags_button.pack(side=tk.LEFT, padx=5)
        self.export_tags_button.pack(side=tk.LEFT, padx=5)

        # Files by tag
        self.files_by_tag_frame.pack(
            fill=tk.BOTH, expand=True, pady=5, side=tk.LEFT, padx=5)

        # Tag selection
        self.tag_selection_frame.pack(fill=tk.X, pady=5)
        self.tag_selection_label.pack(side=tk.LEFT, padx=5)
        self.tag_selection_combo.pack(side=tk.LEFT, padx=5)
        self.find_files_button.pack(side=tk.LEFT, padx=5)

        # Files with tag
        self.tagged_files_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.tagged_files_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tagged_files_yscroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Bottom frame
        self.bottom_frame.pack(fill=tk.X, pady=5)

        # Status frame
        self.status_frame.pack(fill=tk.X, expand=True)

        # Status label
        self.status_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)

        # Progress bar
        self.progress_bar.grid(
            row=1, column=0, columnspan=3, sticky=tk.EW, padx=5, pady=2)

        # Progress details
        self.progress_details.grid(
            row=2, column=0, sticky=tk.W, padx=5, pady=2)

        # Processed files
        self.processed_label.grid(row=2, column=1, sticky=tk.E, padx=5, pady=2)

        # Total files
        self.total_label.grid(row=2, column=2, sticky=tk.E, padx=5, pady=2)

        # Batch status
        self.batch_status_label.grid(
            row=3, column=0, columnspan=3, sticky=tk.W, padx=5, pady=2)

        # Configure grid
        self.status_frame.columnconfigure(0, weight=2)
        self.status_frame.columnconfigure(1, weight=1)
        self.status_frame.columnconfigure(2, weight=1)

    def browse_source(self):
        """Browse for source directory (Windows style)"""
        # Use standard tkinter dialog (works on all platforms)
        directory = filedialog.askdirectory(
            initialdir=self.source_dir.get(),
            title="Select Source Directory"
        )
        if directory:
            # Convert to OS-appropriate path format
            directory = os.path.normpath(directory)
            self.source_dir.set(directory)

    def browse_target(self):
        """Browse for target directory (Windows style)"""
        # Use standard tkinter dialog (works on all platforms)
        directory = filedialog.askdirectory(
            initialdir=self.target_dir.get(),
            title="Select Target Directory"
        )
        if directory:
            # Convert to OS-appropriate path format
            directory = os.path.normpath(directory)
            self.target_dir.set(directory)

    def start_scan(self):
        """Start the file scanning process in a separate thread"""
        if self.running:
            messagebox.showinfo("Info", "Scanning is already in progress")
            return

        source_dir = self.source_dir.get()
        if not os.path.isdir(source_dir):
            messagebox.showerror(
                "Error", f"Source directory does not exist: {source_dir}")
            return

        # Clear previous results
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.analyzed_files = []
        self.running = True
        self.cancel_requested = False
        self.total_files = 0
        self.processed_files = 0

        # Reset progress indicators
        self.progress_bar.config(mode='indeterminate')
        self.progress_bar.start(10)
        self.progress_details.config(text="Initializing scan...")
        self.processed_label.config(text="Processed: 0")
        self.total_label.config(text="Total: 0")
        self.batch_status_label.config(text="Current Batch: 0/0")

        # Enable cancel button
        self.cancel_button.config(state=tk.NORMAL)

        # Update status
        self.queue.put(("status", "Scanning files..."))

        # Start scanning thread
        scan_thread = threading.Thread(
            target=self.scan_files_thread, args=(source_dir,))
        scan_thread.daemon = True
        scan_thread.start()

    def scan_files_thread(self, directory):
        """Thread function to scan files"""
        try:
            # Get the batch size and delay from the GUI
            batch_size = self.batch_size_var.get()
            batch_delay = self.batch_delay_var.get()

            # Progress callback function
            def progress_callback(processed, total, status_message):
                self.queue.put(("progress", {
                    "processed": processed,
                    "total": total,
                    "status": status_message,
                    "percentage": int((processed / max(1, total)) * 100)
                }))

                # Check for cancellation
                return not self.cancel_requested

            # Scan the directory with progress tracking
            files = self.file_analyzer.scan_directory(
                directory,
                batch_size=batch_size,
                batch_delay=batch_delay,
                callback=progress_callback
            )

            if self.cancel_requested:
                self.queue.put(("cancelled", None))
            else:
                self.queue.put(("files", files))
        except Exception as e:
            logger.error(f"Error scanning directory: {str(e)}")
            self.queue.put(("error", str(e)))
        finally:
            self.queue.put(("complete", None))

    def consume_queue(self):
        """Process messages from the queue"""
        try:
            while True:
                message_type, message = self.queue.get_nowait()

                if message_type == "status":
                    self.status_label.config(text=message)

                elif message_type == "progress":
                    processed = message.get("processed", 0)
                    total = message.get("total", 0)
                    percentage = message.get("percentage", 0)
                    status = message.get("status", "")

                    # Update progress bar
                    self.progress_var.set(percentage)

                    # Update labels
                    self.processed_label.config(text=f"Files: {processed}")
                    self.total_label.config(text=f"Total: {total}")
                    self.progress_details.config(
                        text=f"{status} ({percentage}% complete)")

                    # Calculate current batch
                    batch_size = int(self.batch_size_var.get())
                    current_batch = (processed // batch_size) + 1
                    total_batches = (total + batch_size - 1) // batch_size
                    self.batch_status_label.config(
                        text=f"Batch: {current_batch}/{total_batches}")

                elif message_type == "files":
                    self.analyzed_files = message
                    self.update_file_list(message)

                elif message_type == "error":
                    messagebox.showerror("Error", message)
                    self.running = False
                    self.progress_bar.stop()
                    self.status_label.config(text="Ready")

                elif message_type == "success":
                    messagebox.showinfo("Success", message)

                elif message_type == "cancelled":
                    messagebox.showinfo("Cancelled", "Operation was cancelled")
                    self.cancel_button.config(state=tk.NORMAL)

                elif message_type == "complete":
                    if self.running:
                        self.running = False
                        self.progress_bar.stop()
                        if self.cancel_requested:
                            self.status_label.config(
                                text="Operation cancelled")
                        else:
                            self.status_label.config(
                                text=f"Completed scanning {len(self.analyzed_files)} files")
                    else:
                        # For report generation and other tasks
                        self.progress_bar.stop()
                        self.status_label.config(text="Ready")

                    self.cancel_requested = False

                # New message types for Stage 1 features
                elif message_type == "duplicates":
                    # Store duplicate groups
                    self.duplicate_groups = message

                    # Clear existing items
                    for item in self.dup_tree.get_children():
                        self.dup_tree.delete(item)

                    # Add duplicate groups to the tree
                    total_duplicates = 0
                    total_size = 0

                    for group_id, files in message.items():
                        if len(files) > 1:  # Only show groups with actual duplicates
                            file_count = len(files)
                            # Count duplicates (not the original)
                            total_duplicates += file_count - 1

                            # Calculate size (all files in group have same size)
                            try:
                                size = os.path.getsize(files[0])
                                # Size of duplicates
                                total_size += size * (file_count - 1)
                            except:
                                size = 0

                            # Add to tree
                            self.dup_tree.insert(
                                "",
                                tk.END,
                                values=(
                                    group_id,
                                    f"{file_count} files",
                                    get_readable_size(size)
                                )
                            )

                    # Update status
                    self.status_label.config(
                        text=f"Found {total_duplicates} duplicate files ({get_readable_size(total_size)})"
                    )

                    # Enable handle duplicates button if we found duplicates
                    if total_duplicates > 0:
                        self.handle_dup_button.config(state=tk.NORMAL)
                    else:
                        messagebox.showinfo("Info", "No duplicate files found")

                elif message_type == "duplicate_results":
                    # Show results of duplicate handling
                    total_handled = len(message.get("actions", []))
                    space_saved = message.get("space_savings", 0)

                    messagebox.showinfo(
                        "Duplicate Handling Complete",
                        f"Handled {total_handled} duplicate files\n"
                        f"Space saved: {get_readable_size(space_saved)}"
                    )

                    # Refresh duplicate list
                    self.scan_for_duplicates()

                elif message_type == "search_results":
                    # Store search results
                    self.search_results = message

                    # Clear existing items
                    for item in self.search_tree.get_children():
                        self.search_tree.delete(item)

                    # Add search results to the tree
                    for result in message.get("results", []):
                        self.search_tree.insert(
                            "",
                            tk.END,
                            values=(
                                result.get("id", ""),
                                result.get("filename", ""),
                                result.get("category", ""),
                                result.get("extension", ""),
                                result.get("size_formatted", "")
                            )
                        )

                    # Update status
                    total_results = message.get("total", 0)
                    self.status_label.config(
                        text=f"Found {total_results} results for '{message.get('query', '')}'"
                    )

                    if total_results == 0:
                        messagebox.showinfo("Info", "No results found")

                elif message_type == "index_results":
                    # Show results of indexing
                    indexed = message.get("indexed", 0)
                    updated = message.get("updated", 0)
                    errors = message.get("errors", 0)

                    messagebox.showinfo(
                        "Indexing Complete",
                        f"Indexed {indexed} new files\n"
                        f"Updated {updated} existing files\n"
                        f"Errors: {errors}"
                    )

                self.queue.task_done()

        except queue.Empty:
            # Schedule to check again
            self.root.after(100, self.consume_queue)

    def update_file_list(self, files):
        """Update the file list with scanned files"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Add files to the treeview
        for file in files:
            keywords = ", ".join(file.get("keywords", []))
            size = get_readable_size(file.get("size", 0))

            self.tree.insert("", tk.END, values=(
                file.get("filename", ""),
                file.get("file_type", ""),
                size,
                file.get("category", ""),
                keywords
            ))

    def search_files(self, event=None):
        """Filter files based on search term"""
        search_term = self.search_var.get().lower()

        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Add matching files to the treeview
        for file in self.analyzed_files:
            # Check if search term exists in filename or category or keywords
            filename = file.get("filename", "").lower()
            category = file.get("category", "").lower()
            keywords = ", ".join(file.get("keywords", [])).lower()

            if (search_term in filename or
                search_term in category or
                    search_term in keywords):

                size = get_readable_size(file.get("size", 0))
                keywords_display = ", ".join(file.get("keywords", []))

                self.tree.insert("", tk.END, values=(
                    file.get("filename", ""),
                    file.get("file_type", ""),
                    size,
                    file.get("category", ""),
                    keywords_display
                ))

    def show_file_details(self, event=None):
        """Show details of the selected file"""
        selected_items = self.tree.selection()
        if not selected_items:
            return

        item = selected_items[0]
        filename = self.tree.item(item, "values")[0]

        # Find the file info
        file_info = None
        for file in self.analyzed_files:
            if file.get("filename") == filename:
                file_info = file
                break

        if not file_info:
            return

        # Update details text
        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)

        # Format details
        details = f"Filename: {file_info.get('filename', '')}\n"
        details += f"Type: {file_info.get('file_type', '')}\n"
        details += f"Size: {get_readable_size(file_info.get('size', 0))}\n"
        details += f"Path: {file_info.get('path', '')}\n"
        details += f"Category: {file_info.get('category', '')}\n"
        details += f"Keywords: {', '.join(file_info.get('keywords', []))}\n"

        if 'theme' in file_info:
            details += f"Theme: {file_info.get('theme', '')}\n"

        if 'summary' in file_info:
            details += f"\nSummary:\n{file_info.get('summary', '')}\n"

        if 'metadata' in file_info:
            details += "\nMetadata:\n"
            for key, value in file_info.get('metadata', {}).items():
                details += f"- {key}: {value}\n"

        # Add related documents section if we have enough documents
        if len(self.analyzed_files) > 1:
            details += "\n" + "-" * 40 + "\n"
            details += "Finding related documents...\n"
            self.details_text.insert(tk.END, details)
            self.details_text.config(state=tk.DISABLED)

            # Find related documents in a separate thread to avoid freezing UI
            threading.Thread(target=self.find_related_documents_thread, args=(
                file_info,), daemon=True).start()
        else:
            self.details_text.insert(tk.END, details)
            self.details_text.config(state=tk.DISABLED)

    def find_related_documents_thread(self, file_info):
        """Thread function to find related documents"""
        try:
            # Find similar documents using the AI analyzer
            similar_docs = self.ai_analyzer.find_similar_documents(
                file_info, self.analyzed_files, max_results=3)

            # Update the details text with the results
            self.details_text.config(state=tk.NORMAL)

            # Find where the "Finding related documents..." text starts
            search_text = "Finding related documents..."
            start_pos = "1.0"
            while True:
                pos = self.details_text.search(search_text, start_pos, tk.END)
                if not pos:
                    break
                line = pos.split('.')[0]
                start_pos = f"{line}.0"
                end_pos = f"{int(line) + 1}.0"
                self.details_text.delete(start_pos, end_pos)
                break

            # Add the related documents section
            if similar_docs:
                related_text = "Related Documents:\n\n"
                for i, doc in enumerate(similar_docs):
                    score = doc.get("similarity_score", 0)
                    similarity = "High" if score >= 5 else "Medium" if score >= 3 else "Low"
                    related_text += f"{i+1}. {doc.get('filename', '')}\n"
                    related_text += f"   Category: {doc.get('category', '')}\n"
                    related_text += f"   Similarity: {similarity} (Score: {score})\n"
                    if 'keywords' in doc:
                        related_text += f"   Keywords: {', '.join(doc.get('keywords', []))}\n"
                    related_text += "\n"
            else:
                related_text = "No related documents found.\n"

            # Insert the related documents text
            self.details_text.insert(tk.END, related_text)
            self.details_text.config(state=tk.DISABLED)
        except Exception as e:
            # In case of error, update the text
            self.details_text.config(state=tk.NORMAL)

            # Find where the "Finding related documents..." text starts
            search_text = "Finding related documents..."
            start_pos = "1.0"
            while True:
                pos = self.details_text.search(search_text, start_pos, tk.END)
                if not pos:
                    break
                line = pos.split('.')[0]
                start_pos = f"{line}.0"
                end_pos = f"{int(line) + 1}.0"
                self.details_text.delete(start_pos, end_pos)
                break

            self.details_text.insert(
                tk.END, f"Error finding related documents: {str(e)}\n")
            self.details_text.config(state=tk.DISABLED)
            logger.error(f"Error finding related documents: {str(e)}")

    def organize_files(self):
        """Organize the files based on AI analysis"""
        if not self.analyzed_files:
            messagebox.showinfo(
                "Info", "No files to organize. Please scan files first.")
            return

        target_dir = self.target_dir.get()
        if not os.path.isdir(target_dir):
            try:
                os.makedirs(target_dir)
            except Exception as e:
                messagebox.showerror(
                    "Error", f"Could not create target directory: {str(e)}")
                return

        # Start organizing files
        self.running = True
        self.cancel_requested = False

        # Reset progress indicators
        self.progress_bar.config(mode='indeterminate')
        self.progress_bar.start(10)
        self.status_label.config(text="Organizing files...")
        self.progress_details.config(text="Preparing to organize files...")
        self.processed_label.config(text=f"Files: {len(self.analyzed_files)}")
        self.total_label.config(text="Copying: 0")
        self.batch_status_label.config(text="")

        # Enable cancel button
        self.cancel_button.config(state=tk.NORMAL)

        # Save organization rules to settings
        self.save_organization_rules()

        # Start organization thread
        organize_thread = threading.Thread(
            target=self.organize_files_thread,
            args=(self.analyzed_files, target_dir)
        )
        organize_thread.daemon = True
        organize_thread.start()

    def apply_theme(self):
        """Apply the selected theme and update the UI"""
        theme = self.theme_var.get()
        try:
            # Apply the theme
            self.style.theme_use(theme)

            # Save theme to settings
            if self.settings_manager.set_setting("theme", theme):
                messagebox.showinfo(
                    "Theme Changed", f"Theme changed to: {theme}")
                logger.info(f"Changed theme to: {theme}")
            else:
                messagebox.showwarning(
                    "Warning", "Theme applied but could not be saved as default")
        except Exception as e:
            logger.error(f"Error changing theme: {str(e)}")
            messagebox.showerror("Error", f"Could not apply theme: {str(e)}")

    def save_batch_size(self):
        """Save batch size setting"""
        try:
            batch_size = self.batch_size_var.get()
            if batch_size < 1:
                messagebox.showerror(
                    "Invalid Value", "Batch size must be at least 1")
                return

            self.settings_manager.set_setting("batch_size", batch_size)
            messagebox.showinfo(
                "Settings Saved", f"Batch size set to {batch_size}")
        except Exception as e:
            messagebox.showerror(
                "Error", f"Could not save batch size: {str(e)}")

    def save_batch_delay(self):
        """Save batch delay setting"""
        try:
            batch_delay = self.batch_delay_var.get()
            if batch_delay < 0:
                messagebox.showerror(
                    "Invalid Value", "Batch delay cannot be negative")
                return

            self.settings_manager.set_setting("batch_delay", batch_delay)
            messagebox.showinfo(
                "Settings Saved", f"Batch delay set to {batch_delay} seconds")
        except Exception as e:
            messagebox.showerror(
                "Error", f"Could not save batch delay: {str(e)}")

    def save_directory(self, dir_type):
        """Save the current directory as the default

        Args:
            dir_type: Type of directory ('source' or 'target')
        """
        try:
            if dir_type == "source":
                directory = self.source_dir.get()
                if not directory:
                    messagebox.showwarning(
                        "Warning", "Please select a source directory first")
                    return
                setting_name = "Default source directory"
                setting_key = "last_source_dir"
            elif dir_type == "target":
                directory = self.target_dir.get()
                if not directory:
                    messagebox.showwarning(
                        "Warning", "Please select a target directory first")
                    return
                setting_name = "Default target directory"
                setting_key = "last_target_dir"
            else:
                return

            # Save to settings
            if self.settings_manager.set_setting(setting_key, directory):
                messagebox.showinfo(
                    "Settings Saved", f"{setting_name} set to: {directory}")
                logger.info(f"{setting_name} saved: {directory}")
            else:
                messagebox.showwarning(
                    "Warning", f"Could not save {setting_name}")
        except Exception as e:
            logger.error(f"Error saving directory setting: {str(e)}")
            messagebox.showerror(
                "Error", f"Could not save directory setting: {str(e)}")

    def save_organization_rules(self):
        """Save organization rules to settings"""
        try:
            # Get values from UI
            rules = {
                "create_category_folders": self.create_category_folders_var.get(),
                "generate_summaries": self.generate_summaries_var.get(),
                "include_metadata": self.include_metadata_var.get(),
                "copy_instead_of_move": self.copy_instead_of_move_var.get(),
                # Add Stage 1 options
                "detect_duplicates": self.detect_duplicates_var.get(),
                "duplicate_action": self.duplicate_action_var.get(),
                "duplicate_strategy": self.duplicate_strategy_var.get(),
                "apply_tags": self.apply_tags_var.get(),
                "suggest_tags": self.suggest_tags_var.get()
            }

            # Save to settings
            for key, value in rules.items():
                self.settings_manager.set_setting(key, value)

            logger.info("Organization rules saved")
        except Exception as e:
            logger.error(f"Error saving organization rules: {str(e)}")
            messagebox.showerror(
                "Error", f"Failed to save organization rules: {str(e)}")

    def generate_folder_report(self):
        """Generate a comprehensive report of files in a folder"""
        # Ask user to select a folder
        folder_path = filedialog.askdirectory(
            initialdir=self.target_dir.get(),
            title="Select Folder to Generate Report"
        )

        if not folder_path:
            return

        # Normalize path
        folder_path = os.path.normpath(folder_path)

        if not os.path.isdir(folder_path):
            messagebox.showerror(
                "Error", f"Selected path is not a directory: {folder_path}")
            return

        # Check if there are files in this directory
        has_files = False
        for root, dirs, files in os.walk(folder_path):
            # Skip metadata files for checking
            if any(f for f in files if not f.endswith('.meta.txt') and not f.endswith('_summary.txt') and not f.endswith('_Report.md')):
                has_files = True
                break

        if not has_files:
            messagebox.showwarning(
                "Warning", "No files found in the selected folder. The report may be empty.")
            if not messagebox.askyesno("Continue?", "Continue generating report?"):
                return

        # Ask whether to include summaries
        include_summaries = messagebox.askyesno(
            "Include Summaries",
            "Include detailed content summaries in the report?\n\n" +
            "Including summaries creates a more comprehensive report but makes it larger."
        )

        # Update status
        self.status_label.config(text="Generating folder report...")
        self.progress_bar.config(mode='indeterminate')
        self.progress_bar.start(10)
        self.progress_details.config(
            text=f"Analyzing folder: {os.path.basename(folder_path)}")

        # Run in a thread to avoid freezing the UI
        report_thread = threading.Thread(
            target=self.generate_report_thread,
            args=(folder_path, include_summaries)
        )
        report_thread.daemon = True
        report_thread.start()

    def generate_report_thread(self, folder_path, include_summaries):
        """Thread function to generate a folder report"""
        try:
            # Generate the report
            report_path = self.file_organizer.generate_folder_report(
                folder_path, include_summaries)

            if report_path:
                self.queue.put(
                    ("status", "Report generated successfully"))
                self.queue.put(
                    ("success", f"Report saved to: {report_path}"))

                # Ask if user wants to open the report
                if messagebox.askyesno("Report Generated",
                                       f"Report has been generated at:\n{report_path}\n\nOpen the report now?"):
                    # Use the operating system's default application to open the file
                    import subprocess
                    try:
                        if os.name == 'nt':  # Windows
                            os.startfile(report_path)
                        elif os.name == 'posix':  # macOS or Linux
                            subprocess.call(('xdg-open', report_path))
                    except Exception as e:
                        logger.error(f"Error opening report: {str(e)}")
                        messagebox.showerror(
                            "Error", f"Could not open the report: {str(e)}")
            else:
                self.queue.put(("error", "Failed to generate report"))
        except Exception as e:
            logger.error(f"Error generating folder report: {str(e)}")
            self.queue.put(("error", str(e)))
        finally:
            self.queue.put(("complete", None))

    def _create_settings_widgets(self):
        """Create widgets for the settings tab"""
        # Create a notebook for settings categories
        self.settings_notebook = ttk.Notebook(self.settings_tab)

        # General settings tab
        self.general_settings_tab = ttk.Frame(
            self.settings_notebook, padding=10)
        self.settings_notebook.add(
            self.general_settings_tab, text="General Settings")

        # Directory settings
        self.dir_settings_frame = ttk.LabelFrame(
            self.general_settings_tab, text="Directory Settings", padding=10)

        # Source directory
        self.source_settings_label = ttk.Label(
            self.dir_settings_frame, text="Default Source Directory:")
        self.source_settings_entry = ttk.Entry(
            self.dir_settings_frame, textvariable=self.source_dir, width=40)
        self.source_settings_button = ttk.Button(
            self.dir_settings_frame, text="Browse...",
            command=lambda: self.browse_source(save=True))

        # Target directory
        self.target_settings_label = ttk.Label(
            self.dir_settings_frame, text="Default Target Directory:")
        self.target_settings_entry = ttk.Entry(
            self.dir_settings_frame, textvariable=self.target_dir, width=40)
        self.target_settings_button = ttk.Button(
            self.dir_settings_frame, text="Browse...",
            command=lambda: self.browse_target(save=True))

        # Batch processing settings
        self.batch_settings_frame = ttk.LabelFrame(
            self.general_settings_tab, text="Batch Processing", padding=10)

        # Batch size
        self.batch_size_label = ttk.Label(
            self.batch_settings_frame, text="Batch Size:")
        self.batch_size_entry = ttk.Entry(
            self.batch_settings_frame, textvariable=self.batch_size_var, width=5)
        self.batch_size_button = ttk.Button(
            self.batch_settings_frame, text="Save",
            command=self.save_batch_size)
        self.batch_size_info = ttk.Label(
            self.batch_settings_frame,
            text="Number of files to process in each batch (5-20 recommended)")

        # Batch delay
        self.batch_delay_label = ttk.Label(
            self.batch_settings_frame, text="Batch Delay (seconds):")
        self.batch_delay_entry = ttk.Entry(
            self.batch_settings_frame, textvariable=self.batch_delay_var, width=5)
        self.batch_delay_button = ttk.Button(
            self.batch_settings_frame, text="Save",
            command=self.save_batch_delay)
        self.batch_delay_info = ttk.Label(
            self.batch_settings_frame,
            text="Delay between batches to avoid rate limiting (5-30 recommended)")

        # Logging settings
        self.logging_settings_frame = ttk.LabelFrame(
            self.general_settings_tab, text="Logging Settings", padding=10)

        # Log to file only checkbox
        self.log_to_file_only_check = ttk.Checkbutton(
            self.logging_settings_frame,
            text="Log to file only (no console output)",
            variable=self.log_to_file_only_var,
            command=self.save_logging_settings)

        self.logging_info = ttk.Label(
            self.logging_settings_frame,
            text="Note: This setting will take effect on next application restart")

        # Theme settings
        self.theme_settings_frame = ttk.LabelFrame(
            self.general_settings_tab, text="Theme Settings", padding=10)

        # Theme selection
        self.theme_label = ttk.Label(self.theme_settings_frame, text="Theme:")
        self.theme_combo = ttk.Combobox(
            self.theme_settings_frame, textvariable=self.theme_var)

        # Get available themes
        self.theme_combo['values'] = self.style.theme_names()
        self.theme_combo.bind("<<ComboboxSelected>>",
                              lambda e: self.apply_theme())

        # Organization settings tab
        self.organization_settings_tab = ttk.Frame(
            self.settings_notebook, padding=10)
        self.settings_notebook.add(
            self.organization_settings_tab, text="Organization Settings")

        # Organization rules frame
        self.organization_rules_frame = ttk.LabelFrame(
            self.organization_settings_tab, text="Organization Rules", padding=10)

        # Create category folders
        self.create_folders_check = ttk.Checkbutton(
            self.organization_rules_frame,
            text="Create category folders",
            variable=self.create_category_folders_var,
            command=self.save_organization_rules)

        # Generate summaries
        self.generate_summaries_check = ttk.Checkbutton(
            self.organization_rules_frame,
            text="Generate content summaries",
            variable=self.generate_summaries_var,
            command=self.save_organization_rules)

        # Include metadata
        self.include_metadata_check = ttk.Checkbutton(
            self.organization_rules_frame,
            text="Include metadata files",
            variable=self.include_metadata_var,
            command=self.save_organization_rules)

        # Copy instead of move
        self.copy_instead_check = ttk.Checkbutton(
            self.organization_rules_frame,
            text="Copy files instead of moving them",
            variable=self.copy_instead_of_move_var,
            command=self.save_organization_rules)

    def save_logging_settings(self):
        """Save logging settings to the settings manager"""
        try:
            log_to_file_only = self.log_to_file_only_var.get()
            self.settings_manager.set_setting(
                "log_to_file_only", log_to_file_only)
            self.settings_manager.save_settings()
            logger.info(f"Saved log_to_file_only setting: {log_to_file_only}")
        except Exception as e:
            logger.error(f"Error saving logging settings: {str(e)}")
            messagebox.showerror(
                "Error", f"Could not save logging settings: {str(e)}")

    def organize_files_thread(self, files, target_dir):
        """Thread for organizing files"""
        try:
            # Define progress callback
            def organize_progress_callback(current, total, filename):
                percentage = int((current / total) * 100)
                self.queue.put(("progress", {
                    "processed": current,
                    "total": total,
                    "percentage": percentage,
                    "status": filename
                }))
                # Update organization-specific labels
                self.queue.put(
                    ("status", f"Organizing files ({percentage}%)"))

            # Get organization options from the settings
            organization_options = {
                "create_category_folders": self.create_category_folders_var.get(),
                "generate_summaries": self.generate_summaries_var.get(),
                "include_metadata": self.include_metadata_var.get(),
                "copy_instead_of_move": self.copy_instead_of_move_var.get(),
                # Add Stage 1 options
                "detect_duplicates": self.detect_duplicates_var.get(),
                "duplicate_action": self.duplicate_action_var.get(),
                "duplicate_strategy": self.duplicate_strategy_var.get(),
                "apply_tags": self.apply_tags_var.get(),
                "suggest_tags": self.suggest_tags_var.get()
            }

            # Pass the callback and options to the organizer
            result = self.file_organizer.organize_files(
                files,
                target_dir,
                callback=organize_progress_callback,
                options=organization_options
            )

            if self.cancel_requested:
                self.queue.put(("cancelled", None))
            else:
                # Create success message
                success_msg = f"Successfully organized {result.get('organized_count', 0)} files"

                # Add duplicate information if duplicates were detected
                if organization_options["detect_duplicates"] and "duplicates" in result:
                    dup_result = result["duplicates"]
                    dup_count = dup_result.get("total_duplicates", 0)
                    space_saved = dup_result.get("space_savings", 0)

                    if dup_count > 0:
                        success_msg += f"\nFound {dup_count} duplicate files"
                        success_msg += f"\nSpace savings: {get_readable_size(space_saved)}"

                self.queue.put(("success", success_msg))

        except Exception as e:
            logger.error(f"Error organizing files: {str(e)}")
            self.queue.put(
                ("error", f"Error organizing files: {str(e)}"))
        finally:
            self.running = False
            self.queue.put(("complete", None))

    def cancel_operation(self):
        """Cancel the current operation (scanning or organizing)"""
        if not self.running:
            return

        self.cancel_requested = True
        self.queue.put(("status", "Cancelling operation..."))
        self.progress_details.config(text="Cancelling... Please wait")
        logger.info("User requested cancellation of current operation")

        # Disable the cancel button while cancellation is in progress
        self.cancel_button.config(state=tk.DISABLED)

    # Duplicate detection methods
    def browse_directory(self, string_var):
        """Browse for a directory and update the given StringVar"""
        directory = filedialog.askdirectory()
        if directory:
            string_var.set(directory)

    def scan_for_duplicates(self):
        """Scan for duplicate files in the selected directory"""
        directory = self.dup_dir_var.get()
        if not directory:
            messagebox.showinfo(
                "Info", "Please select a directory to scan for duplicates")
            return

        # Clear existing items
        for item in self.dup_tree.get_children():
            self.dup_tree.delete(item)

        # Update status
        self.status_var.set("Scanning for duplicates...")
        self.progress_var.set(0)
        self.progress_details.config(
            text="Preparing to scan for duplicates...")

        # Start scanning thread
        self.running = True
        self.cancel_requested = False

        scan_thread = threading.Thread(
            target=self.scan_duplicates_thread, args=(directory,))
        scan_thread.daemon = True
        scan_thread.start()

    def scan_duplicates_thread(self, directory):
        """Thread for scanning duplicates"""
        try:
            # Get all files in the directory (including subdirectories)
            file_list = []
            for root, _, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_list.append(file_path)

            # Update status
            self.queue.put(
                ("status", f"Found {len(file_list)} files, checking for duplicates..."))

            # Progress callback function
            def progress_callback(processed, total, status_message):
                self.queue.put(("progress", {
                    "processed": processed,
                    "total": total,
                    "percentage": int((processed / total) * 100) if total > 0 else 0,
                    "status": status_message
                }))

            # Get duplicate detection method and similarity threshold
            method = self.dup_method_var.get()
            similarity_threshold = self.similarity_var.get() if method == "content" else None

            # Find duplicates
            duplicate_groups = self.duplicate_detector.find_duplicates(
                file_list,
                method=method,
                similarity_threshold=similarity_threshold,
                callback=progress_callback
            )

            if self.cancel_requested:
                self.queue.put(("cancelled", None))
            else:
                self.queue.put(("duplicates", duplicate_groups))
        except Exception as e:
            logger.error(f"Error scanning for duplicates: {str(e)}")
            self.queue.put(("error", str(e)))
        finally:
            self.queue.put(("complete", None))

    def show_duplicate_details(self, event=None):
        """Show details of the selected duplicate group"""
        selection = self.dup_tree.selection()
        if not selection:
            return

        item = selection[0]
        group_id = self.dup_tree.item(item, "values")[0]

        # Get duplicate group
        duplicate_groups = getattr(self, "duplicate_groups", {})
        if not duplicate_groups or group_id not in duplicate_groups:
            return

        files = duplicate_groups[group_id]

        # Show details
        details = f"Duplicate Group {group_id}\n"
        details += "=" * 40 + "\n\n"
        details += f"Number of duplicate files: {len(files)}\n\n"

        for i, file_path in enumerate(files, 1):
            file_size = os.path.getsize(file_path)
            file_time = os.path.getmtime(file_path)
            details += f"{i}. {file_path}\n"
            details += f"   Size: {get_readable_size(file_size)}\n"
            details += f"   Modified: {time.ctime(file_time)}\n\n"

        # Update details text
        self.dup_details_text.config(state=tk.NORMAL)
        self.dup_details_text.delete(1.0, tk.END)
        self.dup_details_text.insert(tk.END, details)
        self.dup_details_text.config(state=tk.DISABLED)

    def handle_duplicates(self):
        """Handle duplicate files according to the selected action"""
        duplicate_groups = getattr(self, "duplicate_groups", {})
        if not duplicate_groups:
            messagebox.showinfo("Info", "No duplicates to handle")
            return

        action = self.duplicate_action_var.get()
        keep_strategy = self.duplicate_strategy_var.get()

        if action == "move":
            # Ask for target directory
            target_dir = filedialog.askdirectory(
                title="Select directory for duplicate files")
            if not target_dir:
                return
        else:
            target_dir = None

        # Confirm action
        if action == "delete":
            if not messagebox.askyesno("Confirm", "Are you sure you want to delete duplicate files? This cannot be undone."):
                return

        # Update status
        self.status_var.set(f"Handling duplicates ({action})...")
        self.progress_var.set(0)

        # Start handling thread
        self.running = True
        self.cancel_requested = False

        handle_thread = threading.Thread(
            target=self.handle_duplicates_thread,
            args=(duplicate_groups, action, target_dir, keep_strategy)
        )
        handle_thread.daemon = True
        handle_thread.start()

    def handle_duplicates_thread(self, duplicate_groups, action, target_dir, keep_strategy):
        """Thread for handling duplicates"""
        try:
            # Handle duplicates
            results = self.duplicate_detector.handle_duplicates(
                duplicate_groups,
                action=action,
                target_dir=target_dir,
                keep_strategy=keep_strategy
            )

            if self.cancel_requested:
                self.queue.put(("cancelled", None))
            else:
                self.queue.put(("duplicate_results", results))
        except Exception as e:
            logger.error(f"Error handling duplicates: {str(e)}")
            self.queue.put(("error", str(e)))
        finally:
            self.queue.put(("complete", None))

    # Advanced search methods
    def perform_advanced_search(self):
        """Perform advanced search with filters"""
        query = self.adv_search_var.get()
        if not query:
            messagebox.showinfo("Info", "Please enter a search query")
            return

        # Get filters
        filters = {}

        # File type filter
        file_type = self.file_type_var.get()
        if file_type and file_type != "All":
            if file_type == "PDF":
                filters["file_type"] = ".pdf"
            elif file_type == "Word":
                filters["file_type"] = ".docx"
            elif file_type == "Excel":
                filters["file_type"] = ".xlsx"
            elif file_type == "Text":
                filters["file_type"] = ".txt"
            elif file_type == "HTML":
                filters["file_type"] = ".html"
            elif file_type == "Markdown":
                filters["file_type"] = ".md"

        # Category filter
        category = self.category_var.get()
        if category and category != "All":
            filters["category"] = category

        # Date range filter
        date_from = self.date_from_var.get()
        date_to = self.date_to_var.get()
        if date_from or date_to:
            filters["date_range"] = {}
            if date_from:
                filters["date_range"]["start"] = date_from
            if date_to:
                filters["date_range"]["end"] = date_to

        # Clear existing items
        for item in self.search_tree.get_children():
            self.search_tree.delete(item)

        # Update status
        self.status_var.set("Searching...")
        self.progress_var.set(0)

        # Start search thread
        self.running = True
        self.cancel_requested = False

        search_thread = threading.Thread(
            target=self.search_thread, args=(query, filters))
        search_thread.daemon = True
        search_thread.start()

    def search_thread(self, query, filters):
        """Thread for performing search"""
        try:
            # Perform search
            results = self.search_engine.search(query, filters=filters)

            if self.cancel_requested:
                self.queue.put(("cancelled", None))
            else:
                self.queue.put(("search_results", results))
        except Exception as e:
            logger.error(f"Error searching: {str(e)}")
            self.queue.put(("error", str(e)))
        finally:
            self.queue.put(("complete", None))

    def show_search_result_details(self, event=None):
        """Show details of the selected search result"""
        selection = self.search_tree.selection()
        if not selection:
            return

        item = selection[0]
        file_id = self.search_tree.item(item, "values")[0]

        # Get search result
        search_results = getattr(self, "search_results", {})
        if not search_results or "results" not in search_results:
            return

        result = None
        for r in search_results["results"]:
            if str(r["id"]) == file_id:
                result = r
                break

        if not result:
            return

        # Show details
        details = f"File: {result['filename']}\n"
        details += "=" * 40 + "\n\n"
        details += f"Path: {result['path']}\n"
        details += f"Category: {result['category']}\n"
        details += f"Type: {result['extension']}\n"
        details += f"Size: {result['size_formatted']}\n"
        details += f"Created: {result.get('created_time_formatted', 'Unknown')}\n"
        details += f"Modified: {result.get('modified_time_formatted', 'Unknown')}\n\n"

        # Metadata
        if "metadata" in result and result["metadata"]:
            details += "Metadata:\n"
            details += "-" * 40 + "\n"
            for key, value in result["metadata"].items():
                details += f"{key}: {value}\n"
            details += "\n"

        # Tags
        if "tags" in result and result["tags"]:
            details += "Tags:\n"
            details += "-" * 40 + "\n"
            for tag in result["tags"]:
                details += f"- {tag}\n"
            details += "\n"

        # Update details text
        self.search_details_text.config(state=tk.NORMAL)
        self.search_details_text.delete(1.0, tk.END)
        self.search_details_text.insert(tk.END, details)
        self.search_details_text.config(state=tk.DISABLED)

    def index_files(self):
        """Index files for search"""
        directory = self.index_dir_var.get()
        if not directory:
            messagebox.showinfo("Info", "Please select a directory to index")
            return

        # Update status
        self.status_var.set("Indexing files...")
        self.progress_var.set(0)
        self.progress_details.config(text="Preparing to index files...")

        # Start indexing thread
        self.running = True
        self.cancel_requested = False

        index_thread = threading.Thread(
            target=self.index_files_thread, args=(directory,))
        index_thread.daemon = True
        index_thread.start()

    def index_files_thread(self, directory):
        """Thread for indexing files"""
        try:
            # Scan directory for files
            def progress_callback(processed, total, status_message):
                self.queue.put(("progress", {
                    "processed": processed,
                    "total": total,
                    "percentage": int((processed / total) * 100) if total > 0 else 0,
                    "status": status_message
                }))

            # Scan the directory with progress tracking
            files = self.file_analyzer.scan_directory(
                directory,
                batch_size=int(self.batch_size_var.get()),
                batch_delay=float(self.batch_delay_var.get()),
                callback=progress_callback
            )

            if self.cancel_requested:
                self.queue.put(("cancelled", None))
                return

            # Index the files
            self.queue.put(("status", "Indexing files..."))

            # Index files
            results = self.search_engine.index_files(
                files, callback=progress_callback)

            if self.cancel_requested:
                self.queue.put(("cancelled", None))
            else:
                self.queue.put(("index_results", results))
        except Exception as e:
            logger.error(f"Error indexing files: {str(e)}")
            self.queue.put(("error", str(e)))
        finally:
            self.queue.put(("complete", None))

    # Tag management methods
    def add_tag(self):
        """Add a new tag"""
        # Create a dialog for adding a tag
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Tag")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()

        # Tag name
        name_frame = ttk.Frame(dialog, padding="5")
        name_frame.pack(fill=tk.X, pady=5)
        name_label = ttk.Label(name_frame, text="Tag Name:")
        name_label.pack(side=tk.LEFT, padx=5)
        name_var = tk.StringVar()
        name_entry = ttk.Entry(name_frame, textvariable=name_var, width=30)
        name_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # Tag category
        category_frame = ttk.Frame(dialog, padding="5")
        category_frame.pack(fill=tk.X, pady=5)
        category_label = ttk.Label(category_frame, text="Category:")
        category_label.pack(side=tk.LEFT, padx=5)
        category_var = tk.StringVar()
        category_entry = ttk.Entry(
            category_frame, textvariable=category_var, width=30)
        category_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # Tag color
        color_frame = ttk.Frame(dialog, padding="5")
        color_frame.pack(fill=tk.X, pady=5)
        color_label = ttk.Label(color_frame, text="Color:")
        color_label.pack(side=tk.LEFT, padx=5)
        color_var = tk.StringVar()
        color_entry = ttk.Entry(color_frame, textvariable=color_var, width=10)
        color_entry.pack(side=tk.LEFT, padx=5)
        color_button = ttk.Button(color_frame, text="Choose Color",
                                  command=lambda: self.choose_color(color_var))
        color_button.pack(side=tk.LEFT, padx=5)

        # Tag description
        desc_frame = ttk.Frame(dialog, padding="5")
        desc_frame.pack(fill=tk.X, pady=5)
        desc_label = ttk.Label(desc_frame, text="Description:")
        desc_label.pack(anchor=tk.W, padx=5, pady=2)
        desc_text = tk.Text(desc_frame, width=40, height=5)
        desc_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)

        # Parent tag
        parent_frame = ttk.Frame(dialog, padding="5")
        parent_frame.pack(fill=tk.X, pady=5)
        parent_label = ttk.Label(parent_frame, text="Parent Tag:")
        parent_label.pack(side=tk.LEFT, padx=5)
        parent_var = tk.StringVar()

        # Get all tags for parent selection
        tags = self.tag_manager.get_all_tags()
        tag_names = [""] + [tag["name"] for tag in tags]

        parent_combo = ttk.Combobox(
            parent_frame, textvariable=parent_var, values=tag_names, width=30)
        parent_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # Buttons
        button_frame = ttk.Frame(dialog, padding="5")
        button_frame.pack(fill=tk.X, pady=10)

        def save_tag():
            name = name_var.get()
            if not name:
                messagebox.showerror("Error", "Tag name is required")
                return

            category = category_var.get()
            color = color_var.get()
            description = desc_text.get(1.0, tk.END).strip()
            parent_name = parent_var.get()

            # Create tag
            tag_id = self.tag_manager.create_tag(
                name=name,
                category=category,
                color=color,
                description=description,
                parent_name=parent_name if parent_name else None
            )

            if tag_id:
                messagebox.showinfo(
                    "Success", f"Tag '{name}' created successfully")
                dialog.destroy()
                self.refresh_tag_list()
            else:
                messagebox.showerror("Error", f"Failed to create tag '{name}'")

        save_button = ttk.Button(button_frame, text="Save", command=save_tag)
        save_button.pack(side=tk.RIGHT, padx=5)

        cancel_button = ttk.Button(
            button_frame, text="Cancel", command=dialog.destroy)
        cancel_button.pack(side=tk.RIGHT, padx=5)

    def edit_tag(self):
        """Edit the selected tag"""
        selection = self.tag_list.selection()
        if not selection:
            messagebox.showinfo("Info", "Please select a tag to edit")
            return

        item = selection[0]
        tag_id = self.tag_list.item(item, "values")[0]

        # Get tag details
        tag = self.tag_manager.get_tag_by_id(tag_id)
        if not tag:
            messagebox.showerror("Error", "Failed to get tag details")
            return

        # Create a dialog for editing the tag
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit Tag: {tag['name']}")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()

        # Tag name
        name_frame = ttk.Frame(dialog, padding="5")
        name_frame.pack(fill=tk.X, pady=5)
        name_label = ttk.Label(name_frame, text="Tag Name:")
        name_label.pack(side=tk.LEFT, padx=5)
        name_var = tk.StringVar(value=tag['name'])
        name_entry = ttk.Entry(name_frame, textvariable=name_var, width=30)
        name_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # Tag category
        category_frame = ttk.Frame(dialog, padding="5")
        category_frame.pack(fill=tk.X, pady=5)
        category_label = ttk.Label(category_frame, text="Category:")
        category_label.pack(side=tk.LEFT, padx=5)
        category_var = tk.StringVar(value=tag.get('category', ''))
        category_entry = ttk.Entry(
            category_frame, textvariable=category_var, width=30)
        category_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # Tag color
        color_frame = ttk.Frame(dialog, padding="5")
        color_frame.pack(fill=tk.X, pady=5)
        color_label = ttk.Label(color_frame, text="Color:")
        color_label.pack(side=tk.LEFT, padx=5)
        color_var = tk.StringVar(value=tag.get('color', ''))
        color_entry = ttk.Entry(color_frame, textvariable=color_var, width=10)
        color_entry.pack(side=tk.LEFT, padx=5)
        color_button = ttk.Button(color_frame, text="Choose Color",
                                  command=lambda: self.choose_color(color_var))
        color_button.pack(side=tk.LEFT, padx=5)

        # Tag description
        desc_frame = ttk.Frame(dialog, padding="5")
        desc_frame.pack(fill=tk.X, pady=5)
        desc_label = ttk.Label(desc_frame, text="Description:")
        desc_label.pack(anchor=tk.W, padx=5, pady=2)
        desc_text = tk.Text(desc_frame, width=40, height=5)
        desc_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        if tag.get('description'):
            desc_text.insert(tk.END, tag['description'])

        # Parent tag
        parent_frame = ttk.Frame(dialog, padding="5")
        parent_frame.pack(fill=tk.X, pady=5)
        parent_label = ttk.Label(parent_frame, text="Parent Tag:")
        parent_label.pack(side=tk.LEFT, padx=5)
        parent_var = tk.StringVar(value=tag.get('parent_name', ''))

        # Get all tags for parent selection
        tags = self.tag_manager.get_all_tags()
        tag_names = [""] + [t["name"] for t in tags if t["id"] != tag["id"]]

        parent_combo = ttk.Combobox(
            parent_frame, textvariable=parent_var, values=tag_names, width=30)
        parent_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # Buttons
        button_frame = ttk.Frame(dialog, padding="5")
        button_frame.pack(fill=tk.X, pady=10)

        def save_tag():
            name = name_var.get()
            if not name:
                messagebox.showerror("Error", "Tag name is required")
                return

            category = category_var.get()
            color = color_var.get()
            description = desc_text.get(1.0, tk.END).strip()
            parent_name = parent_var.get()

            # Update tag
            success = self.tag_manager.update_tag(
                tag_id=tag["id"],
                name=name,
                category=category,
                color=color,
                description=description,
                parent_name=parent_name if parent_name else None
            )

            if success:
                messagebox.showinfo(
                    "Success", f"Tag '{name}' updated successfully")
                dialog.destroy()
                self.refresh_tag_list()
            else:
                messagebox.showerror("Error", f"Failed to update tag '{name}'")

        save_button = ttk.Button(button_frame, text="Save", command=save_tag)
        save_button.pack(side=tk.RIGHT, padx=5)

        cancel_button = ttk.Button(
            button_frame, text="Cancel", command=dialog.destroy)
        cancel_button.pack(side=tk.RIGHT, padx=5)

    def delete_tag(self):
        """Delete the selected tag"""
        selection = self.tag_list.selection()
        if not selection:
            messagebox.showinfo("Info", "Please select a tag to delete")
            return

        item = selection[0]
        tag_id = self.tag_list.item(item, "values")[0]
        tag_name = self.tag_list.item(item, "text")

        # Confirm deletion
        if not messagebox.askyesno("Confirm", f"Are you sure you want to delete the tag '{tag_name}'?"):
            return

        # Delete tag
        success = self.tag_manager.delete_tag(tag_id)

        if success:
            messagebox.showinfo(
                "Success", f"Tag '{tag_name}' deleted successfully")
            self.refresh_tag_list()
        else:
            messagebox.showerror("Error", f"Failed to delete tag '{tag_name}'")

    def import_tags(self):
        """Import tags from a JSON file"""
        file_path = filedialog.askopenfilename(
            title="Select Tags JSON File",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )

        if not file_path:
            return

        # Import tags
        results = self.tag_manager.import_tags(file_path)

        if results.get("success", False):
            messagebox.showinfo(
                "Success",
                f"Successfully imported {results.get('imported', 0)} tags. "
                f"Errors: {results.get('errors', 0)}"
            )
            self.refresh_tag_list()
        else:
            messagebox.showerror(
                "Error", f"Failed to import tags: {results.get('error', 'Unknown error')}")

    def export_tags(self):
        """Export tags to a JSON file"""
        file_path = filedialog.asksaveasfilename(
            title="Save Tags JSON File",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )

        if not file_path:
            return

        # Export tags
        success = self.tag_manager.export_tags(file_path)

        if success:
            messagebox.showinfo(
                "Success", f"Tags exported successfully to {file_path}")
        else:
            messagebox.showerror("Error", "Failed to export tags")

    def refresh_tag_list(self):
        """Refresh the tag list"""
        # Clear existing items
        for item in self.tag_list.get_children():
            self.tag_list.delete(item)

        # Get all tags
        tags = self.tag_manager.get_all_tags()

        # Add tags to the list
        for tag in tags:
            self.tag_list.insert(
                "",
                tk.END,
                text=tag["name"],
                values=(tag["id"], tag.get("category", ""),
                        tag.get("file_count", 0))
            )

        # Update tag selection combo
        tag_names = [tag["name"] for tag in tags]
        self.tag_selection_combo["values"] = tag_names

    def find_files_by_tag(self):
        """Find files with the selected tag"""
        tag_name = self.tag_selection_var.get()
        if not tag_name:
            messagebox.showinfo("Info", "Please select a tag")
            return

        # Clear existing items
        for item in self.tagged_files_tree.get_children():
            self.tagged_files_tree.delete(item)

        # Get files with tag
        files = self.tag_manager.get_files_by_tag(tag_name)

        if not files:
            messagebox.showinfo(
                "Info", f"No files found with tag '{tag_name}'")
            return

        # Add files to the tree
        for file_path in files:
            file_type = os.path.splitext(file_path)[1]
            self.tagged_files_tree.insert(
                "", tk.END, values=(file_path, file_type))

    def choose_color(self, color_var):
        """Choose a color for a tag"""
        from tkinter import colorchooser
        color = colorchooser.askcolor()[1]
        if color:
            color_var.set(color)
