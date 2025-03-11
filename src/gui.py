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

logger = logging.getLogger("AIDocumentOrganizer")


class DocumentOrganizerApp:
    def __init__(self, root):
        """
        Initialize the Document Organizer application GUI.

        Args:
            root: The tkinter root window
        """
        self.root = root

        # Initialize settings manager
        self.settings_manager = SettingsManager()

        # Set up variables with values from settings
        source_dir = self.settings_manager.get_setting("source_directory", "")
        self.source_dir = tk.StringVar(
            value=source_dir if isinstance(source_dir, str) else "")

        target_dir = self.settings_manager.get_setting("target_directory", "")
        self.target_dir = tk.StringVar(
            value=target_dir if isinstance(target_dir, str) else "")

        # Aliases for save_directory method
        self.source_var = self.source_dir
        self.target_var = self.target_dir
        self.search_term = tk.StringVar()

        batch_size = self.settings_manager.get_setting("batch_size", 10)
        self.batch_size = tk.IntVar(
            value=batch_size if isinstance(batch_size, int) else 10)

        batch_delay = self.settings_manager.get_setting("batch_delay", 5)
        self.batch_delay = tk.IntVar(
            value=batch_delay if isinstance(batch_delay, int) else 5)

        theme = self.settings_manager.get_setting("theme", "clam")
        self.theme_var = tk.StringVar(
            value=theme if isinstance(theme, str) else "clam")

        # Logging options
        log_to_file_only = self.settings_manager.get_setting(
            "log_to_file_only", False)
        self.log_to_file_only = tk.BooleanVar(
            value=log_to_file_only if isinstance(log_to_file_only, bool) else False)

        # Organization rule variables
        create_folders = self.settings_manager.get_setting(
            "organization_rules.create_category_folders", True)
        self.create_category_folders = tk.BooleanVar(
            value=True if create_folders == {} else bool(create_folders))

        gen_summaries = self.settings_manager.get_setting(
            "organization_rules.generate_summaries", True)
        self.generate_summaries = tk.BooleanVar(
            value=True if gen_summaries == {} else bool(gen_summaries))

        include_meta = self.settings_manager.get_setting(
            "organization_rules.include_metadata", True)
        self.include_metadata = tk.BooleanVar(
            value=True if include_meta == {} else bool(include_meta))

        copy_instead = self.settings_manager.get_setting(
            "organization_rules.copy_instead_of_move", True)
        self.copy_instead_of_move = tk.BooleanVar(
            value=True if copy_instead == {} else bool(copy_instead))

        self.analyzer = FileAnalyzer()
        self.organizer = FileOrganizer()
        self.ai_analyzer = AIAnalyzer(self.settings_manager)
        self.openai_analyzer = OpenAIAnalyzer(self.settings_manager)
        self.status_queue = queue.Queue()
        self.is_scanning = False
        self.is_organizing = False
        self.cancel_requested = False
        self.scanned_files = []
        self.total_files = 0
        self.processed_files = 0

        self._create_widgets()
        self._setup_layout()

        # Start the queue consumer
        self.consume_queue()

        logger.info("GUI initialized")

    def _create_widgets(self):
        """Create all the GUI widgets"""
        # Style configuration
        self.style = ttk.Style()

        # Update theme_var to use current theme
        current_theme = self.style.theme_use()
        self.theme_var.set(current_theme)

        # Configure styles
        self.style.configure("TButton", padding=6, font=('Segoe UI', 10))
        self.style.configure("TLabel", font=('Segoe UI', 10))
        self.style.configure("Header.TLabel", font=('Segoe UI', 12, 'bold'))
        self.style.configure("Status.TLabel", font=('Segoe UI', 10, 'italic'))
        self.style.configure(
            "Success.TLabel", foreground='green', font=('Segoe UI', 10, 'bold'))
        self.style.configure(
            "Warning.TLabel", foreground='orange', font=('Segoe UI', 10, 'bold'))
        self.style.configure("Error.TLabel", foreground='red',
                             font=('Segoe UI', 10, 'bold'))

        # Create a notebook for tabs
        self.notebook = ttk.Notebook(self.root)

        # Main tab
        self.main_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.main_tab, text="Document Organizer")

        # Settings tab
        self.settings_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_tab, text="Settings")

        # About tab
        self.about_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.about_tab, text="About")

        # Create settings widgets
        self._create_settings_widgets()

        # Frame for directory selection
        self.dir_frame = ttk.LabelFrame(
            self.main_tab, text="Directory Selection", padding=(10, 5))

        # Source directory widgets
        self.source_label = ttk.Label(self.dir_frame, text="Source Directory:")
        self.source_entry = ttk.Entry(
            self.dir_frame, textvariable=self.source_dir, width=50)
        self.source_button = ttk.Button(
            self.dir_frame, text="Browse...", command=self.browse_source)

        # Target directory widgets
        self.target_label = ttk.Label(self.dir_frame, text="Target Directory:")
        self.target_entry = ttk.Entry(
            self.dir_frame, textvariable=self.target_dir, width=50)
        self.target_button = ttk.Button(
            self.dir_frame, text="Browse...", command=self.browse_target)

        # Scan options frame
        self.options_frame = ttk.LabelFrame(
            self.main_tab, text="Processing Options", padding=(10, 5))

        # Batch size options
        self.batch_label = ttk.Label(self.options_frame, text="Batch Size:")
        self.batch_combobox = ttk.Combobox(self.options_frame, textvariable=self.batch_size,
                                           values=["5", "10", "20", "50", "100"], width=5)
        self.batch_combobox.current(2)  # Default to 20

        # Scan button
        self.scan_button = ttk.Button(
            self.options_frame, text="Scan Files", command=self.start_scan)

        # Status frame with detailed progress information
        self.status_frame = ttk.LabelFrame(
            self.main_tab, text="Processing Status", padding=(10, 5))

        # Status indicators
        self.status_label = ttk.Label(
            self.status_frame, text="Ready", style="Status.TLabel")

        # Determinate progress bar for batch processing
        self.progress_bar = ttk.Progressbar(
            self.status_frame, orient='horizontal', length=400, mode='determinate')

        # Progress details
        self.progress_details = ttk.Label(self.status_frame, text="")

        # Stats frame for processing statistics
        self.stats_frame = ttk.Frame(self.status_frame)
        self.processed_label = ttk.Label(self.stats_frame, text="Processed: 0")
        self.total_label = ttk.Label(self.stats_frame, text="Total: 0")
        self.batch_status_label = ttk.Label(
            self.stats_frame, text="Current Batch: 0/0")

        # File list frame
        self.files_frame = ttk.LabelFrame(
            self.main_tab, text="Scanned Files", padding=(10, 5))

        # Search bar
        self.search_frame = ttk.Frame(self.files_frame, padding=(0, 5))
        self.search_label = ttk.Label(self.search_frame, text="Search:")
        self.search_entry = ttk.Entry(
            self.search_frame, textvariable=self.search_term, width=30)
        self.search_entry.bind("<KeyRelease>", self.search_files)

        # File treeview
        self.tree_columns = ("Filename", "Type", "Size",
                             "Category", "Keywords")
        self.tree = ttk.Treeview(
            self.files_frame, columns=self.tree_columns, show='headings')

        # Set column headings
        for col in self.tree_columns:
            self.tree.heading(col, text=col)

        # Set column widths
        self.tree.column("Filename", width=200)
        self.tree.column("Type", width=80)
        self.tree.column("Size", width=80)
        self.tree.column("Category", width=120)
        self.tree.column("Keywords", width=250)

        # Add scrollbars
        self.tree_yscroll = ttk.Scrollbar(
            self.files_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.tree_yscroll.set)

        # File details frame
        self.details_frame = ttk.LabelFrame(
            self.main_tab, text="File Details", padding=(10, 5))

        # File details
        self.details_text = ScrolledText(
            self.details_frame, wrap=tk.WORD, width=40, height=10)
        self.details_text.config(state=tk.DISABLED)

        # Bottom action frame
        self.action_frame = ttk.Frame(self.main_tab, padding=(10, 5))
        self.organize_button = ttk.Button(
            self.action_frame, text="Organize Files", command=self.organize_files)
        self.report_button = ttk.Button(
            self.action_frame, text="Generate Report", command=self.generate_folder_report)
        self.cancel_button = ttk.Button(
            self.action_frame, text="Cancel", command=self.cancel_operation, state=tk.DISABLED)

        # Bind tree selection event
        self.tree.bind("<<TreeviewSelect>>", self.show_file_details)

    def _setup_layout(self):
        """Setup the layout of widgets using grid"""
        # Place the notebook in the root window
        self.notebook.grid(row=0, column=0, sticky='nsew')

        # Configure the root window grid
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Directory frame (inside main tab)
        self.dir_frame.grid(row=0, column=0, columnspan=2,
                            sticky='ew', padx=10, pady=10)

        self.source_label.grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.source_entry.grid(row=0, column=1, sticky='ew', padx=5, pady=5)
        self.source_button.grid(row=0, column=2, sticky='e', padx=5, pady=5)

        self.target_label.grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.target_entry.grid(row=1, column=1, sticky='ew', padx=5, pady=5)
        self.target_button.grid(row=1, column=2, sticky='e', padx=5, pady=5)

        # Options frame layout
        self.options_frame.grid(
            row=2, column=0, columnspan=2, sticky='ew', padx=10, pady=5)
        self.batch_label.grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.batch_combobox.grid(row=0, column=1, sticky='w', padx=5, pady=5)
        self.scan_button.grid(row=0, column=2, sticky='e', padx=5, pady=5)

        # Status frame
        self.status_frame.grid(row=3, column=0, columnspan=2,
                               sticky='ew', padx=10, pady=(0, 10))
        self.status_label.grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.progress_bar.grid(
            row=1, column=0, columnspan=2, sticky='ew', padx=5, pady=5)
        self.progress_details.grid(row=2, column=0, sticky='w', padx=5, pady=5)

        # Statistics frame
        self.stats_frame.grid(row=3, column=0, columnspan=2,
                              sticky='ew', padx=5, pady=5)
        self.processed_label.grid(row=0, column=0, sticky='w', padx=20, pady=2)
        self.total_label.grid(row=0, column=1, sticky='w', padx=20, pady=2)
        self.batch_status_label.grid(
            row=0, column=2, sticky='w', padx=20, pady=2)

        # Files frame
        self.files_frame.grid(row=1, column=0, sticky='nsew', padx=10, pady=10)

        self.search_frame.grid(row=0, column=0, sticky='ew')
        self.search_label.grid(row=0, column=0, sticky='w', padx=5)
        self.search_entry.grid(row=0, column=1, sticky='ew', padx=5)

        self.tree.grid(row=1, column=0, sticky='nsew')
        self.tree_yscroll.grid(row=1, column=1, sticky='ns')

        # Details frame
        self.details_frame.grid(
            row=1, column=1, sticky='nsew', padx=10, pady=10)
        self.details_text.pack(expand=True, fill='both', padx=5, pady=5)

        # Action frame
        self.action_frame.grid(
            row=2, column=0, columnspan=2, sticky='e', padx=10, pady=10)
        self.report_button.pack(side=tk.RIGHT, padx=(0, 5))
        self.organize_button.pack(side=tk.RIGHT, padx=(0, 5))
        self.cancel_button.pack(side=tk.RIGHT, padx=(0, 5))

        # Configure grid weights for main_tab (not the root)
        self.main_tab.grid_columnconfigure(0, weight=3)
        self.main_tab.grid_columnconfigure(1, weight=2)
        self.main_tab.grid_rowconfigure(1, weight=1)

        self.dir_frame.grid_columnconfigure(1, weight=1)
        self.files_frame.grid_columnconfigure(0, weight=1)
        self.files_frame.grid_rowconfigure(1, weight=1)

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
        if self.is_scanning:
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

        self.scanned_files = []
        self.is_scanning = True
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
        self.status_queue.put(("status", "Scanning files..."))

        # Start scanning thread
        scan_thread = threading.Thread(
            target=self.scan_files_thread, args=(source_dir,))
        scan_thread.daemon = True
        scan_thread.start()

    def scan_files_thread(self, directory):
        """Thread function to scan files"""
        try:
            # Get the batch size and delay from the GUI
            batch_size = self.batch_size.get()
            batch_delay = self.batch_delay.get()

            # Progress callback function
            def progress_callback(processed, total, status_message):
                self.status_queue.put(("progress", {
                    "processed": processed,
                    "total": total,
                    "status": status_message,
                    "percentage": int((processed / max(1, total)) * 100)
                }))

                # Check for cancellation
                return not self.cancel_requested

            # Scan the directory with progress tracking
            files = self.analyzer.scan_directory(
                directory,
                batch_size=batch_size,
                batch_delay=batch_delay,
                callback=progress_callback
            )

            if self.cancel_requested:
                self.status_queue.put(("cancelled", None))
            else:
                self.status_queue.put(("files", files))
        except Exception as e:
            logger.error(f"Error scanning directory: {str(e)}")
            self.status_queue.put(("error", str(e)))
        finally:
            self.status_queue.put(("complete", None))

    def consume_queue(self):
        """Process messages from the queue"""
        try:
            while True:
                message_type, message = self.status_queue.get_nowait()

                if message_type == "status":
                    self.status_label.config(text=message)

                elif message_type == "progress":
                    # Update progress indicators with real-time information
                    progress_data = message
                    processed = progress_data.get("processed", 0)
                    total = progress_data.get("total", 0)
                    percentage = progress_data.get("percentage", 0)
                    status = progress_data.get("status", "")

                    # Update progress bar
                    self.progress_bar.config(mode='determinate')
                    self.progress_bar["value"] = percentage

                    # Update stats labels
                    self.processed_label.config(text=f"Processed: {processed}")
                    self.total_label.config(text=f"Total: {total}")

                    # Calculate current batch
                    batch_size = self.batch_size.get()
                    current_batch = (processed // batch_size) + 1
                    total_batches = (total + batch_size - 1) // batch_size
                    self.batch_status_label.config(
                        text=f"Batch: {current_batch}/{total_batches}")

                    # Update detailed progress text
                    self.progress_details.config(
                        text=f"{status} ({percentage}% complete)")

                elif message_type == "files":
                    self.scanned_files = message
                    self.update_file_list(message)

                elif message_type == "error":
                    messagebox.showerror("Error", message)
                    self.is_scanning = False
                    self.is_organizing = False
                    self.progress_bar.stop()
                    self.status_label.config(text="Ready")
                    self.cancel_button.config(state=tk.DISABLED)

                elif message_type == "success":
                    messagebox.showinfo("Success", message)
                    self.progress_details.config(text=message)

                elif message_type == "cancelled":
                    messagebox.showinfo(
                        "Cancelled", "Operation was cancelled by user")
                    self.progress_details.config(
                        text="Operation cancelled by user")
                    self.status_label.config(text="Operation cancelled")
                    self.cancel_button.config(state=tk.DISABLED)

                elif message_type == "complete":
                    if self.is_scanning:
                        self.is_scanning = False
                        self.progress_bar.stop()
                        if self.cancel_requested:
                            self.status_label.config(text="Scanning cancelled")
                        else:
                            self.status_label.config(
                                text=f"Completed scanning {len(self.scanned_files)} files")
                    elif self.is_organizing:
                        self.is_organizing = False
                        self.progress_bar.stop()
                        if self.cancel_requested:
                            self.status_label.config(
                                text="Organization cancelled")
                        else:
                            self.status_label.config(
                                text="Organization complete")
                            self.progress_details.config(
                                text="All files have been organized")
                    else:
                        # For report generation and other tasks
                        self.progress_bar.stop()
                        self.status_label.config(text="Task completed")

                    # Disable cancel button when operation is complete
                    self.cancel_button.config(state=tk.DISABLED)
                    self.cancel_requested = False

                self.status_queue.task_done()

        except queue.Empty:
            # No more messages, schedule the next check
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
        search_term = self.search_term.get().lower()

        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Add matching files to the treeview
        for file in self.scanned_files:
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
        for file in self.scanned_files:
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
        if len(self.scanned_files) > 1:
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
                file_info, self.scanned_files, max_results=3)

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
        if not self.scanned_files:
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
        self.is_organizing = True
        self.cancel_requested = False

        # Reset progress indicators
        self.progress_bar.config(mode='indeterminate')
        self.progress_bar.start(10)
        self.status_label.config(text="Organizing files...")
        self.progress_details.config(text="Preparing to organize files...")
        self.processed_label.config(text=f"Files: {len(self.scanned_files)}")
        self.total_label.config(text="Copying: 0")
        self.batch_status_label.config(text="")

        # Enable cancel button
        self.cancel_button.config(state=tk.NORMAL)

        # Save organization rules to settings
        self.save_organization_rules()

        # Start organization thread
        organize_thread = threading.Thread(
            target=self.organize_files_thread,
            args=(self.scanned_files, target_dir)
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
            batch_size = self.batch_size.get()
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
            batch_delay = self.batch_delay.get()
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
                directory = self.source_var.get()
                if not directory:
                    messagebox.showwarning(
                        "Warning", "Please select a source directory first")
                    return
                setting_name = "Default source directory"
                setting_key = "source_directory"
            elif dir_type == "target":
                directory = self.target_var.get()
                if not directory:
                    messagebox.showwarning(
                        "Warning", "Please select a target directory first")
                    return
                setting_name = "Default target directory"
                setting_key = "target_directory"
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
        """Save the organization rules to settings"""
        try:
            # Get values from UI
            rules = {
                "create_category_folders": self.create_category_folders.get(),
                "generate_summaries": self.generate_summaries.get(),
                "include_metadata": self.include_metadata.get(),
                "copy_instead_of_move": self.copy_instead_of_move.get()
            }

            # Save to settings
            for key, value in rules.items():
                self.settings_manager.set_setting(
                    f"organization_rules.{key}", value)

            logger.info(f"Organization rules saved: {rules}")
        except Exception as e:
            logger.error(f"Error saving organization rules: {str(e)}")
            messagebox.showerror(
                "Error", f"Could not save organization rules: {str(e)}")

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
            report_path = self.organizer.generate_folder_report(
                folder_path, include_summaries)

            if report_path:
                self.status_queue.put(
                    ("status", "Report generated successfully"))
                self.status_queue.put(
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
                self.status_queue.put(("error", "Failed to generate report"))
        except Exception as e:
            logger.error(f"Error generating folder report: {str(e)}")
            self.status_queue.put(("error", str(e)))
        finally:
            self.status_queue.put(("complete", None))

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
            self.batch_settings_frame, textvariable=self.batch_size, width=5)
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
            self.batch_settings_frame, textvariable=self.batch_delay, width=5)
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
            variable=self.log_to_file_only,
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
            variable=self.create_category_folders,
            command=self.save_organization_rules)

        # Generate summaries
        self.generate_summaries_check = ttk.Checkbutton(
            self.organization_rules_frame,
            text="Generate content summaries",
            variable=self.generate_summaries,
            command=self.save_organization_rules)

        # Include metadata
        self.include_metadata_check = ttk.Checkbutton(
            self.organization_rules_frame,
            text="Include metadata files",
            variable=self.include_metadata,
            command=self.save_organization_rules)

        # Copy instead of move
        self.copy_instead_check = ttk.Checkbutton(
            self.organization_rules_frame,
            text="Copy files instead of moving them",
            variable=self.copy_instead_of_move,
            command=self.save_organization_rules)

    def save_logging_settings(self):
        """Save logging settings to the settings manager"""
        try:
            log_to_file_only = self.log_to_file_only.get()
            self.settings_manager.set_setting(
                "log_to_file_only", log_to_file_only)
            self.settings_manager.save_settings()
            logger.info(f"Saved log_to_file_only setting: {log_to_file_only}")
        except Exception as e:
            logger.error(f"Error saving logging settings: {str(e)}")
            messagebox.showerror(
                "Error", f"Could not save logging settings: {str(e)}")

    def organize_files_thread(self, files, target_dir):
        """Thread function to organize files"""
        try:
            # Define progress callback for organization
            def organize_progress_callback(current, total, filename):
                percentage = int((current / total) * 100)
                self.status_queue.put(("progress", {
                    "processed": current,
                    "total": total,
                    "status": f"Organizing file: {os.path.basename(filename)}",
                    "percentage": percentage
                }))
                # Update organization-specific labels
                self.status_queue.put(
                    ("status", f"Organizing files ({percentage}%)"))

                # Check for cancellation
                return not self.cancel_requested

            # Get organization rules from the settings
            organization_options = {
                "create_category_folders": self.create_category_folders.get(),
                "generate_summaries": self.generate_summaries.get(),
                "include_metadata": self.include_metadata.get(),
                "copy_instead_of_move": self.copy_instead_of_move.get()
            }

            # Log the options being used
            logger.info(f"Organizing with options: {organization_options}")

            # Pass the callback and options to the organizer
            result = self.organizer.organize_files(
                files,
                target_dir,
                callback=organize_progress_callback,
                options=organization_options
            )

            if self.cancel_requested:
                self.status_queue.put(("cancelled", None))
            else:
                self.status_queue.put(
                    ("success", f"Successfully organized {result.get('organized_count', 0)} files"))

                # Show summary of the organization
                summary = f"Successfully organized {result['success']} files into {target_dir}\n\n"

                # Add details about the organization
                if organization_options['create_category_folders']:
                    summary += "Files were organized into category folders.\n"
                else:
                    summary += "Files were placed directly in the target directory.\n"

                if organization_options['generate_summaries']:
                    summary += "Content summaries were generated for each file.\n"

                if organization_options['include_metadata']:
                    summary += "AI analysis metadata was saved with each file.\n"

                if organization_options['copy_instead_of_move']:
                    summary += "Original files were preserved in their source location."
                else:
                    summary += "Files were moved from their source location."

                messagebox.showinfo("Organization Complete", summary)
        except Exception as e:
            logger.error(f"Error organizing files: {str(e)}")
            self.status_queue.put(
                ("error", f"Error organizing files: {str(e)}"))
        finally:
            self.is_organizing = False
            self.status_queue.put(("complete", None))

    def cancel_operation(self):
        """Cancel the current operation (scanning or organizing)"""
        if not self.is_scanning and not self.is_organizing:
            return

        self.cancel_requested = True
        self.status_queue.put(("status", "Cancelling operation..."))
        self.progress_details.config(text="Cancelling... Please wait")
        logger.info("User requested cancellation of current operation")

        # Disable the cancel button while cancellation is in progress
        self.cancel_button.config(state=tk.DISABLED)
