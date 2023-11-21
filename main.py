import os
import platform
import sys
import time
import tkinter as tk
import webbrowser
from datetime import datetime
from shutil import move
from tkinter import filedialog, font, messagebox

import pandas as pd
import requests
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from clams_processing import clean_all_clams_data, trim_all_clams_data, process_directory, recombine_columns, \
    reformat_csvs_in_directory

VERSION = "v1.0.4"


class StdoutRedirect:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self._stdout = sys.stdout

    def write(self, message):
        original_stdout = sys.stdout
        sys.stdout = self._stdout
        try:
            self.text_widget.insert(tk.END, message)
            self.text_widget.see(tk.END)  # Scroll to the end
            self._stdout.write(message)
            self.text_widget.see(tk.END)  # Scroll to the end
            self._stdout.flush()  # Flush the buffer
        except Exception as e:
            print(f"An exception occurred: {e}")
        finally:
            sys.stdout = original_stdout

    def flush(self):
        self._stdout.flush()


def check_for_update():
    current_version = VERSION
    repo_owner = 'PistilliLab'
    repo_name = 'CLAMSwrangler'  # Replace with your actual repo name
    url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest'

    response = requests.get(url)
    if response.status_code == 200:
        latest_release = response.json()
        latest_version = latest_release['tag_name']

        if latest_version != current_version:
            new_version = messagebox.askyesno('Update Available',
                                              f"CLAMS Wrangler {latest_version} is available. Update?")
            if new_version is True:
                webbrowser.open(latest_release['html_url'])
        else:
            messagebox.showinfo('No Update Available',
                                f"You are using the latest version of CLAMS Wrangler! ({VERSION})")
    else:
        print("Could not check for updates.")


def browse_working_directory():
    """Opens dialog window to select file path."""
    folder_selected = filedialog.askdirectory()
    directory_path_entry.delete(0, tk.END)
    directory_path_entry.insert(0, folder_selected)


def read_instructions(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError as e:
        print(f"An error occurred: {e}")
        return ""


def resource_path(relative_path):
    """Returns filepath """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def initialize_experiment_config_file(directory_path):
    # Create a folder for the config file
    config_file_path = os.path.join(directory_path, 'config')
    os.makedirs(config_file_path, exist_ok=True)

    # Path to the experiment configuration file
    config_file = os.path.join(config_file_path, 'experiment_config.csv')

    with open(config_file, 'w') as file:
        file.write("ID,GROUP LABEL\n")


def save_configuration(id_value, group_label_value, directory_path):
    # Check if the experiment configuration file exists
    experiment_config_file = os.path.join(directory_path, 'config/experiment_config.csv')
    if not os.path.exists(experiment_config_file):
        # Initialize a new experiment configuration file
        initialize_experiment_config_file(directory_path)

    # Path to the experiment configuration file
    config_file = os.path.join(directory_path, 'config', 'experiment_config.csv')

    # Write the ID and GROUP LABEL to the config file
    with open(config_file, 'a') as file:
        file.write(f"{id_value},{group_label_value}\n")

    # Display confirmation message in output_text
    confirmation_message = f"Configuration saved: ID = {id_value}, Group Label = {group_label_value}"
    output_text.insert(tk.END, confirmation_message + "\n")
    output_text.see(tk.END)  # Scroll to the end

    # Clear the entry boxes
    entry_id.delete(0, tk.END)
    entry_group_label.delete(0, tk.END)


def browse_config_file():
    """Opens dialog window to select a prebuilt config file and copy it to the config directory.
    """
    directory_path = directory_path_entry.get()
    # Check if the experiment configuration file exists
    experiment_config_file = os.path.join(directory_path, 'config/experiment_config.csv')
    if not os.path.exists(experiment_config_file):
        # Initialize a new experiment configuration file
        initialize_experiment_config_file(directory_path)

    selected_file = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
    if selected_file:
        experiment_config_file = selected_file  # Update the global variable
        # Display the selected file in the entry widget
        config_file_entry.delete(0, tk.END)
        config_file_entry.insert(0, experiment_config_file)

        # Check the format of the experiment configuration file
        try:
            config_df = pd.read_csv(experiment_config_file)
            expected_columns = ["ID", "GROUP LABEL"]
            if not all(col in config_df.columns for col in expected_columns):
                raise ValueError(
                    "The experiment configuration file does not have the expected columns: ID, GROUP LABEL")

            # Copy the selected file to the config directory
            config_directory = os.path.join(directory_path, 'config')
            config_file_dest = os.path.join(config_directory, 'experiment_config.csv')
            # We'll use pandas to copy the file while preserving the format
            config_df.to_csv(config_file_dest, index=False, columns=expected_columns)
            output_text.insert(tk.END, "Experiment configuration file copied to the config directory.\n")
        except pd.errors.EmptyDataError:
            # Handle the case where the file is empty
            output_text.insert(tk.END, "Error: Experiment configuration file is empty\n")
        except (pd.errors.ParserError, ValueError) as e:
            # Handle parsing errors or format mismatch
            output_text.insert(tk.END, f"Error: Invalid format in experiment configuration file: {str(e)}\n")


def log_user_input_and_output(input_values, output_text_content):
    """Log user input values and output text to a log file.

    Parameters:
    input_values (dict): Dictionary containing user input values.
    output_text_content (str): Content of the output_text widget.
    """
    # Create a timestamp for the log file
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    log_file_path = os.path.join(directory_path_entry.get(), 'config', f'log_{timestamp}.txt')

    with open(log_file_path, 'w') as log_file:
        # Write software version to the log file
        log_file.write(f"Data processed using CLAMS Wrangler {VERSION} on {timestamp}\n\n")
        # Write user input values to the log file
        log_file.write("User Input Values:\n")
        for key, value in input_values.items():
            log_file.write(f"{key}: {value}\n")

        # Write output_text content to the log file
        log_file.write("\nOutput Text:\n")
        log_file.write(output_text_content)


def main_process_clams_data():
    """Main function to process all CLAMS data files in the provided directory.

    Parameters:
    directory_path (string): directory containing .csv files to process
    trim_hours (int): number of hours to trim from the beginning of the cleaned data
    keep_hours (int): number of hours to keep in the trimmed data
    bin_hours (int): number of hours to bin the data

    Returns:
    Nothing. Prints progress and saves processed files to respective directories.
    """
    # handle directory errors
    try:
        directory_path = directory_path_entry.get()

        if not directory_path:
            output_text.insert(tk.END, "Directory path is not provided!\n")
            return
        elif not os.path.isdir(directory_path):
            output_text.insert(tk.END, "Provided path is not a valid directory!\n")
            return

    except ValueError as e:
        output_text.insert(tk.END, f"Error: {str(e)}\n")

    # handle trim hour errors
    try:
        trim_hours_str = trim_hours_entry.get()

        if not trim_hours_str:
            output_text.insert(tk.END, "Trim hours value is not provided!\n")
            return

        trim_hours = int(trim_hours_str)

    except ValueError as e:
        output_text.insert(tk.END, f"Error: {str(e)} Value must be a whole integer!\n")

    # this has a default value and can not be modified, so no need for error handling
    start_dark = start_cycle_var.get() == "Start Dark"

    # handle keep hours errors
    try:
        keep_hours_str = keep_hours_entry.get()

        if not keep_hours_str:
            output_text.insert(tk.END, "Keep hours value is not provided!\n")
            return

        keep_hours = int(keep_hours_str)

    except ValueError as e:
        output_text.insert(tk.END, f"Error: {str(e)} Value must be a whole integer!\n")

    # handle bin hours errors
    try:
        bin_hours_str = bin_hours_entry.get()

        if not bin_hours_str:
            output_text.insert(tk.END, "Bin hours value is not provided!\n")
            return

        bin_hours = int(bin_hours_str)

        # check if factor of 12
        if 12 % bin_hours != 0:
            output_text.insert(tk.END, f"Bin hours must be a factor of 12!\n")
            return

    except ValueError as e:
        output_text.insert(tk.END, f"Error: {str(e)} Value must be a whole integer!\n")

    # Redirect stdout to the output_text widget
    original_stdout = sys.stdout
    sys.stdout = StdoutRedirect(output_text)

    # Check if the experiment configuration file exists
    experiment_config_file = os.path.join(directory_path, 'config/experiment_config.csv')
    if not os.path.exists(experiment_config_file):
        # Initialize a new experiment configuration file
        initialize_experiment_config_file(directory_path)

        # Check if the user provided a config file to be copied
        selected_config_file = config_file_entry.get()
        if selected_config_file and os.path.exists(selected_config_file):
            try:
                # Read the selected config file
                config_df = pd.read_csv(selected_config_file)
                expected_columns = ["ID", "GROUP LABEL"]
                if all(col in config_df.columns for col in expected_columns):
                    # Copy the selected config file to the new experiment configuration file
                    config_directory = os.path.join(directory_path, 'config')
                    config_file_dest = os.path.join(config_directory, 'experiment_config.csv')
                    config_df.to_csv(config_file_dest, index=False, columns=expected_columns)
            except (pd.errors.EmptyDataError, pd.errors.ParserError, ValueError) as e:
                # Handle errors while reading/copying the selected config file
                output_text.insert(tk.END, f"Error copying config file: {str(e)}\n")

    output_text.insert("end", "\nCleaning all CLAMS data...\n")
    clean_all_clams_data(directory_path)

    output_text.insert("end", "\nTrimming all cleaned CLAMS data...\n")
    trim_all_clams_data(directory_path, trim_hours, keep_hours, start_dark)

    output_text.insert("end", "\nBinning all trimmed CLAMS data...\n")
    process_directory(directory_path, bin_hours)

    # Path to experiment config file
    experiment_config_file = os.path.join(directory_path, 'config/experiment_config.csv')

    output_text.insert("end", "\nCombining all binned CLAMS data...\n")
    recombine_columns(directory_path, experiment_config_file)

    output_text.insert("end", "\nReformatting all combined CLAMS data...\n")
    reformat_csvs_in_directory(os.path.join(directory_path, 'Combined_CLAMS_data'))

    output_text.insert("end", "\nAll CLAMS files processed successfully!")

    # Restore the original stdout
    sys.stdout = original_stdout

    # Log user input values and output text
    input_values = {
        "Directory Path": directory_path_entry.get(),
        "Trim Hours": trim_hours_entry.get(),
        "Start Cycle": start_cycle_var,
        "Keep Hours": keep_hours_entry.get(),
        "Bin Hours": bin_hours_entry.get(),
        "Config File": config_file_entry.get(),
    }
    output_text_content = output_text.get("1.0", tk.END)
    log_user_input_and_output(input_values, output_text_content)

    # Create a timestamped directory within the working directory
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    timestamped_dir = os.path.join(directory_path, f'timestamp_{timestamp}')
    os.makedirs(timestamped_dir, exist_ok=True)

    # Move the relevant folders to the timestamped directory
    folders_to_move = ['Binned_CLAMS_data', 'Cleaned_CLAMS_data', 'Combined_CLAMS_data', 'config', 'Trimmed_CLAMS_data']
    for folder in folders_to_move:
        source_folder = os.path.join(directory_path, folder)
        destination_folder = os.path.join(timestamped_dir, folder)
        move(source_folder, destination_folder)


# Create the main window
root = ttk.Window(themename="superhero")
root.title(f"CLAMS Wrangler {VERSION}")
root.minsize(width=1400, height=1000)

# error handling for not finding ico file on Windows
if os.path.exists(resource_path('CLAMS_icon.ico')) and platform.system() == "Windows":
    root.iconbitmap(resource_path('CLAMS_icon.ico'))
else:
    print("ICO file not found")

# for macOS
if os.path.exists(resource_path('CLAMS_icon.png')) and platform.system() == "Darwin":
    mac_icon = tk.PhotoImage(file=resource_path('CLAMS_icon.png'))
    root.iconphoto(True, mac_icon)
else:
    print("PNG file not found")

# for linux
if os.path.exists(resource_path('CLAMS_icon.png')):
    icon_image = tk.PhotoImage(file=resource_path('CLAMS_icon.png'))
    root.iconphoto(True, icon_image)
else:
    print("PNG file not found")

# Get the default font
default_font = font.nametofont("TkDefaultFont")

# Configure the default font
default_font.configure(size=12, family="Arial")

# Create a header frame for the logo
header_frame = ttk.Frame(root)
header_frame.pack(fill=tk.X)

# Add a logo (replace 'logo.png' with the path to your logo image)
logo_image = tk.PhotoImage(file=resource_path('logo.png'))
logo_label = ttk.Label(header_frame, image=logo_image)
logo_label.pack(side=tk.TOP, pady=10)

# Set the column weights for the header frame
header_frame.grid_columnconfigure(0, weight=4)
header_frame.grid_columnconfigure(1, weight=1)

main_frame = ttk.Frame(root)
main_frame.pack(fill=tk.BOTH, expand=True)

instructions_frame = ttk.Frame(main_frame)
instructions_frame.grid(row=0, column=0, padx=10, pady=10)

instructions_label = ttk.Label(instructions_frame, text="Instructions")
instructions_label.grid(row=0, column=0, pady=10)
instructions_text = tk.Text(instructions_frame, wrap=tk.WORD, width=60, height=30)
# instructions_text.pack()
instructions_text.grid(row=1, column=0)
instructions = read_instructions(resource_path('instructions.txt'))  # read in using read_instructions function at top
instructions_text.insert(tk.END, instructions)
instructions_text.config(state=tk.DISABLED)  # prevent editing

# Add citation label and text
citation_label = ttk.Label(instructions_frame, text="Please cite this software")
citation_label.grid(row=2, column=0, pady=10)
citation_text = tk.Text(instructions_frame, wrap=tk.WORD, width=60, height=5)
citation_text.grid(row=3, column=0, pady=10)
citation_text.insert(tk.END, f"Clayton, S. A., Mizener, A. D., & Rentz, L. E. (2023). CLAMS Wrangler ({VERSION}) "
                             "[Computer software]. https://github.com/PistilliLab/CLAMSwrangler")
citation_text.config(state=tk.DISABLED)

# Defines frame for user input
input_frame = ttk.Frame(main_frame)
input_frame.grid(row=0, column=1, padx=10, pady=10)
input_frame.grid_columnconfigure(1, weight=5)  # fill available space

directory_path_label = ttk.Label(input_frame, text="Directory Path:")
directory_path_label.grid(row=0, column=0, sticky=W, padx=2, pady=2)
browse_button = ttk.Button(input_frame, text="Browse", width=10, command=browse_working_directory)
browse_button.grid(row=0, column=2, sticky=E, padx=2, pady=2)
directory_path_entry = ttk.Entry(input_frame, width=75)
directory_path_entry.grid(row=0, column=1, sticky=EW, padx=2, pady=2)

trim_hours_label = ttk.Label(input_frame, text="Trim Hours:")
trim_hours_label.grid(row=1, column=0, sticky=EW, padx=2, pady=2)
start_cycle_var = tk.StringVar()
start_cycle_dropdown = ttk.Combobox(input_frame, textvariable=start_cycle_var, values=["Start Light", "Start Dark"],
                                    width=8, state="readonly")
start_cycle_var.set("Start Light")
start_cycle_dropdown.grid(row=1, column=2, sticky=EW, padx=1, pady=2)
trim_hours_entry = ttk.Entry(input_frame, width=75)
trim_hours_entry.grid(row=1, column=1, sticky=EW, padx=2, pady=2)

keep_hours_label = ttk.Label(input_frame, text="Keep Hours:")
keep_hours_label.grid(row=2, column=0, sticky=EW, padx=2, pady=2)
keep_hours_entry = ttk.Entry(input_frame, width=75)
keep_hours_entry.grid(row=2, column=1, sticky=EW, padx=2, pady=2)

bin_hours_label = ttk.Label(input_frame, text="Bin Hours:")
bin_hours_label.grid(row=3, column=0, sticky=EW, padx=2, pady=2)
bin_hours_entry = ttk.Entry(input_frame, width=75)
bin_hours_entry.grid(row=3, column=1, sticky=EW, padx=2, pady=2)

config_file_label = ttk.Label(input_frame, text="Config File:")
config_file_label.grid(row=4, column=0, sticky=EW, padx=2, pady=2)
btn_browse_config = ttk.Button(input_frame, text="Browse", width=10, command=browse_config_file)
btn_browse_config.grid(row=4, column=2, sticky=EW, padx=2, pady= 2)
config_file_entry = ttk.Entry(input_frame, width=75)
config_file_entry.grid(row=4, column=1, sticky=EW, padx=2, pady=2)

label_id = ttk.Label(input_frame, text="ID:")
label_id.grid(row=5, column=0, sticky=EW, padx=2, pady=2)
entry_id = ttk.Entry(input_frame, width=75)
entry_id.grid(row=5, column=1, sticky=EW, padx=2, pady=2)

label_group_label = ttk.Label(input_frame, text="Group Label:")
label_group_label.grid(row=6, column=0, sticky=EW, padx=2, pady=2)
entry_group_label = ttk.Entry(input_frame, width=75)
entry_group_label.grid(row=6, column=1, sticky=EW, padx=2, pady=2)

# Add "Add Label" button
btn_add_config = ttk.Button(input_frame, text="Add Label",
                            command=lambda: save_configuration(entry_id.get(), entry_group_label.get(),
                                                               directory_path_entry.get()))
btn_add_config.grid(row=7, column=1, padx=2, pady=2)

output_text = ttk.Text(input_frame, wrap=tk.WORD, width=100, height=20)
output_text.grid(row=8, column=0, columnspan=3, padx=10, pady=10)

start_button = ttk.Button(input_frame, text="Start Processing", command=main_process_clams_data)
start_button.grid(row=9, column=0, columnspan=3, padx=10, pady=10)

# Set weights for rescaling window
main_frame.grid_rowconfigure(0, weight=1)
main_frame.grid_columnconfigure(0, weight=1)
main_frame.grid_columnconfigure(1, weight=3)

instructions_frame.grid_rowconfigure(0, weight=1)
instructions_frame.grid_columnconfigure(0, weight=1)

input_frame.grid_rowconfigure(0, weight=1)
input_frame.grid_rowconfigure(1, weight=1)
input_frame.grid_rowconfigure(2, weight=1)
input_frame.grid_rowconfigure(3, weight=1)
input_frame.grid_rowconfigure(4, weight=1)
input_frame.grid_rowconfigure(5, weight=3)
input_frame.grid_columnconfigure(0, weight=1)

# Create a footer frame for the credits
footer_frame = ttk.Frame(root)
footer_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=5)

# Add credits text
credits_text = (f"{VERSION} Developed by the Pistilli Lab. Credits: Alan Mizener, Stuart Clayton, Lauren Rentz. "
                f"Visit github.com/PistilliLab")
credits_label = ttk.Label(footer_frame, text=credits_text, state="readonly")
credits_label.pack(side=tk.LEFT, padx=10)

# Add Exit button
exit_button = ttk.Button(footer_frame, text="Exit", command=root.quit, bootstyle=DANGER)
exit_button.pack(side=tk.RIGHT, padx=10)

# Add "Check for Updates" button
update_button = ttk.Button(footer_frame, text="Check for Updates", command=check_for_update)
update_button.pack(side=tk.RIGHT, padx=10)


root.mainloop()
