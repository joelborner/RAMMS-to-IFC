import tkinter as tk
from tkinter import ttk, filedialog
import ramms_to_ifc

class GapSection:
    def __init__(self, master):
        self.master = master

        self.options_frame = tk.Frame(self.master)
        self.options_frame.pack(side=tk.TOP, padx=10, pady=10, fill=tk.BOTH)

        self.scale_label = tk.Label(self.options_frame, text="Gap Length [m]")
        self.scale_label.pack(side=tk.TOP, pady=(10, 5))

        self.scale_var = tk.DoubleVar()
        self.scale_var.set(2.0)

        self.scale = tk.Scale(
            self.options_frame,
            from_=0.1,
            to=10.0,
            length=500,
            resolution=0.1,
            orient=tk.HORIZONTAL,
            variable=self.scale_var
        )
        self.scale.pack(side=tk.TOP, padx=10)


class FileSelector:
    def __init__(self, master):
        self.file_path = None
        self.master = master
        master.title("IFC Converter for RAMMS::Rockfall Trajectories")
        master.geometry("600x600")
        master.resizable(False, False)

        self.selected_files = []

        # File section
        file_label_frame = ttk.LabelFrame(master, text="Select files", padding=(10, 10))
        file_label_frame.pack(fill="both", padx=10, pady=10)
        self.file_box = tk.Listbox(file_label_frame, height=5, width=85)
        self.file_box.pack(side="left", padx=10, pady=10, fill="both")
        scrollbar = ttk.Scrollbar(file_label_frame, orient="vertical", command=self.file_box.yview)
        scrollbar.pack(side="right", fill="y")
        self.file_box.configure(yscrollcommand=scrollbar.set)
        browse_button_frame = ttk.Frame(master)
        browse_button_frame.pack(pady=10)
        self.browse_button = ttk.Button(browse_button_frame, text="Browse", command=self.browse_files)
        self.browse_button.pack(side="left", padx=10)

        # Rock section
        rock_label_frame = ttk.LabelFrame(master, text="Select Rock", padding=(10, 10))
        rock_label_frame.pack(fill="both", padx=10, pady=10)
        self.rock_box = tk.Listbox(rock_label_frame, height=1, width=70)
        self.rock_box.pack(side="left", padx=10, pady=10, fill="both")
        self.browse_button = ttk.Button(rock_label_frame, text="Browse", command=self.browse_rock)
        self.browse_button.pack(side="left", padx=10)

        # Gap section
        self.gap_section = GapSection(self.master)

        # Option section
        option_label_frame = ttk.LabelFrame(master, text="Color Options", padding=(10, 10))
        option_label_frame.pack(fill="both", padx=10, pady=10)
        self.option_var = tk.IntVar(value=1)
        self.option1_button = ttk.Radiobutton(option_label_frame, text="Uniform Color", variable=self.option_var,
                                              value=1)
        self.option1_button.pack(side="left", padx=10, pady=5, expand=True)
        self.option2_button = ttk.Radiobutton(option_label_frame, text="Kinetic Energy Colorbar",
                                              variable=self.option_var,
                                              value=2)
        self.option2_button.pack(side="left", padx=10, pady=5, expand=True)
        self.option3_button = ttk.Radiobutton(option_label_frame, text="Jump Height Colorbar", variable=self.option_var,
                                              value=3)
        self.option3_button.pack(side="left", padx=10, pady=5, expand=True)

        # Start button
        start_button_frame = ttk.Frame(master)
        start_button_frame.pack(pady=10)
        self.start_button = ttk.Button(start_button_frame, text="Convert to IFC", command=self.start)
        self.start_button.pack()

        self.status_label=tk.Label(self.master, text="")
        self.status_label.pack(side=tk.TOP, pady=(10, 0))

    def browse_files(self):
        files = filedialog.askopenfilenames(filetypes=[("Trajectory Files", "*.rts")])
        for file in files:
            self.selected_files.append(file)
            self.file_box.insert(tk.END, file)

    def browse_rock(self):
        file_types = [("Rock File", "*.pts")]
        self.file_path = filedialog.askopenfilename(filetypes=file_types)
        self.rock_box.delete(0, tk.END)
        self.rock_box.insert(tk.END, self.file_path)

    def start(self):
        trajectory_data = []
        if self.file_path and len(self.selected_files) > 0:
            self.status_label.config(
                text="Converting...")
            for file in self.selected_files:
                rock_mass, data = ramms_to_ifc.read_rts(file)
                trajectory_data.append([rock_mass, ("Pos" + file.split("_Pos")[1]).split(".rts")[0], data])
            ramms_to_ifc.ramms_to_ifc(self.selected_files[0].split("_Pos")[0].split("/")[-1], trajectory_data, self.gap_section.scale_var.get(), self.file_path, self.option_var.get())
            self.status_label.config(
                text="Successfully converted " + str(len(self.selected_files)) + " trajectories to IFC")
        else:
            self.status_label.config(
                text="Please select a rock file and at least one trajectory.")


root = tk.Tk()
style = ttk.Style(root)
style.theme_use("winnative")
my_gui = FileSelector(root)
root.mainloop()
