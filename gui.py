import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import threading
import queue
import time

from file_analyzer import FileAnalyzer
from file_organizer import FileOrganizer
from utils import get_readable_size, sanitize_filename

class DocumentOrganizerApp:
    def __init__(self, root):
        """
        Initialize the Document Organizer application GUI.
        
        Args:
            root: The tkinter root window
        """
        self.root = root
        self.source_dir = tk.StringVar()
        self.target_dir = tk.StringVar()
        self.search_term = tk.StringVar()
        self.analyzer = FileAnalyzer()
        self.organizer = FileOrganizer()
        self.status_queue = queue.Queue()
        self.is_scanning = False
        self.scanned_files = []
        
        # Set default directories (use raw strings for Windows paths)
        self.source_dir.set(os.path.expanduser(r"~\Documents"))
        self.target_dir.set(os.path.expanduser(r"~\Documents\Organized"))
        
        self._create_widgets()
        self._setup_layout()
        
        # Start the queue consumer
        self.consume_queue()
    
    def _create_widgets(self):
        """Create all the GUI widgets"""
        # Style configuration
        self.style = ttk.Style()
        self.style.configure("TButton", padding=6, font=('Segoe UI', 10))
        self.style.configure("TLabel", font=('Segoe UI', 10))
        self.style.configure("Header.TLabel", font=('Segoe UI', 12, 'bold'))
        self.style.configure("Status.TLabel", font=('Segoe UI', 10, 'italic'))
        
        # Frame for directory selection
        self.dir_frame = ttk.LabelFrame(self.root, text="Directory Selection", padding=(10, 5))
        
        # Source directory widgets
        self.source_label = ttk.Label(self.dir_frame, text="Source Directory:")
        self.source_entry = ttk.Entry(self.dir_frame, textvariable=self.source_dir, width=50)
        self.source_button = ttk.Button(self.dir_frame, text="Browse...", command=self.browse_source)
        
        # Target directory widgets
        self.target_label = ttk.Label(self.dir_frame, text="Target Directory:")
        self.target_entry = ttk.Entry(self.dir_frame, textvariable=self.target_dir, width=50)
        self.target_button = ttk.Button(self.dir_frame, text="Browse...", command=self.browse_target)
        
        # Scan button
        self.scan_button = ttk.Button(self.dir_frame, text="Scan Files", command=self.start_scan)
        
        # Status bar
        self.status_frame = ttk.Frame(self.root, padding=(10, 5))
        self.status_label = ttk.Label(self.status_frame, text="Ready", style="Status.TLabel")
        self.progress_bar = ttk.Progressbar(self.status_frame, mode='indeterminate', length=200)
        
        # File list frame
        self.files_frame = ttk.LabelFrame(self.root, text="Scanned Files", padding=(10, 5))
        
        # Search bar
        self.search_frame = ttk.Frame(self.files_frame, padding=(0, 5))
        self.search_label = ttk.Label(self.search_frame, text="Search:")
        self.search_entry = ttk.Entry(self.search_frame, textvariable=self.search_term, width=30)
        self.search_entry.bind("<KeyRelease>", self.search_files)
        
        # File treeview
        self.tree_columns = ("Filename", "Type", "Size", "Category", "Keywords")
        self.tree = ttk.Treeview(self.files_frame, columns=self.tree_columns, show='headings')
        
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
        self.tree_yscroll = ttk.Scrollbar(self.files_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.tree_yscroll.set)
        
        # File details frame
        self.details_frame = ttk.LabelFrame(self.root, text="File Details", padding=(10, 5))
        
        # File details
        self.details_text = ScrolledText(self.details_frame, wrap=tk.WORD, width=40, height=10)
        self.details_text.config(state=tk.DISABLED)
        
        # Bottom action frame
        self.action_frame = ttk.Frame(self.root, padding=(10, 5))
        self.organize_button = ttk.Button(self.action_frame, text="Organize Files", command=self.organize_files)
        
        # Bind tree selection event
        self.tree.bind("<<TreeviewSelect>>", self.show_file_details)
    
    def _setup_layout(self):
        """Setup the layout of widgets using grid"""
        # Directory frame
        self.dir_frame.grid(row=0, column=0, columnspan=2, sticky='ew', padx=10, pady=10)
        
        self.source_label.grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.source_entry.grid(row=0, column=1, sticky='ew', padx=5, pady=5)
        self.source_button.grid(row=0, column=2, sticky='e', padx=5, pady=5)
        
        self.target_label.grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.target_entry.grid(row=1, column=1, sticky='ew', padx=5, pady=5)
        self.target_button.grid(row=1, column=2, sticky='e', padx=5, pady=5)
        
        self.scan_button.grid(row=2, column=1, sticky='e', padx=5, pady=10)
        
        # Status frame
        self.status_frame.grid(row=3, column=0, columnspan=2, sticky='ew', padx=10, pady=(0, 10))
        self.status_label.grid(row=0, column=0, sticky='w')
        self.progress_bar.grid(row=0, column=1, sticky='e', padx=10)
        
        # Files frame
        self.files_frame.grid(row=1, column=0, sticky='nsew', padx=10, pady=10)
        
        self.search_frame.grid(row=0, column=0, sticky='ew')
        self.search_label.grid(row=0, column=0, sticky='w', padx=5)
        self.search_entry.grid(row=0, column=1, sticky='ew', padx=5)
        
        self.tree.grid(row=1, column=0, sticky='nsew')
        self.tree_yscroll.grid(row=1, column=1, sticky='ns')
        
        # Details frame
        self.details_frame.grid(row=1, column=1, sticky='nsew', padx=10, pady=10)
        self.details_text.pack(expand=True, fill='both', padx=5, pady=5)
        
        # Action frame
        self.action_frame.grid(row=2, column=0, columnspan=2, sticky='e', padx=10, pady=10)
        self.organize_button.pack(side=tk.RIGHT)
        
        # Configure grid weights
        self.root.grid_columnconfigure(0, weight=3)
        self.root.grid_columnconfigure(1, weight=2)
        self.root.grid_rowconfigure(1, weight=1)
        
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
            messagebox.showerror("Error", f"Source directory does not exist: {source_dir}")
            return
        
        # Clear previous results
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self.scanned_files = []
        self.is_scanning = True
        self.progress_bar.start(10)
        
        # Update status
        self.status_queue.put(("status", "Scanning files..."))
        
        # Start scanning thread
        scan_thread = threading.Thread(target=self.scan_files_thread, args=(source_dir,))
        scan_thread.daemon = True
        scan_thread.start()
    
    def scan_files_thread(self, directory):
        """Thread function to scan files"""
        try:
            files = self.analyzer.scan_directory(directory)
            self.status_queue.put(("files", files))
        except Exception as e:
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
                    # Update the progress indicator if needed
                    pass
                
                elif message_type == "files":
                    self.scanned_files = message
                    self.update_file_list(message)
                
                elif message_type == "error":
                    messagebox.showerror("Error", message)
                    self.is_scanning = False
                    self.progress_bar.stop()
                    self.status_label.config(text="Ready")
                
                elif message_type == "complete":
                    self.is_scanning = False
                    self.progress_bar.stop()
                    self.status_label.config(text=f"Completed scanning {len(self.scanned_files)} files")
                
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
        
        if 'summary' in file_info:
            details += f"\nSummary:\n{file_info.get('summary', '')}\n"
        
        if 'metadata' in file_info:
            details += "\nMetadata:\n"
            for key, value in file_info.get('metadata', {}).items():
                details += f"- {key}: {value}\n"
        
        self.details_text.insert(tk.END, details)
        self.details_text.config(state=tk.DISABLED)
    
    def organize_files(self):
        """Organize the files based on AI analysis"""
        if not self.scanned_files:
            messagebox.showinfo("Info", "No files to organize. Please scan files first.")
            return
        
        target_dir = self.target_dir.get()
        if not os.path.isdir(target_dir):
            try:
                os.makedirs(target_dir)
            except Exception as e:
                messagebox.showerror("Error", f"Could not create target directory: {str(e)}")
                return
        
        # Start organizing files
        self.status_label.config(text="Organizing files...")
        self.progress_bar.start(10)
        
        # Start organization thread
        organize_thread = threading.Thread(
            target=self.organize_files_thread, 
            args=(self.scanned_files, target_dir)
        )
        organize_thread.daemon = True
        organize_thread.start()
    
    def organize_files_thread(self, files, target_dir):
        """Thread function to organize files"""
        try:
            result = self.organizer.organize_files(files, target_dir)
            self.status_queue.put(("status", f"Organized {result['success']} files. {result['failed']} failed."))
            
            if result['failed'] > 0:
                failed_files = ", ".join(result['failed_files'][:5])
                if len(result['failed_files']) > 5:
                    failed_files += "..."
                self.status_queue.put(("error", f"Failed to organize some files: {failed_files}"))
            else:
                messagebox.showinfo("Success", f"Successfully organized {result['success']} files into {target_dir}")
        except Exception as e:
            self.status_queue.put(("error", f"Error organizing files: {str(e)}"))
        finally:
            self.status_queue.put(("complete", None))
