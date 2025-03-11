import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import threading
import queue
import time
import logging
from PIL import Image, ImageTk
import traceback

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
from .image_analyzer import ImageAnalyzer
from .organization_rules import OrganizationRuleManager, OrganizationRule

logger = logging.getLogger("AIDocumentOrganizer")


class DocumentOrganizerApp:
    def _resource_path(self, relative_path):
        """Get absolute path to resource, works for dev and for PyInstaller"""
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
            return os.path.join(base_path, '..', relative_path)
        except Exception:
            return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', relative_path)

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
        self.image_analyzer = ImageAnalyzer()
        self.rule_manager = self.file_organizer.rule_manager
        
        # Initialize UI style
        self.style = ttk.Style()

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

        # New options for Stage 2 features
        # Custom rules
        self.use_custom_rules_var = tk.BooleanVar(
            value=self.settings.get("use_custom_rules", False))
        self.rules_file_var = tk.StringVar(
            value=self.settings.get("rules_file", ""))

        # Batch processing
        self.use_process_pool_var = tk.BooleanVar(
            value=self.settings_manager.get_setting("batch_processing.use_process_pool", True))
        self.adaptive_workers_var = tk.BooleanVar(
            value=self.settings_manager.get_setting("batch_processing.adaptive_workers", True))
        self.max_workers_var = tk.StringVar(
            value=str(self.settings_manager.get_setting("batch_processing.max_workers", 4)))
        self.memory_limit_var = tk.StringVar(
            value=str(self.settings_manager.get_setting("batch_processing.memory_limit_percent", 80)))
        self.enable_pause_resume_var = tk.BooleanVar(
            value=self.settings_manager.get_setting("batch_processing.enable_pause_resume", True))
        self.save_job_state_var = tk.BooleanVar(
            value=self.settings_manager.get_setting("batch_processing.save_job_state", True))

        # Image analysis
        self.image_analysis_enabled_var = tk.BooleanVar(
            value=self.settings_manager.get_setting("image_analysis.enabled", True))
        self.extract_exif_var = tk.BooleanVar(
            value=self.settings_manager.get_setting("image_analysis.extract_exif", True))
        self.generate_thumbnails_var = tk.BooleanVar(
            value=self.settings_manager.get_setting("image_analysis.generate_thumbnails", True))
        self.thumbnail_width_var = tk.StringVar(
            value=str(self.settings_manager.get_setting("image_analysis.thumbnail_size", [200, 200])[0]))
        self.thumbnail_height_var = tk.StringVar(
            value=str(self.settings_manager.get_setting("image_analysis.thumbnail_size", [200, 200])[1]))
        self.vision_api_enabled_var = tk.BooleanVar(
            value=self.settings_manager.get_setting("image_analysis.vision_api_enabled", False))
        self.vision_api_provider_var = tk.StringVar(
            value=self.settings_manager.get_setting("image_analysis.vision_api_provider", "google"))
        self.detect_objects_var = tk.BooleanVar(
            value=self.settings_manager.get_setting("image_analysis.detect_objects", True))
        self.detect_faces_var = tk.BooleanVar(
            value=self.settings_manager.get_setting("image_analysis.detect_faces", False))
        self.extract_text_var = tk.BooleanVar(
            value=self.settings_manager.get_setting("image_analysis.extract_text", True))
        self.content_moderation_var = tk.BooleanVar(
            value=self.settings_manager.get_setting("image_analysis.content_moderation", False))

        # Document summarization
        self.summary_length_var = tk.StringVar(
            value=self.settings_manager.get_setting("document_summarization.summary_length", "medium"))
        self.extract_key_points_var = tk.BooleanVar(
            value=self.settings_manager.get_setting("document_summarization.extract_key_points", True))
        self.extract_action_items_var = tk.BooleanVar(
            value=self.settings_manager.get_setting("document_summarization.extract_action_items", True))
        self.generate_executive_summary_var = tk.BooleanVar(
            value=self.settings_manager.get_setting("document_summarization.generate_executive_summary", False))
        self.summary_file_format_var = tk.StringVar(
            value=self.settings_manager.get_setting("document_summarization.summary_file_format", "md"))

        # Current state for rule editing
        self.selected_rule = None
        self.current_job_id = None
        self.is_paused = False

        # Thread control
        self.queue = queue.Queue()
        self.running = False
        self.cancel_requested = False

        # Store analyzed files
        self.analyzed_files = []
        
        # Initialize AI analyzer
        self.ai_analyzer = AIAnalyzer(settings_manager=self.settings_manager)

        # Create widgets
        self._create_widgets()
        self._setup_layout()

        # Apply theme
        self.apply_theme()

        # Set up queue consumer
        self.root.after(100, self.consume_queue)

        logger.info("GUI initialized")

    def _create_widgets(self):
        """Create and setup all widgets"""
        # Create notebook for tabs - will be placed later in layout setup
        self.notebook = ttk.Notebook(self.root)

        # Create main tabs
        self.main_tab = ttk.Frame(self.notebook)
        self.settings_tab = ttk.Frame(self.notebook)
        self.rules_tab = ttk.Frame(self.notebook)
        self.images_tab = ttk.Frame(self.notebook)
        self.batch_tab = ttk.Frame(self.notebook)
        self.ocr_tab = ttk.Frame(self.notebook)
        # Add missing tabs that are referenced later
        self.duplicates_tab = ttk.Frame(self.notebook)
        self.search_tab = ttk.Frame(self.notebook)
        self.tags_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.main_tab, text='Main')
        self.notebook.add(self.settings_tab, text='Settings')
        self.notebook.add(self.rules_tab, text='Rules')
        self.notebook.add(self.images_tab, text='Images')
        self.notebook.add(self.batch_tab, text='Batch')
        self.notebook.add(self.ocr_tab, text='OCR')
        # Add new tabs to notebook
        self.notebook.add(self.duplicates_tab, text='Duplicates')
        self.notebook.add(self.search_tab, text='Search')
        self.notebook.add(self.tags_tab, text='Tags')

        # Create widgets for each tab
        self._create_main_tab()
        self._create_settings_widgets()  # Use the existing method
        self._create_rules_tab()
        self._create_images_tab()
        self._create_batch_tab()
        # Skip OCR tab for now as it's not critical
        # self._create_ocr_tab()

    def _create_main_tab(self):
        """Create the main tab content"""
        # Main frame
        self.main_frame = ttk.Frame(self.main_tab, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Top frame
        self.top_frame = ttk.Frame(self.main_frame, padding="5")
        self.top_frame.pack(fill=tk.X, pady=5)
        
        # Middle frame with notebook
        self.middle_frame = ttk.Frame(self.main_frame, padding="5")
        self.middle_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Bottom frame
        self.bottom_frame = ttk.Frame(self.main_frame, padding="5")
        self.bottom_frame.pack(fill=tk.X, pady=5)
        
        # Create the status frame in the bottom frame - this is the only status frame in the app
        self.status_frame = ttk.LabelFrame(self.bottom_frame, text="Status", padding="5")

        # Directory frame
        self.dir_frame = ttk.LabelFrame(
            self.top_frame, text="Directories", padding="5")
        self.dir_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Source directory
        self.source_label = ttk.Label(self.dir_frame, text="Source Directory:")
        self.source_entry = ttk.Entry(
            self.dir_frame, textvariable=self.source_dir, width=40)
        self.source_button = ttk.Button(
            self.dir_frame, text="Browse...", command=self.browse_source)

        # Target directory
        self.target_label = ttk.Label(self.dir_frame, text="Target Directory:")
        self.target_entry = ttk.Entry(
            self.dir_frame, textvariable=self.target_dir, width=40)
        self.target_button = ttk.Button(
            self.dir_frame, text="Browse...", command=self.browse_target)

        # Create the contents of the new tabs
        self._create_rules_tab()
        self._create_images_tab()
        self._create_batch_tab()

        # Create options frame
        self.options_frame = ttk.LabelFrame(
            self.top_frame, text="Options", padding="5")

        # Batch size options
        self.batch_label = ttk.Label(self.options_frame, text="Batch Size:")
        self.batch_combobox = ttk.Combobox(self.options_frame, textvariable=self.batch_size_var,
                                      values=["5", "10", "20", "50", "100"], width=5)
        self.batch_combobox.current(0)  # Default to 5

        # Action buttons directly in options frame
        # Scan button
        self.scan_button = ttk.Button(
            self.options_frame, text="Scan Files", command=self.start_scan)

        # Organize button
        self.organize_button = ttk.Button(
            self.options_frame, text="Organize Files", command=self.organize_files)

        # Cancel button
        self.cancel_button = ttk.Button(
            self.options_frame, text="Cancel", command=self.cancel_operation)

        # Status frame created elsewhere
        # Removed duplicate frame creation

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
        self.files_frame = ttk.Frame(self.main_tab, padding="5")

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

        # Scan button
        self.scan_button.grid(row=1, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=2)

        # Organize button
        self.organize_button.grid(row=2, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=2)

        # Cancel button
        self.cancel_button.grid(row=3, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=2)

        # Bottom frame
        self.bottom_frame = ttk.Frame(self.main_frame, padding="5")
        self.bottom_frame.pack(fill=tk.X, pady=5)
        
        # Place notebook directly in root
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

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

        # Status frame already created, just ensure it's in the bottom frame
        # We'll set layout properties here but create the frame elsewhere to avoid duplicates

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
        """Consume messages from the queue"""
        try:
            while not self.queue.empty():
                message_type, message = self.queue.get_nowait()

                if message_type == "progress":
                    current, total, status_message = message
                    if total > 0:
                        self.progress_var.set(current / total * 100)
                    else:
                        self.progress_var.set(0)
                    self.status_var.set(status_message)
                    self.status_label.update()

                elif message_type == "update_files":
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

                elif message_type == "paused":
                    messagebox.showinfo("Paused", "Operation was paused")

                elif message_type == "status":
                    self.status_var.set(message)
                    self.status_label.update()

                elif message_type == "update_time":
                    elapsed_str, remaining_str = message
                    self.elapsed_time_var.set(elapsed_str)
                    self.remaining_time_var.set(remaining_str)

                elif message_type == "update_job_list":
                    self.update_job_list()

                elif message_type == "reset_ui":
                    # Reset batch processing UI
                    self.start_batch_button.configure(state="normal")
                    self.pause_batch_button.configure(state="disabled")
                    self.resume_batch_button.configure(state="disabled")
                    self.cancel_batch_button.configure(state="disabled")

                elif message_type == "refresh_images":
                    # Refresh image display if we're on the images tab
                    if hasattr(self, "current_images") and self.current_images:
                        self.display_images(self.current_images)

                elif message_type == "complete":
                    if self.running:
                        self.running = False
                        self.progress_bar.stop()
                        if self.cancel_requested:
                            self.status_label.config(
                                text="Operation cancelled")
                        else:
                            self.status_label.config(text="Ready")
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in queue consumer: {str(e)}")
            logger.error(traceback.format_exc())

        # Schedule next queue check
        if self.root:
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
                "suggest_tags": self.suggest_tags_var.get(),
                # Add Stage 2 options
                "use_custom_rules": self.use_custom_rules_var.get(),
                "rules_file": self.rules_file_var.get(),
                "batch_processing": {
                    "use_process_pool": self.use_process_pool_var.get(),
                    "adaptive_workers": self.adaptive_workers_var.get(),
                    "max_workers": self.max_workers_var.get(),
                    "memory_limit_percent": self.memory_limit_var.get(),
                    "enable_pause_resume": self.enable_pause_resume_var.get(),
                    "save_job_state": self.save_job_state_var.get(),
                },
                "image_analysis": {
                    "enabled": self.image_analysis_enabled_var.get(),
                    "extract_exif": self.extract_exif_var.get(),
                    "generate_thumbnails": self.generate_thumbnails_var.get(),
                    "thumbnail_size": [int(self.thumbnail_width_var.get()), int(self.thumbnail_height_var.get())],
                    "vision_api_enabled": self.vision_api_enabled_var.get(),
                    "vision_api_provider": self.vision_api_provider_var.get(),
                    "detect_objects": self.detect_objects_var.get(),
                    "detect_faces": self.detect_faces_var.get(),
                    "extract_text": self.extract_text_var.get(),
                    "content_moderation": self.content_moderation_var.get(),
                },
                "document_summarization": {
                    "summary_length": self.summary_length_var.get(),
                    "extract_key_points": self.extract_key_points_var.get(),
                    "extract_action_items": self.extract_action_items_var.get(),
                    "generate_executive_summary": self.generate_executive_summary_var.get(),
                    "summary_file_format": self.summary_file_format_var.get(),
                },
            }

            # Save to settings
            for key, value in rules.items():
                self.settings_manager.set_setting(key, value)

            logger.info("Organization rules saved")
        except Exception as e:
            logger.error(f"Error saving organization rules: {str(e)}")
            messagebox.showerror(
                "Error", f"Failed to save organization rules: {str(e)}")
                
    def save_max_workers(self):
        """Save max workers setting"""
        try:
            max_workers = self.max_workers_var.get()
            if max_workers < 1:
                messagebox.showerror(
                    "Invalid Value", "Max workers must be at least 1")
                return

            self.settings_manager.set_setting("batch_processing.max_workers", max_workers)
            messagebox.showinfo(
                "Settings Saved", f"Max workers set to {max_workers}")
        except Exception as e:
            logger.error(f"Error saving max workers setting: {str(e)}")
            messagebox.showerror(
                "Error", f"Could not save max workers setting: {str(e)}")
                
    def save_memory_limit(self):
        """Save memory limit setting"""
        try:
            memory_limit = self.memory_limit_var.get()
            if memory_limit < 1 or memory_limit > 100:
                messagebox.showerror(
                    "Invalid Value", "Memory limit must be between 1 and 100 percent")
                return

            self.settings_manager.set_setting("batch_processing.memory_limit_percent", memory_limit)
            messagebox.showinfo(
                "Settings Saved", f"Memory limit set to {memory_limit}%")
        except Exception as e:
            logger.error(f"Error saving memory limit setting: {str(e)}")
            messagebox.showerror(
                "Error", f"Could not save memory limit setting: {str(e)}")
                
    def save_thumbnail_size(self):
        """Save thumbnail size setting"""
        try:
            width = int(self.thumbnail_width_var.get())
            height = int(self.thumbnail_height_var.get())
            
            if width < 10 or height < 10:
                messagebox.showerror(
                    "Invalid Value", "Thumbnail dimensions must be at least 10px")
                return

            self.settings_manager.set_setting("image_analysis.thumbnail_size", [width, height])
            messagebox.showinfo(
                "Settings Saved", f"Thumbnail size set to {width}×{height}px")
        except ValueError:
            messagebox.showerror(
                "Invalid Input", "Thumbnail dimensions must be numbers")
        except Exception as e:
            logger.error(f"Error saving thumbnail size setting: {str(e)}")
            messagebox.showerror(
                "Error", f"Could not save thumbnail size setting: {str(e)}")
                
    def save_vision_provider(self):
        """Save vision API provider setting"""
        try:
            provider = self.vision_api_provider_var.get()
            self.settings_manager.set_setting("image_analysis.vision_api_provider", provider)
            messagebox.showinfo(
                "Settings Saved", f"Vision API provider set to {provider}")
        except Exception as e:
            logger.error(f"Error saving vision provider setting: {str(e)}")
            messagebox.showerror(
                "Error", f"Could not save vision provider setting: {str(e)}")
                
    def save_summary_length(self):
        """Save summary length setting"""
        try:
            length = self.summary_length_var.get()
            self.settings_manager.set_setting("document_summarization.summary_length", length)
            messagebox.showinfo(
                "Settings Saved", f"Summary length set to {length}")
        except Exception as e:
            logger.error(f"Error saving summary length setting: {str(e)}")
            messagebox.showerror(
                "Error", f"Could not save summary length setting: {str(e)}")
                
    def save_summary_file_format(self):
        """Save summary file format setting"""
        try:
            format = self.summary_file_format_var.get()
            self.settings_manager.set_setting("document_summarization.summary_file_format", format)
            messagebox.showinfo(
                "Settings Saved", f"Summary file format set to {format}")
        except Exception as e:
            logger.error(f"Error saving summary file format setting: {str(e)}")
            messagebox.showerror(
                "Error", f"Could not save summary file format setting: {str(e)}")
                
    def browse_rules_file(self):
        """Browse for a rules file"""
        try:
            file_path = filedialog.askopenfilename(
                title="Select Rules File",
                filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")])
            if file_path:
                self.rules_file_var.set(file_path)
        except Exception as e:
            logger.error(f"Error browsing for rules file: {str(e)}")
            messagebox.showerror(
                "Error", f"Could not open file browser: {str(e)}")

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

        # Custom rules
        self.use_custom_rules_check = ttk.Checkbutton(
            self.organization_rules_frame,
            text="Use custom rules",
            variable=self.use_custom_rules_var,
            command=self.save_organization_rules)

        # Rules file
        self.rules_file_entry = ttk.Entry(
            self.organization_rules_frame, textvariable=self.rules_file_var, width=40)
        self.rules_file_button = ttk.Button(
            self.organization_rules_frame, text="Browse...",
            command=lambda: self.browse_rules_file(save=True))

        # Batch processing
        self.use_process_pool_check = ttk.Checkbutton(
            self.organization_rules_frame,
            text="Use process pool",
            variable=self.use_process_pool_var,
            command=self.save_organization_rules)

        self.adaptive_workers_check = ttk.Checkbutton(
            self.organization_rules_frame,
            text="Adaptive workers",
            variable=self.adaptive_workers_var,
            command=self.save_organization_rules)

        self.max_workers_entry = ttk.Entry(
            self.organization_rules_frame, textvariable=self.max_workers_var, width=5)
        self.max_workers_button = ttk.Button(
            self.organization_rules_frame, text="Save",
            command=self.save_max_workers)
        self.max_workers_info = ttk.Label(
            self.organization_rules_frame,
            text="Number of workers to use (1-10 recommended)")

        self.memory_limit_entry = ttk.Entry(
            self.organization_rules_frame, textvariable=self.memory_limit_var, width=5)
        self.memory_limit_button = ttk.Button(
            self.organization_rules_frame, text="Save",
            command=self.save_memory_limit)
        self.memory_limit_info = ttk.Label(
            self.organization_rules_frame,
            text="Memory limit as a percentage (50-100 recommended)")

        self.enable_pause_resume_check = ttk.Checkbutton(
            self.organization_rules_frame,
            text="Enable pause/resume",
            variable=self.enable_pause_resume_var,
            command=self.save_organization_rules)

        self.save_job_state_check = ttk.Checkbutton(
            self.organization_rules_frame,
            text="Save job state",
            variable=self.save_job_state_var,
            command=self.save_organization_rules)

        # Image analysis
        self.image_analysis_enabled_check = ttk.Checkbutton(
            self.organization_rules_frame,
            text="Enable image analysis",
            variable=self.image_analysis_enabled_var,
            command=self.save_organization_rules)

        self.extract_exif_check = ttk.Checkbutton(
            self.organization_rules_frame,
            text="Extract EXIF data",
            variable=self.extract_exif_var,
            command=self.save_organization_rules)

        self.generate_thumbnails_check = ttk.Checkbutton(
            self.organization_rules_frame,
            text="Generate thumbnails",
            variable=self.generate_thumbnails_var,
            command=self.save_organization_rules)

        self.thumbnail_width_entry = ttk.Entry(
            self.organization_rules_frame, textvariable=self.thumbnail_width_var, width=5)
        self.thumbnail_width_button = ttk.Button(
            self.organization_rules_frame, text="Save",
            command=self.save_thumbnail_size)
        self.thumbnail_width_info = ttk.Label(
            self.organization_rules_frame,
            text="Thumbnail width (pixels, 100-1000 recommended)")

        self.thumbnail_height_entry = ttk.Entry(
            self.organization_rules_frame, textvariable=self.thumbnail_height_var, width=5)
        self.thumbnail_height_button = ttk.Button(
            self.organization_rules_frame, text="Save",
            command=self.save_thumbnail_size)
        self.thumbnail_height_info = ttk.Label(
            self.organization_rules_frame,
            text="Thumbnail height (pixels, 100-1000 recommended)")

        self.vision_api_enabled_check = ttk.Checkbutton(
            self.organization_rules_frame,
            text="Enable Vision API",
            variable=self.vision_api_enabled_var,
            command=self.save_organization_rules)

        self.vision_api_provider_entry = ttk.Entry(
            self.organization_rules_frame, textvariable=self.vision_api_provider_var, width=30)
        self.vision_api_provider_button = ttk.Button(
            self.organization_rules_frame, text="Save",
            command=self.save_vision_provider)
        self.vision_api_provider_info = ttk.Label(
            self.organization_rules_frame,
            text="Provider for Vision API (google, azure, etc.)")

        self.detect_objects_check = ttk.Checkbutton(
            self.organization_rules_frame,
            text="Detect objects",
            variable=self.detect_objects_var,
            command=self.save_organization_rules)

        self.detect_faces_check = ttk.Checkbutton(
            self.organization_rules_frame,
            text="Detect faces",
            variable=self.detect_faces_var,
            command=self.save_organization_rules)

        self.extract_text_check = ttk.Checkbutton(
            self.organization_rules_frame,
            text="Extract text",
            variable=self.extract_text_var,
            command=self.save_organization_rules)

        self.content_moderation_check = ttk.Checkbutton(
            self.organization_rules_frame,
            text="Content moderation",
            variable=self.content_moderation_var,
            command=self.save_organization_rules)

        # Document summarization
        self.summary_length_entry = ttk.Entry(
            self.organization_rules_frame, textvariable=self.summary_length_var, width=5)
        self.summary_length_button = ttk.Button(
            self.organization_rules_frame, text="Save",
            command=self.save_summary_length)
        self.summary_length_info = ttk.Label(
            self.organization_rules_frame,
            text="Summary length (short, medium, long)")

        self.extract_key_points_check = ttk.Checkbutton(
            self.organization_rules_frame,
            text="Extract key points",
            variable=self.extract_key_points_var,
            command=self.save_organization_rules)

        self.extract_action_items_check = ttk.Checkbutton(
            self.organization_rules_frame,
            text="Extract action items",
            variable=self.extract_action_items_var,
            command=self.save_organization_rules)

        self.generate_executive_summary_check = ttk.Checkbutton(
            self.organization_rules_frame,
            text="Generate executive summary",
            variable=self.generate_executive_summary_var,
            command=self.save_organization_rules)

        self.summary_file_format_entry = ttk.Entry(
            self.organization_rules_frame, textvariable=self.summary_file_format_var, width=5)
        self.summary_file_format_button = ttk.Button(
            self.organization_rules_frame, text="Save",
            command=self.save_summary_file_format)
        self.summary_file_format_info = ttk.Label(
            self.organization_rules_frame,
            text="Format for summary files (md, txt, html, etc.)")

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
                "suggest_tags": self.suggest_tags_var.get(),
                # Add Stage 2 options
                "use_custom_rules": self.use_custom_rules_var.get(),
                "rules_file": self.rules_file_var.get(),
                "batch_processing": {
                    "use_process_pool": self.use_process_pool_var.get(),
                    "adaptive_workers": self.adaptive_workers_var.get(),
                    "max_workers": self.max_workers_var.get(),
                    "memory_limit_percent": self.memory_limit_var.get(),
                    "enable_pause_resume": self.enable_pause_resume_var.get(),
                    "save_job_state": self.save_job_state_var.get(),
                },
                "image_analysis": {
                    "enabled": self.image_analysis_enabled_var.get(),
                    "extract_exif": self.extract_exif_var.get(),
                    "generate_thumbnails": self.generate_thumbnails_var.get(),
                    "thumbnail_size": [int(self.thumbnail_width_var.get()), int(self.thumbnail_height_var.get())],
                    "vision_api_enabled": self.vision_api_enabled_var.get(),
                    "vision_api_provider": self.vision_api_provider_var.get(),
                    "detect_objects": self.detect_objects_var.get(),
                    "detect_faces": self.detect_faces_var.get(),
                    "extract_text": self.extract_text_var.get(),
                    "content_moderation": self.content_moderation_var.get(),
                },
                "document_summarization": {
                    "summary_length": self.summary_length_var.get(),
                    "extract_key_points": self.extract_key_points_var.get(),
                    "extract_action_items": self.extract_action_items_var.get(),
                    "generate_executive_summary": self.generate_executive_summary_var.get(),
                    "summary_file_format": self.summary_file_format_var.get(),
                },
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

    def _create_rules_tab(self):
        """Create the organization rules tab"""
        # Main frame
        rules_frame = ttk.Frame(self.rules_tab, padding="10")
        rules_frame.pack(fill="both", expand=True)

        # Split into two panes - left for rule list, right for rule editing
        rules_paned = ttk.PanedWindow(rules_frame, orient=tk.HORIZONTAL)
        rules_paned.pack(fill="both", expand=True)

        # Left pane - Rule list and management
        rule_list_frame = ttk.LabelFrame(
            rules_paned, text="Organization Rules", padding="10")
        rules_paned.add(rule_list_frame, weight=1)

        # Rule list with scrollbar
        rule_list_frame_inner = ttk.Frame(rule_list_frame)
        rule_list_frame_inner.pack(fill="both", expand=True)

        self.rule_list = ttk.Treeview(rule_list_frame_inner, columns=("priority", "type", "enabled"),
                                      show="headings", selectmode="browse")
        self.rule_list.heading("priority", text="Priority")
        self.rule_list.heading("type", text="Type")
        self.rule_list.heading("enabled", text="Enabled")

        self.rule_list.column("priority", width=60, anchor="center")
        self.rule_list.column("type", width=100)
        self.rule_list.column("enabled", width=60, anchor="center")

        # Bind selection event
        self.rule_list.bind("<<TreeviewSelect>>", self.on_rule_select)

        # Scrollbars
        rule_list_vsb = ttk.Scrollbar(
            rule_list_frame_inner, orient="vertical", command=self.rule_list.yview)
        self.rule_list.configure(yscrollcommand=rule_list_vsb.set)

        # Pack rule list and scrollbar
        self.rule_list.pack(side="left", fill="both", expand=True)
        rule_list_vsb.pack(side="right", fill="y")

        # Rule list buttons
        rule_buttons_frame = ttk.Frame(rule_list_frame, padding="5")
        rule_buttons_frame.pack(fill="x", pady=5)

        ttk.Button(rule_buttons_frame, text="Add Rule",
                   command=self.add_rule).pack(side="left", padx=5)
        ttk.Button(rule_buttons_frame, text="Edit Rule",
                   command=self.edit_rule).pack(side="left", padx=5)
        ttk.Button(rule_buttons_frame, text="Delete Rule",
                   command=self.delete_rule).pack(side="left", padx=5)
        ttk.Button(rule_buttons_frame, text="Enable/Disable",
                   command=self.toggle_rule).pack(side="left", padx=5)

        # IO buttons
        rule_io_frame = ttk.Frame(rule_list_frame, padding="5")
        rule_io_frame.pack(fill="x", pady=5)

        ttk.Button(rule_io_frame, text="Import Rules",
                   command=self.import_rules).pack(side="left", padx=5)
        ttk.Button(rule_io_frame, text="Export Rules",
                   command=self.export_rules).pack(side="left", padx=5)

        # Right pane - Rule editing
        self.rule_edit_frame = ttk.LabelFrame(
            rules_paned, text="Rule Editor", padding="10")
        rules_paned.add(self.rule_edit_frame, weight=2)

        # Rule properties
        rule_props_frame = ttk.Frame(self.rule_edit_frame, padding="5")
        rule_props_frame.pack(fill="x", pady=5)

        # Rule name
        ttk.Label(rule_props_frame, text="Rule Name:").grid(
            row=0, column=0, sticky="w", padx=5, pady=5)
        self.rule_name_var = tk.StringVar()
        ttk.Entry(rule_props_frame, textvariable=self.rule_name_var, width=40).grid(
            row=0, column=1, sticky="w", padx=5, pady=5)

        # Rule description
        ttk.Label(rule_props_frame, text="Description:").grid(
            row=1, column=0, sticky="w", padx=5, pady=5)
        self.rule_desc_var = tk.StringVar()
        ttk.Entry(rule_props_frame, textvariable=self.rule_desc_var, width=40).grid(
            row=1, column=1, sticky="w", padx=5, pady=5)

        # Rule priority
        ttk.Label(rule_props_frame, text="Priority:").grid(
            row=2, column=0, sticky="w", padx=5, pady=5)
        self.rule_priority_var = tk.StringVar(value="100")
        ttk.Entry(rule_props_frame, textvariable=self.rule_priority_var, width=10).grid(
            row=2, column=1, sticky="w", padx=5, pady=5)
        ttk.Label(rule_props_frame, text="(Lower number = higher priority)").grid(
            row=2, column=2, sticky="w", padx=5, pady=5)

        # Rule type
        ttk.Label(rule_props_frame, text="Rule Type:").grid(
            row=3, column=0, sticky="w", padx=5, pady=5)
        self.rule_type_var = tk.StringVar(value="File Name Pattern")
        self.rule_types = [
            ("File Name Pattern", "pattern"),
            ("File Content", "content"),
            ("File Metadata", "metadata"),
            ("Date/Time", "date"),
            ("File Tags", "tag"),
            ("AI Analysis", "ai"),
            ("Image Properties", "image")
        ]
        rule_type_combo = ttk.Combobox(rule_props_frame, textvariable=self.rule_type_var,
                                       values=[t[0] for t in self.rule_types], state="readonly", width=20)
        rule_type_combo.grid(row=3, column=1, sticky="w", padx=5, pady=5)
        rule_type_combo.bind("<<ComboboxSelected>>",
                             self.update_rule_condition_frame)

        # Rule condition frame (will be populated based on rule type)
        self.rule_condition_frame = ttk.LabelFrame(
            self.rule_edit_frame, text="Condition", padding="10")
        self.rule_condition_frame.pack(fill="x", pady=10)

        # Placeholder for condition widgets
        self.condition_widgets = []

        # Initial condition widgets
        self.update_rule_condition_frame()

        # Rule action frame
        rule_action_frame = ttk.LabelFrame(
            self.rule_edit_frame, text="Action", padding="10")
        rule_action_frame.pack(fill="x", pady=10)

        # Target path template
        ttk.Label(rule_action_frame, text="Target Path Template:").grid(
            row=0, column=0, sticky="w", padx=5, pady=5)
        self.target_path_var = tk.StringVar()
        ttk.Entry(rule_action_frame, textvariable=self.target_path_var, width=40).grid(
            row=0, column=1, sticky="w", padx=5, pady=5)

        # Path template help
        ttk.Label(rule_action_frame, text="(Use {placeholders} like {year}, {month}, {category}, etc.)").grid(
            row=1, column=0, columnspan=2, sticky="w", padx=5, pady=5)

        # Action options
        self.should_copy_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(rule_action_frame, text="Copy files (instead of moving)",
                        variable=self.should_copy_var).grid(row=2, column=0, sticky="w", padx=5, pady=5)

        self.create_summary_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(rule_action_frame, text="Create summary files",
                        variable=self.create_summary_var).grid(row=2, column=1, sticky="w", padx=5, pady=5)

        # Save/cancel buttons
        rule_button_frame = ttk.Frame(self.rule_edit_frame, padding="5")
        rule_button_frame.pack(fill="x", pady=10)

        ttk.Button(rule_button_frame, text="Save Rule",
                   command=self.save_rule).pack(side="left", padx=5)
        ttk.Button(rule_button_frame, text="Cancel",
                   command=self.cancel_rule_edit).pack(side="left", padx=5)
        ttk.Button(rule_button_frame, text="Test Rule",
                   command=self.test_rule).pack(side="left", padx=5)

        # Populate rule list
        self.populate_rule_list()

        # Instructions
        ttk.Label(rule_button_frame, text="Create and manage rules to automatically organize your files.").pack(
            side="right", padx=5)

    def _create_images_tab(self):
        """Create the images tab"""
        # Main frame
        images_frame = ttk.Frame(self.images_tab, padding="10")
        images_frame.pack(fill="both", expand=True)

        # Split into two panes - top for filters, bottom for image grid
        images_paned = ttk.PanedWindow(images_frame, orient=tk.VERTICAL)
        images_paned.pack(fill="both", expand=True)

        # Top pane - Filters and options
        image_options_frame = ttk.LabelFrame(
            images_paned, text="Image Options", padding="10")
        images_paned.add(image_options_frame, weight=1)

        # Image filter options
        image_filter_frame = ttk.Frame(image_options_frame, padding="5")
        image_filter_frame.pack(fill="x", pady=5)

        # Image search
        ttk.Label(image_filter_frame, text="Search:").grid(
            row=0, column=0, sticky="w", padx=5, pady=5)
        self.image_search_var = tk.StringVar()
        ttk.Entry(image_filter_frame, textvariable=self.image_search_var,
                  width=30).grid(row=0, column=1, sticky="w", padx=5, pady=5)
        ttk.Button(image_filter_frame, text="Search", command=self.search_images).grid(
            row=0, column=2, sticky="w", padx=5, pady=5)

        # Image type filter
        ttk.Label(image_filter_frame, text="Image Type:").grid(
            row=1, column=0, sticky="w", padx=5, pady=5)
        self.image_type_var = tk.StringVar(value="All")
        image_type_combo = ttk.Combobox(image_filter_frame, textvariable=self.image_type_var,
                                        values=["All", "JPG", "PNG",
                                                "GIF", "BMP", "TIFF", "WebP"],
                                        state="readonly", width=15)
        image_type_combo.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        image_type_combo.bind("<<ComboboxSelected>>", self.filter_images)

        # Date range filter
        ttk.Label(image_filter_frame, text="Date Range:").grid(
            row=2, column=0, sticky="w", padx=5, pady=5)
        date_frame = ttk.Frame(image_filter_frame)
        date_frame.grid(row=2, column=1, columnspan=2,
                        sticky="w", padx=5, pady=5)

        self.image_date_from_var = tk.StringVar()
        self.image_date_to_var = tk.StringVar()
        ttk.Label(date_frame, text="From:").pack(side="left", padx=2)
        ttk.Entry(date_frame, textvariable=self.image_date_from_var,
                  width=10).pack(side="left", padx=2)
        ttk.Label(date_frame, text="To:").pack(side="left", padx=2)
        ttk.Entry(date_frame, textvariable=self.image_date_to_var,
                  width=10).pack(side="left", padx=2)
        ttk.Button(date_frame, text="Apply", command=self.filter_images).pack(
            side="left", padx=5)

        # Content filter (for AI-detected content)
        ttk.Label(image_filter_frame, text="Content:").grid(
            row=3, column=0, sticky="w", padx=5, pady=5)
        self.image_content_var = tk.StringVar()
        ttk.Entry(image_filter_frame, textvariable=self.image_content_var,
                  width=30).grid(row=3, column=1, sticky="w", padx=5, pady=5)
        ttk.Button(image_filter_frame, text="Filter", command=self.filter_images).grid(
            row=3, column=2, sticky="w", padx=5, pady=5)

        # View options
        image_view_frame = ttk.LabelFrame(
            image_options_frame, text="View Options", padding="5")
        image_view_frame.pack(fill="x", pady=5)

        # Thumbnail size
        ttk.Label(image_view_frame, text="Thumbnail Size:").grid(
            row=0, column=0, sticky="w", padx=5, pady=5)
        self.thumbnail_size_var = tk.StringVar(value="Medium")
        thumbnail_size_combo = ttk.Combobox(image_view_frame, textvariable=self.thumbnail_size_var,
                                            values=[
                                                "Small", "Medium", "Large"],
                                            state="readonly", width=10)
        thumbnail_size_combo.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        thumbnail_size_combo.bind(
            "<<ComboboxSelected>>", self.update_thumbnail_size)

        # Sort order
        ttk.Label(image_view_frame, text="Sort By:").grid(
            row=0, column=2, sticky="w", padx=5, pady=5)
        self.image_sort_var = tk.StringVar(value="Date (Newest)")
        image_sort_combo = ttk.Combobox(image_view_frame, textvariable=self.image_sort_var,
                                        values=[
                                            "Date (Newest)", "Date (Oldest)", "Name", "Size"],
                                        state="readonly", width=15)
        image_sort_combo.grid(row=0, column=3, sticky="w", padx=5, pady=5)
        image_sort_combo.bind("<<ComboboxSelected>>", self.sort_images)

        # Bottom pane - Image grid
        image_grid_frame = ttk.LabelFrame(
            images_paned, text="Images", padding="10")
        images_paned.add(image_grid_frame, weight=3)

        # Create a canvas with scrollbars for the image grid
        image_canvas_frame = ttk.Frame(image_grid_frame)
        image_canvas_frame.pack(fill="both", expand=True)

        self.image_canvas = tk.Canvas(image_canvas_frame)
        self.image_canvas.pack(side="left", fill="both", expand=True)

        image_vsb = ttk.Scrollbar(
            image_canvas_frame, orient="vertical", command=self.image_canvas.yview)
        image_vsb.pack(side="right", fill="y")
        self.image_canvas.configure(yscrollcommand=image_vsb.set)

        image_hsb = ttk.Scrollbar(
            image_grid_frame, orient="horizontal", command=self.image_canvas.xview)
        image_hsb.pack(side="bottom", fill="x")
        self.image_canvas.configure(xscrollcommand=image_hsb.set)

        # Frame to hold the image grid (inside canvas)
        self.image_grid = ttk.Frame(self.image_canvas)
        self.image_canvas.create_window(
            (0, 0), window=self.image_grid, anchor='nw')

        # Bind canvas configure event to update scroll region
        self.image_grid.bind("<Configure>", lambda e: self.image_canvas.configure(
            scrollregion=self.image_canvas.bbox("all")))

        # Status and actions at the bottom
        image_status_frame = ttk.Frame(images_frame, padding="5")
        image_status_frame.pack(fill="x", side="bottom", pady=5)

        self.image_count_var = tk.StringVar(value="0 images found")
        ttk.Label(image_status_frame, textvariable=self.image_count_var).pack(
            side="left", padx=5)

        ttk.Button(image_status_frame, text="Analyze Selected",
                   command=self.analyze_selected_images).pack(side="right", padx=5)
        ttk.Button(image_status_frame, text="Organize Selected",
                   command=self.organize_selected_images).pack(side="right", padx=5)

        # Store image references to prevent garbage collection
        self.image_references = []
        self.selected_images = []

    def _create_batch_tab(self):
        """Create the batch processing tab"""
        # Main frame
        batch_frame = ttk.Frame(self.batch_tab, padding="10")
        batch_frame.pack(fill="both", expand=True)

        # Split into top (control) and bottom (jobs) sections
        batch_paned = ttk.PanedWindow(batch_frame, orient=tk.VERTICAL)
        batch_paned.pack(fill="both", expand=True)

        # Top pane - Batch processing controls
        batch_control_frame = ttk.LabelFrame(
            batch_paned, text="Batch Processing Control", padding="10")
        batch_paned.add(batch_control_frame, weight=1)

        # Batch processing settings
        batch_settings_frame = ttk.Frame(batch_control_frame, padding="5")
        batch_settings_frame.pack(fill="x", pady=5)

        # Source directory
        ttk.Label(batch_settings_frame, text="Source Directory:").grid(
            row=0, column=0, sticky="w", padx=5, pady=5)
        self.batch_source_var = tk.StringVar(value=self.source_dir.get())
        ttk.Entry(batch_settings_frame, textvariable=self.batch_source_var,
                  width=40).grid(row=0, column=1, sticky="w", padx=5, pady=5)
        ttk.Button(batch_settings_frame, text="Browse...", command=self.browse_batch_source).grid(
            row=0, column=2, sticky="w", padx=5, pady=5)

        # Target directory
        ttk.Label(batch_settings_frame, text="Target Directory:").grid(
            row=1, column=0, sticky="w", padx=5, pady=5)
        self.batch_target_var = tk.StringVar(value=self.target_dir.get())
        ttk.Entry(batch_settings_frame, textvariable=self.batch_target_var,
                  width=40).grid(row=1, column=1, sticky="w", padx=5, pady=5)
        ttk.Button(batch_settings_frame, text="Browse...", command=self.browse_batch_target).grid(
            row=1, column=2, sticky="w", padx=5, pady=5)

        # Batch size
        ttk.Label(batch_settings_frame, text="Batch Size:").grid(
            row=2, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(batch_settings_frame, textvariable=self.batch_size_var,
                  width=10).grid(row=2, column=1, sticky="w", padx=5, pady=5)

        # Batch delay
        ttk.Label(batch_settings_frame, text="Batch Delay (seconds):").grid(
            row=3, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(batch_settings_frame, textvariable=self.batch_delay_var,
                  width=10).grid(row=3, column=1, sticky="w", padx=5, pady=5)

        # Process pool
        ttk.Checkbutton(batch_settings_frame, text="Use Process Pool",
                        variable=self.use_process_pool_var).grid(row=4, column=0, sticky="w", padx=5, pady=5)

        # Adaptive workers
        ttk.Checkbutton(batch_settings_frame, text="Adaptive Worker Count",
                        variable=self.adaptive_workers_var).grid(row=4, column=1, sticky="w", padx=5, pady=5)

        # Max workers
        ttk.Label(batch_settings_frame, text="Max Workers:").grid(
            row=5, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(batch_settings_frame, textvariable=self.max_workers_var,
                  width=10).grid(row=5, column=1, sticky="w", padx=5, pady=5)

        # Memory limit
        ttk.Label(batch_settings_frame, text="Memory Limit (%):").grid(
            row=6, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(batch_settings_frame, textvariable=self.memory_limit_var,
                  width=10).grid(row=6, column=1, sticky="w", padx=5, pady=5)

        # Pause/Resume
        ttk.Checkbutton(batch_settings_frame, text="Enable Pause/Resume",
                        variable=self.enable_pause_resume_var).grid(row=7, column=0, sticky="w", padx=5, pady=5)

        # Save job state
        ttk.Checkbutton(batch_settings_frame, text="Save Job State",
                        variable=self.save_job_state_var).grid(row=7, column=1, sticky="w", padx=5, pady=5)

        # Action buttons
        batch_action_frame = ttk.Frame(batch_control_frame, padding="5")
        batch_action_frame.pack(fill="x", pady=5)

        self.start_batch_button = ttk.Button(
            batch_action_frame, text="Start Batch", command=self.start_batch)
        self.start_batch_button.pack(side="left", padx=5)

        self.pause_batch_button = ttk.Button(
            batch_action_frame, text="Pause", command=self.pause_batch)
        self.pause_batch_button.pack(side="left", padx=5)
        self.pause_batch_button.configure(state="disabled")

        self.resume_batch_button = ttk.Button(
            batch_action_frame, text="Resume", command=self.resume_batch)
        self.resume_batch_button.pack(side="left", padx=5)
        self.resume_batch_button.configure(state="disabled")

        self.cancel_batch_button = ttk.Button(
            batch_action_frame, text="Cancel", command=self.cancel_batch)
        self.cancel_batch_button.pack(side="left", padx=5)
        self.cancel_batch_button.configure(state="disabled")

        # Progress frame
        batch_progress_frame = ttk.LabelFrame(
            batch_control_frame, text="Progress", padding="10")
        batch_progress_frame.pack(fill="x", pady=5)

        # Overall progress
        ttk.Label(batch_progress_frame, text="Overall Progress:").grid(
            row=0, column=0, sticky="w", padx=5, pady=5)
        self.batch_progress = ttk.Progressbar(
            batch_progress_frame, variable=self.progress_var, length=400)
        self.batch_progress.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        # Status message
        ttk.Label(batch_progress_frame, text="Status:").grid(
            row=1, column=0, sticky="w", padx=5, pady=5)
        self.batch_status_var = tk.StringVar(value="Ready")
        ttk.Label(batch_progress_frame, textvariable=self.batch_status_var).grid(
            row=1, column=1, sticky="w", padx=5, pady=5)

        # Resource usage
        ttk.Label(batch_progress_frame, text="CPU Usage:").grid(
            row=2, column=0, sticky="w", padx=5, pady=5)
        self.cpu_usage_var = tk.StringVar(value="0%")
        ttk.Label(batch_progress_frame, textvariable=self.cpu_usage_var).grid(
            row=2, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(batch_progress_frame, text="Memory Usage:").grid(
            row=3, column=0, sticky="w", padx=5, pady=5)
        self.memory_usage_var = tk.StringVar(value="0%")
        ttk.Label(batch_progress_frame, textvariable=self.memory_usage_var).grid(
            row=3, column=1, sticky="w", padx=5, pady=5)

        # Time estimates
        ttk.Label(batch_progress_frame, text="Elapsed Time:").grid(
            row=4, column=0, sticky="w", padx=5, pady=5)
        self.elapsed_time_var = tk.StringVar(value="00:00:00")
        ttk.Label(batch_progress_frame, textvariable=self.elapsed_time_var).grid(
            row=4, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(batch_progress_frame, text="Estimated Time Remaining:").grid(
            row=5, column=0, sticky="w", padx=5, pady=5)
        self.remaining_time_var = tk.StringVar(value="00:00:00")
        ttk.Label(batch_progress_frame, textvariable=self.remaining_time_var).grid(
            row=5, column=1, sticky="w", padx=5, pady=5)

        # Bottom pane - Job history
        job_history_frame = ttk.LabelFrame(
            batch_paned, text="Job History", padding="10")
        batch_paned.add(job_history_frame, weight=1)

        # Job history list with scrollbar
        job_history_frame_inner = ttk.Frame(job_history_frame)
        job_history_frame_inner.pack(fill="both", expand=True)

        self.job_list = ttk.Treeview(job_history_frame_inner,
                                     columns=("start_time", "status",
                                              "files", "progress"),
                                     show="headings", selectmode="browse")
        self.job_list.heading("start_time", text="Start Time")
        self.job_list.heading("status", text="Status")
        self.job_list.heading("files", text="Files")
        self.job_list.heading("progress", text="Progress")

        self.job_list.column("start_time", width=150)
        self.job_list.column("status", width=100)
        self.job_list.column("files", width=100)
        self.job_list.column("progress", width=100)

        # Scrollbars
        job_list_vsb = ttk.Scrollbar(
            job_history_frame_inner, orient="vertical", command=self.job_list.yview)
        self.job_list.configure(yscrollcommand=job_list_vsb.set)

        # Pack job list and scrollbar
        self.job_list.pack(side="left", fill="both", expand=True)
        job_list_vsb.pack(side="right", fill="y")

        # Job actions
        job_actions_frame = ttk.Frame(job_history_frame, padding="5")
        job_actions_frame.pack(fill="x", pady=5)

        ttk.Button(job_actions_frame, text="Resume Selected Job",
                   command=self.resume_selected_job).pack(side="left", padx=5)
        ttk.Button(job_actions_frame, text="View Details",
                   command=self.view_job_details).pack(side="left", padx=5)
        ttk.Button(job_actions_frame, text="Clear Completed",
                   command=self.clear_completed_jobs).pack(side="left", padx=5)

        # Initialize job list
        self.update_job_list()

    # Rule management methods
    def populate_rule_list(self):
        """Populate the rule list with rules from the rule manager"""
        # Clear existing items
        for item in self.rule_list.get_children():
            self.rule_list.delete(item)

        # Get all rules
        rules = self.rule_manager.get_all_rules()

        # Add rules to the list
        for rule in rules:
            rule_type = "Unknown"
            for display_name, type_code in self.rule_types:
                if rule.rule_type == type_code:
                    rule_type = display_name
                    break

            enabled = "Yes" if rule.enabled else "No"
            self.rule_list.insert("", "end", iid=rule.rule_id,
                                  values=(rule.priority, rule_type, enabled))

    def on_rule_select(self, event):
        """Handle rule selection in the rule list"""
        selected_items = self.rule_list.selection()
        if not selected_items:
            return

        rule_id = selected_items[0]
        rule = self.rule_manager.get_rule(rule_id)
        if not rule:
            return

        # Store the selected rule
        self.selected_rule = rule

        # Update the rule editor fields
        self.rule_name_var.set(rule.name)
        self.rule_desc_var.set(rule.description)
        self.rule_priority_var.set(str(rule.priority))

        # Set rule type
        rule_type_display = "File Name Pattern"
        for display_name, type_code in self.rule_types:
            if rule.rule_type == type_code:
                rule_type_display = display_name
                break
        self.rule_type_var.set(rule_type_display)

        # Update condition frame
        self.update_rule_condition_frame()

        # Set action values
        self.target_path_var.set(rule.target_path_template)
        self.should_copy_var.set(rule.should_copy)
        self.create_summary_var.set(rule.create_summary)

    def update_rule_condition_frame(self, event=None):
        """Update the condition frame based on the selected rule type"""
        # Clear existing widgets
        for widget in self.condition_widgets:
            widget.destroy()
        self.condition_widgets = []

        # Get the selected rule type
        rule_type_display = self.rule_type_var.get()
        rule_type = "pattern"  # Default
        for display_name, type_code in self.rule_types:
            if display_name == rule_type_display:
                rule_type = type_code
                break

        # Create condition widgets based on rule type
        if rule_type == "pattern":
            # File name pattern condition
            label = ttk.Label(self.rule_condition_frame,
                              text="File Name Pattern:")
            label.grid(row=0, column=0, sticky="w", padx=5, pady=5)
            self.condition_widgets.append(label)

            self.pattern_var = tk.StringVar()
            entry = ttk.Entry(self.rule_condition_frame,
                              textvariable=self.pattern_var, width=40)
            entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)
            self.condition_widgets.append(entry)

            help_label = ttk.Label(
                self.rule_condition_frame, text="(Use regular expressions, e.g. .*\\.pdf for PDF files)")
            help_label.grid(row=1, column=0, columnspan=2,
                            sticky="w", padx=5, pady=5)
            self.condition_widgets.append(help_label)

            self.case_sensitive_var = tk.BooleanVar(value=False)
            check = ttk.Checkbutton(
                self.rule_condition_frame, text="Case sensitive", variable=self.case_sensitive_var)
            check.grid(row=2, column=0, sticky="w", padx=5, pady=5)
            self.condition_widgets.append(check)

        elif rule_type == "content":
            # File content condition
            label = ttk.Label(self.rule_condition_frame,
                              text="Content Contains:")
            label.grid(row=0, column=0, sticky="w", padx=5, pady=5)
            self.condition_widgets.append(label)

            self.content_var = tk.StringVar()
            entry = ttk.Entry(self.rule_condition_frame,
                              textvariable=self.content_var, width=40)
            entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)
            self.condition_widgets.append(entry)

            self.case_sensitive_var = tk.BooleanVar(value=False)
            check = ttk.Checkbutton(
                self.rule_condition_frame, text="Case sensitive", variable=self.case_sensitive_var)
            check.grid(row=1, column=0, sticky="w", padx=5, pady=5)
            self.condition_widgets.append(check)

        elif rule_type == "metadata":
            # Metadata condition
            label = ttk.Label(self.rule_condition_frame,
                              text="Metadata Field:")
            label.grid(row=0, column=0, sticky="w", padx=5, pady=5)
            self.condition_widgets.append(label)

            self.metadata_field_var = tk.StringVar()
            metadata_fields = ["file_type", "file_size", "created_time", "modified_time",
                               "author", "title", "subject", "keywords", "page_count"]
            combo = ttk.Combobox(self.rule_condition_frame, textvariable=self.metadata_field_var,
                                 values=metadata_fields, width=20)
            combo.grid(row=0, column=1, sticky="w", padx=5, pady=5)
            self.condition_widgets.append(combo)

            label = ttk.Label(self.rule_condition_frame, text="Value:")
            label.grid(row=1, column=0, sticky="w", padx=5, pady=5)
            self.condition_widgets.append(label)

            self.metadata_value_var = tk.StringVar()
            entry = ttk.Entry(self.rule_condition_frame,
                              textvariable=self.metadata_value_var, width=40)
            entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)
            self.condition_widgets.append(entry)

        elif rule_type == "date":
            # Date condition
            label = ttk.Label(self.rule_condition_frame, text="Date Field:")
            label.grid(row=0, column=0, sticky="w", padx=5, pady=5)
            self.condition_widgets.append(label)

            self.date_field_var = tk.StringVar(value="modified_time")
            date_fields = ["created_time",
                           "modified_time", "date_time_original"]
            combo = ttk.Combobox(self.rule_condition_frame, textvariable=self.date_field_var,
                                 values=date_fields, width=20)
            combo.grid(row=0, column=1, sticky="w", padx=5, pady=5)
            self.condition_widgets.append(combo)

            label = ttk.Label(self.rule_condition_frame, text="Start Date:")
            label.grid(row=1, column=0, sticky="w", padx=5, pady=5)
            self.condition_widgets.append(label)

            self.start_date_var = tk.StringVar()
            entry = ttk.Entry(self.rule_condition_frame,
                              textvariable=self.start_date_var, width=20)
            entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)
            self.condition_widgets.append(entry)

            label = ttk.Label(self.rule_condition_frame, text="End Date:")
            label.grid(row=2, column=0, sticky="w", padx=5, pady=5)
            self.condition_widgets.append(label)

            self.end_date_var = tk.StringVar()
            entry = ttk.Entry(self.rule_condition_frame,
                              textvariable=self.end_date_var, width=20)
            entry.grid(row=2, column=1, sticky="w", padx=5, pady=5)
            self.condition_widgets.append(entry)

            help_label = ttk.Label(
                self.rule_condition_frame, text="(Format: YYYY-MM-DD)")
            help_label.grid(row=3, column=0, columnspan=2,
                            sticky="w", padx=5, pady=5)
            self.condition_widgets.append(help_label)

        elif rule_type == "tag":
            # Tag condition
            label = ttk.Label(self.rule_condition_frame, text="Tag Name:")
            label.grid(row=0, column=0, sticky="w", padx=5, pady=5)
            self.condition_widgets.append(label)

            self.tag_var = tk.StringVar()
            entry = ttk.Entry(self.rule_condition_frame,
                              textvariable=self.tag_var, width=40)
            entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)
            self.condition_widgets.append(entry)

        elif rule_type == "ai":
            # AI analysis condition
            label = ttk.Label(self.rule_condition_frame, text="AI Field:")
            label.grid(row=0, column=0, sticky="w", padx=5, pady=5)
            self.condition_widgets.append(label)

            self.ai_field_var = tk.StringVar(value="category")
            ai_fields = ["category", "summary", "sentiment", "key_points"]
            combo = ttk.Combobox(self.rule_condition_frame, textvariable=self.ai_field_var,
                                 values=ai_fields, width=20)
            combo.grid(row=0, column=1, sticky="w", padx=5, pady=5)
            self.condition_widgets.append(combo)

            label = ttk.Label(self.rule_condition_frame, text="Value:")
            label.grid(row=1, column=0, sticky="w", padx=5, pady=5)
            self.condition_widgets.append(label)

            self.ai_value_var = tk.StringVar()
            entry = ttk.Entry(self.rule_condition_frame,
                              textvariable=self.ai_value_var, width=40)
            entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)
            self.condition_widgets.append(entry)

        elif rule_type == "image":
            # Image condition
            label = ttk.Label(self.rule_condition_frame, text="Image Field:")
            label.grid(row=0, column=0, sticky="w", padx=5, pady=5)
            self.condition_widgets.append(label)

            self.image_field_var = tk.StringVar(value="dimensions")
            image_fields = ["dimensions", "format", "has_transparency", "is_animated",
                            "camera_make", "camera_model", "labels", "objects"]
            combo = ttk.Combobox(self.rule_condition_frame, textvariable=self.image_field_var,
                                 values=image_fields, width=20)
            combo.grid(row=0, column=1, sticky="w", padx=5, pady=5)
            self.condition_widgets.append(combo)

            label = ttk.Label(self.rule_condition_frame, text="Value:")
            label.grid(row=1, column=0, sticky="w", padx=5, pady=5)
            self.condition_widgets.append(label)

            self.image_value_var = tk.StringVar()
            entry = ttk.Entry(self.rule_condition_frame,
                              textvariable=self.image_value_var, width=40)
            entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)
            self.condition_widgets.append(entry)

    def add_rule(self):
        """Add a new rule"""
        # Clear the editor
        self.selected_rule = None
        self.rule_name_var.set("New Rule")
        self.rule_desc_var.set("")
        self.rule_priority_var.set("100")
        self.rule_type_var.set("File Name Pattern")
        self.target_path_var.set("{file_type}/{file_name}")
        self.should_copy_var.set(True)
        self.create_summary_var.set(False)

        # Update condition frame
        self.update_rule_condition_frame()

    def edit_rule(self):
        """Edit the selected rule"""
        selected_items = self.rule_list.selection()
        if not selected_items:
            messagebox.showinfo("Edit Rule", "Please select a rule to edit")
            return

        # Rule is already loaded in the editor from on_rule_select

    def delete_rule(self):
        """Delete the selected rule"""
        selected_items = self.rule_list.selection()
        if not selected_items:
            messagebox.showinfo(
                "Delete Rule", "Please select a rule to delete")
            return

        rule_id = selected_items[0]
        if messagebox.askyesno("Delete Rule", "Are you sure you want to delete this rule?"):
            if self.rule_manager.delete_rule(rule_id):
                self.populate_rule_list()
                messagebox.showinfo("Delete Rule", "Rule deleted successfully")
            else:
                messagebox.showerror("Delete Rule", "Failed to delete rule")

    def toggle_rule(self):
        """Toggle the enabled state of the selected rule"""
        selected_items = self.rule_list.selection()
        if not selected_items:
            messagebox.showinfo(
                "Toggle Rule", "Please select a rule to toggle")
            return

        rule_id = selected_items[0]
        rule = self.rule_manager.get_rule(rule_id)
        if rule:
            rule.enabled = not rule.enabled
            if self.rule_manager.update_rule(rule):
                self.populate_rule_list()
            else:
                messagebox.showerror("Toggle Rule", "Failed to update rule")

    def save_rule(self):
        """Save the current rule"""
        # Validate inputs
        try:
            priority = int(self.rule_priority_var.get())
            if priority < 1 or priority > 1000:
                messagebox.showerror(
                    "Save Rule", "Priority must be between 1 and 1000")
                return
        except ValueError:
            messagebox.showerror("Save Rule", "Priority must be a number")
            return

        if not self.rule_name_var.get().strip():
            messagebox.showerror("Save Rule", "Rule name cannot be empty")
            return

        if not self.target_path_var.get().strip():
            messagebox.showerror(
                "Save Rule", "Target path template cannot be empty")
            return

        # Get rule type
        rule_type_display = self.rule_type_var.get()
        rule_type = "pattern"  # Default
        for display_name, type_code in self.rule_types:
            if display_name == rule_type_display:
                rule_type = type_code
                break

        # Create or update rule
        if self.selected_rule:
            # Update existing rule
            rule = self.selected_rule
            rule.name = self.rule_name_var.get()
            rule.description = self.rule_desc_var.get()
            rule.priority = priority
            rule.rule_type = rule_type
            rule.target_path_template = self.target_path_var.get()
            rule.should_copy = self.should_copy_var.get()
            rule.create_summary = self.create_summary_var.get()
        else:
            # Create new rule
            rule = self.rule_manager.create_rule_template("default")
            rule.name = self.rule_name_var.get()
            rule.description = self.rule_desc_var.get()
            rule.priority = priority
            rule.rule_type = rule_type
            rule.target_path_template = self.target_path_var.get()
            rule.should_copy = self.should_copy_var.get()
            rule.create_summary = self.create_summary_var.get()

        # Set condition based on rule type
        if rule_type == "pattern":
            rule.set_name_pattern_condition(
                self.pattern_var.get(),
                operator=rule.OP_REGEX,
                case_sensitive=self.case_sensitive_var.get()
            )
        elif rule_type == "content":
            rule.set_content_condition(
                self.content_var.get(),
                operator=rule.OP_CONTAINS,
                case_sensitive=self.case_sensitive_var.get()
            )
        elif rule_type == "metadata":
            rule.set_metadata_condition(
                self.metadata_field_var.get(),
                self.metadata_value_var.get()
            )
        elif rule_type == "date":
            rule.set_date_condition(
                self.date_field_var.get(),
                (self.start_date_var.get(), self.end_date_var.get())
            )
        elif rule_type == "tag":
            rule.set_tag_condition(
                self.tag_var.get()
            )
        elif rule_type == "ai":
            rule.set_ai_analysis_condition(
                self.ai_field_var.get(),
                self.ai_value_var.get()
            )
        elif rule_type == "image":
            rule.set_image_condition(
                self.image_field_var.get(),
                self.image_value_var.get()
            )

        # Save rule
        if self.selected_rule:
            if self.rule_manager.update_rule(rule):
                self.populate_rule_list()
                messagebox.showinfo("Save Rule", "Rule updated successfully")
            else:
                messagebox.showerror("Save Rule", "Failed to update rule")
        else:
            self.rule_manager.add_rule(rule)
            self.populate_rule_list()
            messagebox.showinfo("Save Rule", "Rule created successfully")

    def cancel_rule_edit(self):
        """Cancel rule editing"""
        self.selected_rule = None
        self.rule_name_var.set("")
        self.rule_desc_var.set("")
        self.rule_priority_var.set("100")
        self.rule_type_var.set("File Name Pattern")
        self.target_path_var.set("")
        self.should_copy_var.set(True)
        self.create_summary_var.set(False)

        # Update condition frame
        self.update_rule_condition_frame()

    def test_rule(self):
        """Test the current rule against sample files"""
        # Check if we have analyzed files
        if not self.analyzed_files:
            messagebox.showinfo(
                "Test Rule", "Please scan files first to test the rule")
            return

        # Create a temporary rule from current settings
        try:
            priority = int(self.rule_priority_var.get())
        except ValueError:
            priority = 100

        # Get rule type
        rule_type_display = self.rule_type_var.get()
        rule_type = "pattern"  # Default
        for display_name, type_code in self.rule_types:
            if display_name == rule_type_display:
                rule_type = type_code
                break

        # Create temporary rule
        temp_rule = self.rule_manager.create_rule_template("default")
        temp_rule.name = self.rule_name_var.get() or "Test Rule"
        temp_rule.description = self.rule_desc_var.get()
        temp_rule.priority = priority
        temp_rule.rule_type = rule_type
        temp_rule.target_path_template = self.target_path_var.get(
        ) or "{file_type}/{file_name}"

        # Set condition based on rule type
        try:
            if rule_type == "pattern":
                temp_rule.set_name_pattern_condition(
                    self.pattern_var.get(),
                    operator=temp_rule.OP_REGEX,
                    case_sensitive=self.case_sensitive_var.get()
                )
            elif rule_type == "content":
                temp_rule.set_content_condition(
                    self.content_var.get(),
                    operator=temp_rule.OP_CONTAINS,
                    case_sensitive=self.case_sensitive_var.get()
                )
            elif rule_type == "metadata":
                temp_rule.set_metadata_condition(
                    self.metadata_field_var.get(),
                    self.metadata_value_var.get()
                )
            elif rule_type == "date":
                temp_rule.set_date_condition(
                    self.date_field_var.get(),
                    (self.start_date_var.get(), self.end_date_var.get())
                )
            elif rule_type == "tag":
                temp_rule.set_tag_condition(
                    self.tag_var.get()
                )
            elif rule_type == "ai":
                temp_rule.set_ai_analysis_condition(
                    self.ai_field_var.get(),
                    self.ai_value_var.get()
                )
            elif rule_type == "image":
                temp_rule.set_image_condition(
                    self.image_field_var.get(),
                    self.image_value_var.get()
                )
        except Exception as e:
            messagebox.showerror(
                "Test Rule", f"Error creating test rule: {str(e)}")
            return

        # Test rule against analyzed files
        matching_files = []
        for file_info in self.analyzed_files:
            if temp_rule.matches(file_info):
                matching_files.append(file_info)

        # Show results
        if matching_files:
            result_text = f"Rule matches {len(matching_files)} files:\n\n"
            for file_info in matching_files[:10]:  # Show first 10 matches
                result_text += f"- {file_info['file_name']}\n"

            if len(matching_files) > 10:
                result_text += f"\n... and {len(matching_files) - 10} more files"

            messagebox.showinfo("Test Rule Results", result_text)
        else:
            messagebox.showinfo("Test Rule Results",
                                "No files match this rule")

    def import_rules(self):
        """Import rules from a file"""
        file_path = filedialog.askopenfilename(
            title="Import Rules",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )

        if file_path:
            if self.rule_manager.load_rules(file_path):
                self.populate_rule_list()
                messagebox.showinfo(
                    "Import Rules", "Rules imported successfully")
            else:
                messagebox.showerror("Import Rules", "Failed to import rules")

    def export_rules(self):
        """Export rules to a file"""
        file_path = filedialog.asksaveasfilename(
            title="Export Rules",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )

        if file_path:
            if self.rule_manager.save_rules(file_path):
                messagebox.showinfo(
                    "Export Rules", "Rules exported successfully")
            else:
                messagebox.showerror("Export Rules", "Failed to export rules")

    # Image handling methods
    def search_images(self):
        """Search for images based on the search text"""
        search_text = self.image_search_var.get().lower()
        if not search_text:
            self.filter_images()
            return

        # Filter the analyzed files to find images matching the search text
        self.display_images([
            file_info for file_info in self.analyzed_files
            if file_info.get("is_image", False) and search_text in file_info.get("file_name", "").lower()
        ])

    def filter_images(self, event=None):
        """Filter images based on selected criteria"""
        if not self.analyzed_files:
            messagebox.showinfo("Filter Images", "Please scan files first")
            return

        # Get filter criteria
        image_type = self.image_type_var.get()
        date_from = self.image_date_from_var.get()
        date_to = self.image_date_to_var.get()
        content = self.image_content_var.get().lower()

        # Filter images
        filtered_images = []
        for file_info in self.analyzed_files:
            if not file_info.get("is_image", False):
                continue

            # Filter by image type
            if image_type != "All":
                file_ext = file_info.get("file_ext", "").lower()
                if image_type.lower() not in file_ext:
                    continue

            # Filter by date range
            if date_from or date_to:
                # Get image date
                image_date = None
                if "metadata" in file_info and "date_time_original" in file_info["metadata"]:
                    try:
                        date_str = file_info["metadata"]["date_time_original"]
                        # Parse date in format "YYYY:MM:DD HH:MM:SS"
                        parts = date_str.split(" ")[0].split(":")
                        image_date = f"{parts[0]}-{parts[1]}-{parts[2]}"
                    except:
                        pass

                if not image_date:
                    # Use file modified date as fallback
                    modified_time = file_info.get("modified_time", 0)
                    image_date = time.strftime(
                        "%Y-%m-%d", time.localtime(modified_time))

                # Check date range
                if date_from and image_date < date_from:
                    continue
                if date_to and image_date > date_to:
                    continue

            # Filter by content
            if content:
                # Check image analysis for content labels
                content_match = False
                if "image_analysis" in file_info and "labels" in file_info["image_analysis"]:
                    for label in file_info["image_analysis"]["labels"]:
                        if content in label.lower():
                            content_match = True
                            break

                if not content_match:
                    continue

            # Image passed all filters
            filtered_images.append(file_info)

        # Display filtered images
        self.display_images(filtered_images)

    def sort_images(self, event=None):
        """Sort images based on selected criteria"""
        if not hasattr(self, "current_images") or not self.current_images:
            return

        sort_by = self.image_sort_var.get()

        if sort_by == "Date (Newest)":
            self.current_images.sort(key=lambda x: x.get(
                "modified_time", 0), reverse=True)
        elif sort_by == "Date (Oldest)":
            self.current_images.sort(key=lambda x: x.get("modified_time", 0))
        elif sort_by == "Name":
            self.current_images.sort(
                key=lambda x: x.get("file_name", "").lower())
        elif sort_by == "Size":
            self.current_images.sort(
                key=lambda x: x.get("file_size", 0), reverse=True)

        # Redisplay images
        self.display_images(self.current_images)

    def update_thumbnail_size(self, event=None):
        """Update thumbnail size based on selection"""
        size = self.thumbnail_size_var.get()

        if size == "Small":
            self.image_analyzer.set_thumbnail_size(100, 100)
        elif size == "Medium":
            self.image_analyzer.set_thumbnail_size(200, 200)
        elif size == "Large":
            self.image_analyzer.set_thumbnail_size(300, 300)

        # Redisplay images if we have any
        if hasattr(self, "current_images") and self.current_images:
            self.display_images(self.current_images)

    def display_images(self, image_files):
        """Display images in the grid"""
        # Store current images
        self.current_images = image_files

        # Clear existing images
        for widget in self.image_grid.winfo_children():
            widget.destroy()

        # Clear image references
        self.image_references = []
        self.selected_images = []

        # Update count
        self.image_count_var.set(f"{len(image_files)} images found")

        if not image_files:
            # Show "no images" message
            ttk.Label(self.image_grid, text="No images found matching the criteria").grid(
                row=0, column=0, padx=20, pady=20)
            return

        # Determine grid dimensions
        size = self.thumbnail_size_var.get()
        if size == "Small":
            cols = 6
            thumb_size = 100
        elif size == "Medium":
            cols = 4
            thumb_size = 200
        else:  # Large
            cols = 3
            thumb_size = 300

        # Create image thumbnails
        for i, file_info in enumerate(image_files):
            row = i // cols
            col = i % cols

            # Create frame for image
            image_frame = ttk.Frame(self.image_grid, padding=5)
            image_frame.grid(row=row, column=col, padx=5, pady=5)

            # Get or generate thumbnail
            thumbnail_path = None
            if "image_analysis" in file_info and "thumbnail_path" in file_info["image_analysis"]:
                thumbnail_path = file_info["image_analysis"]["thumbnail_path"]

            if not thumbnail_path or not os.path.exists(thumbnail_path):
                # Generate thumbnail
                try:
                    thumbnail_path = self.image_analyzer._generate_thumbnail(
                        file_info["file_path"])
                except:
                    thumbnail_path = None

            # Display thumbnail or placeholder
            if thumbnail_path and os.path.exists(thumbnail_path):
                try:
                    # Load image and resize
                    img = Image.open(thumbnail_path)
                    img.thumbnail((thumb_size, thumb_size))
                    photo = ImageTk.PhotoImage(img)

                    # Store reference to prevent garbage collection
                    self.image_references.append(photo)

                    # Create label with image
                    img_label = ttk.Label(image_frame, image=photo)
                    img_label.pack(pady=2)

                    # Bind click event
                    img_label.bind(
                        "<Button-1>", lambda e, fi=file_info: self.toggle_image_selection(e, fi))
                except Exception as e:
                    ttk.Label(image_frame, text="Error loading image").pack(
                        pady=2)
            else:
                ttk.Label(image_frame, text="No thumbnail").pack(pady=2)

            # Add filename label
            filename = file_info.get("file_name", "")
            if len(filename) > 20:
                filename = filename[:17] + "..."
            ttk.Label(image_frame, text=filename).pack(pady=2)

    def toggle_image_selection(self, event, file_info):
        """Toggle selection of an image"""
        widget = event.widget

        # Check if image is already selected
        if file_info in self.selected_images:
            # Deselect
            self.selected_images.remove(file_info)
            widget.configure(style="TLabel")  # Reset style
        else:
            # Select
            self.selected_images.append(file_info)
            # Create a selected style if it doesn't exist
            try:
                self.style.configure("Selected.TLabel", background="#4a6984")
                widget.configure(style="Selected.TLabel")
            except:
                # Fallback if style doesn't work
                widget.configure(background="#4a6984")

    def analyze_selected_images(self):
        """Analyze selected images with AI vision"""
        if not self.selected_images:
            messagebox.showinfo(
                "Analyze Images", "Please select images to analyze")
            return

        # Check if vision API is enabled
        if not self.settings_manager.get_setting("image_analysis.vision_api_enabled", False):
            result = messagebox.askyesno(
                "Vision API Not Enabled",
                "The Vision API is not enabled in settings. Would you like to enable it now?"
            )
            if result:
                # Switch to settings tab
                self.notebook.select(self.settings_tab)
                return
            else:
                return

        # Get API key
        api_key = self.settings_manager.get_api_key("vision")
        if not api_key:
            messagebox.showinfo(
                "API Key Required",
                "Please set your Vision API key in the settings tab"
            )
            return

        # Configure image analyzer
        provider = self.settings_manager.get_setting(
            "image_analysis.vision_api_provider", "google")
        self.image_analyzer.set_vision_api(provider, api_key)

        # Start analysis in a thread
        self.running = True
        self.cancel_requested = False
        threading.Thread(target=self.analyze_images_thread,
                         daemon=True).start()

    def analyze_images_thread(self):
        """Thread for analyzing images"""
        try:
            total = len(self.selected_images)

            for i, file_info in enumerate(self.selected_images):
                if self.cancel_requested:
                    self.queue.put(("cancelled", None))
                    break

                # Update status
                self.queue.put(
                    ("progress", (i, total, f"Analyzing {file_info['file_name']}...")))

                # Analyze image
                try:
                    result = self.image_analyzer.analyze_image(
                        file_info["file_path"])

                    # Update file info with analysis results
                    file_info["image_analysis"] = result

                    # Update status
                    self.queue.put(
                        ("progress", (i+1, total, f"Analyzed {file_info['file_name']}")))
                except Exception as e:
                    self.queue.put(
                        ("error", f"Error analyzing {file_info['file_name']}: {str(e)}"))

            # Refresh display
            self.queue.put(("refresh_images", None))

        except Exception as e:
            self.queue.put(("error", str(e)))
        finally:
            self.queue.put(("complete", None))

    def organize_selected_images(self):
        """Organize selected images"""
        if not self.selected_images:
            messagebox.showinfo("Organize Images",
                                "Please select images to organize")
            return

        # Get target directory
        target_dir = self.target_dir.get()
        if not target_dir:
            target_dir = filedialog.askdirectory(
                title="Select Target Directory")
            if not target_dir:
                return
            self.target_dir.set(target_dir)

        # Get organization options
        options = {
            "create_category_folders": self.create_category_folders_var.get(),
            "generate_summaries": self.generate_summaries_var.get(),
            "include_metadata": self.include_metadata_var.get(),
            "copy_instead_of_move": self.copy_instead_of_move_var.get(),
            "detect_duplicates": self.detect_duplicates_var.get(),
            "duplicate_action": self.duplicate_action_var.get(),
            "duplicate_strategy": self.duplicate_strategy_var.get(),
            "apply_tags": self.apply_tags_var.get(),
            "suggest_tags": self.suggest_tags_var.get(),
            "use_custom_rules": self.use_custom_rules_var.get(),
            "rules_file": self.rules_file_var.get()
        }

        # Start organization in a thread
        self.running = True
        self.cancel_requested = False
        threading.Thread(target=self.organize_images_thread,
                         args=(self.selected_images, target_dir, options),
                         daemon=True).start()

    def organize_images_thread(self, images, target_dir, options):
        """Thread for organizing images"""
        try:
            # Define progress callback
            def progress_callback(current, total, filename):
                self.queue.put(("progress", (current, total, filename)))
                return not self.cancel_requested

            # Organize files
            result = self.file_organizer.organize_files(
                images, target_dir, progress_callback, options)

            # Show results
            message = (
                f"Organization complete:\n"
                f"- {result['organized_files']} files organized\n"
                f"- {result['skipped_files']} files skipped\n"
                f"- {result['duplicate_files']} duplicate files\n"
                f"- {result['error_files']} errors"
            )
            self.queue.put(("success", message))

        except Exception as e:
            self.queue.put(("error", str(e)))
        finally:
            self.queue.put(("complete", None))

    # Batch processing methods
    def browse_batch_source(self):
        """Browse for batch source directory"""
        directory = filedialog.askdirectory(title="Select Source Directory")
        if directory:
            self.batch_source_var.set(directory)
            self.source_dir.set(directory)  # Update main source dir too

    def browse_batch_target(self):
        """Browse for batch target directory"""
        directory = filedialog.askdirectory(title="Select Target Directory")
        if directory:
            self.batch_target_var.set(directory)
            self.target_dir.set(directory)  # Update main target dir too

    def start_batch(self):
        """Start a batch processing job"""
        # Get source and target directories
        source_dir = self.batch_source_var.get()
        target_dir = self.batch_target_var.get()

        if not source_dir:
            messagebox.showinfo("Batch Processing",
                                "Please select a source directory")
            return

        if not target_dir:
            messagebox.showinfo("Batch Processing",
                                "Please select a target directory")
            return

        # Get batch settings
        try:
            batch_size = int(self.batch_size_var.get())
            if batch_size < 1:
                messagebox.showinfo("Batch Processing",
                                    "Batch size must be at least 1")
                return
        except ValueError:
            messagebox.showinfo("Batch Processing",
                                "Batch size must be a number")
            return

        try:
            batch_delay = float(self.batch_delay_var.get())
            if batch_delay < 0:
                messagebox.showinfo("Batch Processing",
                                    "Batch delay must be non-negative")
                return
        except ValueError:
            messagebox.showinfo("Batch Processing",
                                "Batch delay must be a number")
            return

        try:
            max_workers = int(self.max_workers_var.get())
            if max_workers < 1:
                messagebox.showinfo("Batch Processing",
                                    "Max workers must be at least 1")
                return
        except ValueError:
            messagebox.showinfo("Batch Processing",
                                "Max workers must be a number")
            return

        try:
            memory_limit = int(self.memory_limit_var.get())
            if memory_limit < 10 or memory_limit > 100:
                messagebox.showinfo("Batch Processing",
                                    "Memory limit must be between 10 and 100")
                return
        except ValueError:
            messagebox.showinfo("Batch Processing",
                                "Memory limit must be a number")
            return

        # Configure file analyzer
        self.file_analyzer.batch_size = batch_size
        self.file_analyzer.batch_delay = batch_delay
        self.file_analyzer.max_workers = max_workers

        # Update settings
        self.settings_manager.set_setting("batch_size", batch_size)
        self.settings_manager.set_setting("batch_delay", batch_delay)
        self.settings_manager.set_setting(
            "batch_processing.max_workers", max_workers)
        self.settings_manager.set_setting(
            "batch_processing.memory_limit_percent", memory_limit)
        self.settings_manager.set_setting(
            "batch_processing.use_process_pool", self.use_process_pool_var.get())
        self.settings_manager.set_setting(
            "batch_processing.adaptive_workers", self.adaptive_workers_var.get())
        self.settings_manager.set_setting(
            "batch_processing.enable_pause_resume", self.enable_pause_resume_var.get())
        self.settings_manager.set_setting(
            "batch_processing.save_job_state", self.save_job_state_var.get())

        # Start batch processing in a thread
        self.running = True
        self.cancel_requested = False
        self.is_paused = False

        # Update UI
        self.start_batch_button.configure(state="disabled")
        self.pause_batch_button.configure(state="normal")
        self.resume_batch_button.configure(state="disabled")
        self.cancel_batch_button.configure(state="normal")

        # Reset progress
        self.progress_var.set(0)
        self.batch_status_var.set("Starting batch processing...")
        self.cpu_usage_var.set("0%")
        self.memory_usage_var.set("0%")
        self.elapsed_time_var.set("00:00:00")
        self.remaining_time_var.set("00:00:00")

        # Start batch processing thread
        threading.Thread(target=self.batch_processing_thread,
                         args=(source_dir, target_dir),
                         daemon=True).start()

        # Start resource monitoring
        self.start_resource_monitoring()

    def pause_batch(self):
        """Pause the current batch processing job"""
        if self.running and not self.is_paused:
            self.is_paused = True
            self.file_analyzer.pause_operation()
            self.batch_status_var.set("Paused")

            # Update UI
            self.pause_batch_button.configure(state="disabled")
            self.resume_batch_button.configure(state="normal")

    def resume_batch(self):
        """Resume the paused batch processing job"""
        if self.running and self.is_paused:
            self.is_paused = False
            self.file_analyzer.resume_operation()
            self.batch_status_var.set("Resuming...")

            # Update UI
            self.pause_batch_button.configure(state="normal")
            self.resume_batch_button.configure(state="disabled")

    def cancel_batch(self):
        """Cancel the current batch processing job"""
        if self.running:
            self.cancel_requested = True
            self.file_analyzer.cancel_operation()
            self.batch_status_var.set("Cancelling...")

            # Update UI
            self.pause_batch_button.configure(state="disabled")
            self.resume_batch_button.configure(state="disabled")
            self.cancel_batch_button.configure(state="disabled")

    def resume_selected_job(self):
        """Resume a selected job from the job history"""
        selected_items = self.job_list.selection()
        if not selected_items:
            messagebox.showinfo("Resume Job", "Please select a job to resume")
            return

        job_id = selected_items[0]
        job_state = self.file_analyzer.get_job_state(job_id)

        if not job_state:
            messagebox.showinfo("Resume Job", "Job state not found")
            return

        if job_state["completed"]:
            messagebox.showinfo("Resume Job", "Job is already completed")
            return

        # Get source and target directories
        source_dir = job_state["directory"]
        target_dir = self.batch_target_var.get()

        if not target_dir:
            messagebox.showinfo(
                "Resume Job", "Please select a target directory")
            return

        # Start batch processing in a thread
        self.running = True
        self.cancel_requested = False
        self.is_paused = False

        # Update UI
        self.start_batch_button.configure(state="disabled")
        self.pause_batch_button.configure(state="normal")
        self.resume_batch_button.configure(state="disabled")
        self.cancel_batch_button.configure(state="normal")

        # Reset progress
        self.progress_var.set(0)
        self.batch_status_var.set(f"Resuming job {job_id}...")

        # Start batch processing thread
        threading.Thread(target=self.batch_processing_thread,
                         args=(source_dir, target_dir, job_id),
                         daemon=True).start()

        # Start resource monitoring
        self.start_resource_monitoring()

    def view_job_details(self):
        """View details of a selected job"""
        selected_items = self.job_list.selection()
        if not selected_items:
            messagebox.showinfo("Job Details", "Please select a job to view")
            return

        job_id = selected_items[0]
        job_state = self.file_analyzer.get_job_state(job_id)

        if not job_state:
            messagebox.showinfo("Job Details", "Job state not found")
            return

        # Create a details dialog
        details_dialog = tk.Toplevel(self.root)
        details_dialog.title(f"Job Details - {job_id}")
        details_dialog.geometry("600x400")
        details_dialog.transient(self.root)
        details_dialog.grab_set()

        # Job details
        ttk.Label(details_dialog, text=f"Job ID: {job_id}").pack(
            anchor="w", padx=10, pady=5)
        ttk.Label(details_dialog, text=f"Directory: {job_state['directory']}").pack(
            anchor="w", padx=10, pady=5)
        ttk.Label(details_dialog, text=f"Total Files: {job_state['total_files']}").pack(
            anchor="w", padx=10, pady=5)
        ttk.Label(details_dialog, text=f"Processed Files: {len(job_state['processed_files'])}").pack(
            anchor="w", padx=10, pady=5)
        ttk.Label(details_dialog, text=f"Pending Files: {len(job_state['pending_files'])}").pack(
            anchor="w", padx=10, pady=5)
        ttk.Label(details_dialog, text=f"Status: {'Completed' if job_state['completed'] else 'Pending'}").pack(
            anchor="w", padx=10, pady=5)

        # Elapsed time
        elapsed_time = job_state['elapsed_time']
        hours = int(elapsed_time // 3600)
        minutes = int((elapsed_time % 3600) // 60)
        seconds = int(elapsed_time % 60)
        ttk.Label(details_dialog, text=f"Elapsed Time: {hours:02d}:{minutes:02d}:{seconds:02d}").pack(
            anchor="w", padx=10, pady=5)

        # File list
        ttk.Label(details_dialog, text="Processed Files:").pack(
            anchor="w", padx=10, pady=5)

        # Create a frame with scrollbar for the file list
        file_frame = ttk.Frame(details_dialog)
        file_frame.pack(fill="both", expand=True, padx=10, pady=5)

        file_list = tk.Listbox(file_frame)
        file_list.pack(side="left", fill="both", expand=True)

        file_scrollbar = ttk.Scrollbar(
            file_frame, orient="vertical", command=file_list.yview)
        file_scrollbar.pack(side="right", fill="y")
        file_list.configure(yscrollcommand=file_scrollbar.set)

        # Add processed files to the list
        # Limit to first 100 files
        for file_info in job_state['processed_files'][:100]:
            file_list.insert("end", file_info.get('file_name', 'Unknown'))

        if len(job_state['processed_files']) > 100:
            file_list.insert(
                "end", f"... and {len(job_state['processed_files']) - 100} more files")

        # Close button
        ttk.Button(details_dialog, text="Close",
                   command=details_dialog.destroy).pack(pady=10)

    def clear_completed_jobs(self):
        """Clear completed jobs from the job history"""
        # Get all jobs
        job_ids = []
        for item in self.job_list.get_children():
            job_state = self.file_analyzer.get_job_state(item)
            if job_state and job_state["completed"]:
                job_ids.append(item)

        if not job_ids:
            messagebox.showinfo("Clear Jobs", "No completed jobs to clear")
            return

        # Confirm
        if not messagebox.askyesno("Clear Jobs", f"Clear {len(job_ids)} completed jobs?"):
            return

        # Clear jobs
        for job_id in job_ids:
            self.job_list.delete(job_id)
            if job_id in self.file_analyzer.job_state:
                del self.file_analyzer.job_state[job_id]

        messagebox.showinfo(
            "Clear Jobs", f"Cleared {len(job_ids)} completed jobs")

    def update_job_list(self):
        """Update the job history list"""
        # Clear existing items
        for item in self.job_list.get_children():
            self.job_list.delete(item)

        # Add jobs from file analyzer
        for job_id, job_state in self.file_analyzer.job_states.items():
            # Format start time
            start_time = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(job_state["start_time"]))

            # Determine status
            if job_state["completed"]:
                status = "Completed"
            elif self.is_paused and self.current_job_id == job_id:
                status = "Paused"
            elif self.running and self.current_job_id == job_id:
                status = "Running"
            else:
                status = "Pending"

            # Calculate progress
            total_files = job_state["total_files"]
            processed_files = len(job_state["processed_files"])
            if total_files > 0:
                progress = f"{processed_files}/{total_files} ({processed_files/total_files*100:.1f}%)"
            else:
                progress = "0/0 (0%)"

            # Add to list
            self.job_list.insert("", "end", iid=job_id,
                                 values=(start_time, status, f"{total_files} files", progress))

    def batch_processing_thread(self, source_dir, target_dir, job_id=None):
        """Thread for batch processing"""
        try:
            # Start time
            start_time = time.time()
            last_update_time = start_time

            # Define progress callback
            def progress_callback(current, total, status_message):
                nonlocal last_update_time
                current_time = time.time()

                # Update progress at most once per second to avoid GUI freezing
                if current_time - last_update_time >= 1.0:
                    self.queue.put(
                        ("progress", (current, total, status_message)))
                    last_update_time = current_time

                    # Update job progress
                    if self.file_analyzer.current_job_id:
                        job_progress = self.file_analyzer.get_job_progress(
                            self.file_analyzer.current_job_id)
                        if job_progress:
                            # Update time estimates
                            elapsed = job_progress["elapsed_time"]
                            remaining = job_progress["estimated_time_remaining"]

                            # Format times
                            elapsed_str = self.format_time(elapsed)
                            remaining_str = self.format_time(remaining)

                            # Update UI
                            self.queue.put(
                                ("update_time", (elapsed_str, remaining_str)))

                return not self.cancel_requested

            # Scan directory with enhanced options
            use_processes = self.use_process_pool_var.get()
            adaptive_workers = self.adaptive_workers_var.get()
            enable_pause_resume = self.enable_pause_resume_var.get()

            # Store current job ID
            self.current_job_id = job_id

            # Scan directory
            analyzed_files = self.file_analyzer.scan_directory(
                source_dir,
                batch_size=int(self.batch_size_var.get()),
                batch_delay=float(self.batch_delay_var.get()),
                callback=progress_callback,
                use_processes=use_processes,
                adaptive_workers=adaptive_workers,
                job_id=job_id,
                resume=(job_id is not None)
            )

            # Check if operation was cancelled or paused
            if self.cancel_requested:
                self.queue.put(("cancelled", None))
                return

            if self.is_paused:
                self.queue.put(("paused", None))
                return

            # Store analyzed files
            self.analyzed_files = analyzed_files

            # Update file list
            self.queue.put(("update_files", analyzed_files))

            # If we have a target directory, organize files
            if target_dir and analyzed_files:
                # Get organization options
                options = {
                    "create_category_folders": self.create_category_folders_var.get(),
                    "generate_summaries": self.generate_summaries_var.get(),
                    "include_metadata": self.include_metadata_var.get(),
                    "copy_instead_of_move": self.copy_instead_of_move_var.get(),
                    "detect_duplicates": self.detect_duplicates_var.get(),
                    "duplicate_action": self.duplicate_action_var.get(),
                    "duplicate_strategy": self.duplicate_strategy_var.get(),
                    "apply_tags": self.apply_tags_var.get(),
                    "suggest_tags": self.suggest_tags_var.get(),
                    "use_custom_rules": self.use_custom_rules_var.get(),
                    "rules_file": self.rules_file_var.get()
                }

                # Organize files
                self.queue.put(("status", "Organizing files..."))
                result = self.file_organizer.organize_files(
                    analyzed_files, target_dir, progress_callback, options)

                # Show results
                message = (
                    f"Batch processing complete:\n"
                    f"- {len(analyzed_files)} files analyzed\n"
                    f"- {result['organized_files']} files organized\n"
                    f"- {result['skipped_files']} files skipped\n"
                    f"- {result['duplicate_files']} duplicate files\n"
                    f"- {result['error_files']} errors"
                )
                self.queue.put(("success", message))
            else:
                # Just show analysis results
                self.queue.put(
                    ("success", f"Analysis complete: {len(analyzed_files)} files analyzed"))

            # Update job list
            self.queue.put(("update_job_list", None))

        except Exception as e:
            self.queue.put(("error", str(e)))
        finally:
            # Stop resource monitoring
            self.stop_resource_monitoring()

            # Reset UI
            self.queue.put(("reset_ui", None))

            # Mark as complete
            self.queue.put(("complete", None))

    def start_resource_monitoring(self):
        """Start monitoring system resources"""
        self.resource_monitoring = True
        threading.Thread(
            target=self.resource_monitoring_thread, daemon=True).start()

    def stop_resource_monitoring(self):
        """Stop monitoring system resources"""
        self.resource_monitoring = False

    def resource_monitoring_thread(self):
        """Thread for monitoring system resources"""
        try:
            while self.resource_monitoring and self.running:
                # Get resource usage
                if hasattr(self.file_analyzer, "resource_monitor"):
                    cpu_percent = self.file_analyzer.resource_monitor.get_cpu_percent()
                    memory_percent = self.file_analyzer.resource_monitor.get_memory_percent()

                    # Update UI
                    self.cpu_usage_var.set(f"{cpu_percent:.1f}%")
                    self.memory_usage_var.set(f"{memory_percent:.1f}%")

                # Sleep for a bit
                time.sleep(1.0)
        except:
            pass

    def format_time(self, seconds):
        """Format time in seconds to HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
