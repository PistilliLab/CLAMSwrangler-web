import glob
import os
import re
import shutil
from datetime import timedelta

import numpy as np
import pandas as pd

# Global variable to hold the list of experiment IDs
experiment_ids = []

def identify_ids_from_config_file(experiment_config_file):
    """
    Reads the experiment configuration CSV file and extracts a list of unique IDs.

    Parameters:
        experiment_config_file (str): Path to the experiment config CSV file.
                                     The file is expected to have a header with at least
                                     the columns 'ID' and 'GROUP_LABEL'.

    Returns:
        list: A list of unique IDs from the configuration file.
    """
    global experiment_ids
    try:
        config_df = pd.read_csv(experiment_config_file)
    except Exception as e:
        print(f"Error reading experiment config file: {e}")
        return []

    if 'ID' not in config_df.columns:
        print("The config file does not contain an 'ID' column.")
        return []

    # Extract unique IDs; depending on your file these may be ints or strings.
    experiment_ids = config_df['ID'].unique().tolist()
    print(experiment_ids)
    return experiment_ids


def merge_fragmented_runs_by_id(path_to_original_csv_files):
    """
    For each CSV file in the provided directory, identify the animal (using the line containing 'Subject ID'),
    group files by that animal, and then merge them in run order. For each animal:

      - If only one file exists, copy it to the output directory.
      - If multiple files exist, choose the earliest file (based on file modification time) as the base file,
        keeping its header. Then, for each subsequent file, extract only the data rows (assumed to start at row 26)
        and (optionally) stop reading if the value in the INTERVAL column does not continue consecutively.

    The merged (or copied) files are written to a new directory named "Aggregated_Runs" inside path_to_original_csv_files.
    """

    # Create an output directory for aggregated files
    output_dir = os.path.join(path_to_original_csv_files, "Aggregated_Runs")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Get a list of all CSV files in the directory
    csv_files = glob.glob(os.path.join(path_to_original_csv_files, "*.csv"))

    # Group files by Subject ID (extracted from the metadata line that contains "Subject ID")
    files_by_id = {}
    for file_path in csv_files:
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            continue

        subject_id = None
        # Look for a line containing "Subject ID"
        for line in lines:
            if "Subject ID" in line:
                # Assumes the line is formatted like: "Subject ID, <id>"
                parts = line.strip().split(',')
                if len(parts) >= 2:
                    subject_id = parts[1].strip()
                break
        if subject_id is None:
            print(f"Could not find Subject ID in {file_path}; skipping.")
            continue

        files_by_id.setdefault(subject_id, []).append(file_path)

    # Process each subject (animal) group
    for subject_id, file_list in files_by_id.items():
        # Sort files by modification time (as a proxy for run order)
        file_list.sort(key=lambda x: os.path.getmtime(x))

        if len(file_list) == 1:
            # If only one file exists, simply copy it to the output directory.
            dest = os.path.join(output_dir, os.path.basename(file_list[0]))
            shutil.copy(file_list[0], dest)
            print(f"Copied single file for Subject ID {subject_id} to {dest}")
        else:
            print(f"Merging {len(file_list)} files for Subject ID {subject_id} ...")

            # Use the earliest file as the base (keeping its header and full content)
            earliest_file = file_list[0]
            with open(earliest_file, 'r') as f:
                aggregated_lines = f.readlines()

            # --- Determine the column order from the base file's header ---
            # (Search the header lines for one that contains "INTERVAL")
            header_line_index = None
            header_columns = None
            for i, line in enumerate(aggregated_lines):
                if "INTERVAL" in line:
                    header_line_index = i
                    header_columns = line.strip().split(',')
                    break
            if header_line_index is None:
                print(f"Warning: No header with 'INTERVAL' found in {earliest_file}. Will not do interval checking.")
                interval_col_index = None
            else:
                try:
                    interval_col_index = header_columns.index("INTERVAL")
                except ValueError:
                    print(f"Warning: 'INTERVAL' column not found in header of {earliest_file}.")
                    interval_col_index = None

            # For subsequent files, we assume that the data portion begins at row 26
            HEADER_LINES_TO_SKIP = 25  # (i.e. skip the first 25 lines; row 26 is index 25)

            # Optionally, find the last interval from the base file (if available) to help check continuity
            last_interval = None
            for line in reversed(aggregated_lines):
                if not line.strip():
                    continue
                parts = line.strip().split(',')
                if interval_col_index is not None and len(parts) > interval_col_index:
                    try:
                        last_interval = int(parts[interval_col_index])
                        break
                    except ValueError:
                        continue

            # Helper: process data rows from a file based on consecutive intervals.
            def extract_data_lines(lines, interval_index):
                data_rows = []
                file_last_interval = None
                for line in lines:
                    if not line.strip():
                        continue
                    parts = line.strip().split(',')
                    if len(parts) <= interval_index:
                        continue
                    try:
                        current_interval = int(parts[interval_index])
                    except ValueError:
                        # If we can’t convert the interval to an int, assume it’s not a data row.
                        continue
                    if file_last_interval is None:
                        # For the very first data row of this file, we accept it (even if it does not
                        # continue from the previous file’s last interval—sometimes the run restarts).
                        data_rows.append(line)
                        file_last_interval = current_interval
                    else:
                        if current_interval == file_last_interval + 1:
                            data_rows.append(line)
                            file_last_interval = current_interval
                        else:
                            # When the sequence breaks, assume the data portion is finished.
                            break
                return data_rows, file_last_interval

            # Process every subsequent file and append its data rows
            for file_path in file_list[1:]:
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                if len(lines) <= HEADER_LINES_TO_SKIP:
                    print(f"File {file_path} does not have enough lines to contain data; skipping.")
                    continue

                # Grab all lines after the first 25 (i.e. starting at row 26)
                candidate_data = lines[HEADER_LINES_TO_SKIP:]

                if interval_col_index is not None:
                    filtered_data, file_last_interval = extract_data_lines(candidate_data, interval_col_index)
                    # (If desired, one might check whether the first row of this file is the expected continuation.)
                    if last_interval is not None and filtered_data:
                        try:
                            first_interval = int(filtered_data[0].strip().split(',')[interval_col_index])
                            if first_interval != last_interval + 1:
                                # Here you could decide to adjust the intervals or simply note a discontinuity.
                                # For now, we simply print a warning.
                                print(
                                    f"Warning: For file {file_path}, first interval ({first_interval}) does not continue from previous last interval ({last_interval}).")
                        except ValueError:
                            pass
                    # Update last_interval (if any data was found)
                    if file_last_interval is not None:
                        last_interval = file_last_interval
                    aggregated_lines.extend(filtered_data)
                else:
                    # If we couldn’t identify the INTERVAL column, simply append all candidate data lines.
                    aggregated_lines.extend(candidate_data)

            # Write the aggregated output to a new file
            out_filename = os.path.join(output_dir, f"Aggregated_ID{subject_id}.csv")
            with open(out_filename, 'w') as f:
                f.writelines(aggregated_lines)
            print(f"Aggregated file for Subject ID {subject_id} written to {out_filename}")


def align_dates(path_to_merged_csv_files):
    """This function will align the dates so all the runs appear to have been started at the same time. For the
    reformatting our code does, this is not necessary. But for CalR and visualization in that, it is necessary."""
    pass


def make_channel_unique(path_to_aligned_csv_files):
    """This could be done at any point after everything is combined. But if I recall correctly, Calr assumes that
    each animal is in a unique channel. So when multiple runs are combined, they may overlap and it trys to
    combine them or isn't sure what to do. However, I don't know if it's expecting channels within a certain range
    either, so will have to try combining and running in Calr to see."""


def clean_all_clams_data(directory_path):
    """Reformat all CLAMS data files (.csv) in the provided directory by dropping unnecessary rows.

    Parameters:
    directory_path (string): directory containing .csv files to clean

    Returns:
    Nothing. Prints new filenames saved to "Cleaned_CLAMS_data" directory.
    """

    def clean_file(file_path, output_directory):
        """Helper function to clean individual file."""
        # Read the file as plain text to extract metadata
        with open(file_path, 'r') as f:
            lines = f.readlines()

        # Extract the "Subject ID" value
        for line in lines:
            if 'Subject ID' in line:
                subject_id = line.split(',')[1].strip()
                break

        # Read the data chunk of the CSV file
        df = pd.read_csv(file_path, skiprows=range(0, 22))

        # Drop additional 2 formatting rows
        df.drop([0, 1], inplace=True)

        # Construct the new file name
        file_name = os.path.basename(file_path)
        base_name, ext = os.path.splitext(file_name)
        ext = ext.lower()
        new_file_name = f"{base_name}_ID{subject_id}{ext}"

        # Save the cleaned data to the new directory
        output_path = os.path.join(output_directory, new_file_name)
        df.to_csv(output_path, index=False)
        print(f"Cleaning {file_name}")

    # Create the output directory if it doesn't exist
    output_directory = os.path.join(directory_path, "Cleaned_CLAMS_data")
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

        # Process all CSV files in the directory, regardless of extension case
        csv_pattern = re.compile(r"\.csv$", re.IGNORECASE)
        all_files = glob.iglob(os.path.join(directory_path, "*"))
        csv_files = [file_path for file_path in all_files if csv_pattern.search(file_path)]

        for file_path in csv_files:
            clean_file(file_path, output_directory)


def quality_control(directory_path):
    """
    Performs quality control on each CSV file in the "Cleaned_CLAMS_data" folder
    inside the provided parent directory. Rows that fail quality standards are dropped
    according to these rules:

      1. If any of the columns "VO2", "VCO2", "RER", "FLOW", or "PRESSURE" are equal to 0,
         the row is dropped.
      2. If "O2IN" is less than 20.85, the row is dropped.
      3. If "VO2" is negative or equal to 0, the row is dropped.

    The quality-controlled files are saved into a subdirectory named "QC_Filtered" within the
    provided parent directory.

    Parameters:
        directory_path (str): The parent directory containing the "Cleaned_CLAMS_data" folder.
    """

    # Create an output directory for quality-controlled files
    qc_dir = os.path.join(directory_path, "QC_Filtered")
    if not os.path.exists(qc_dir):
        os.makedirs(qc_dir)

    # Get the path to the cleaned data files
    cleaned_directory = os.path.join(directory_path, "Cleaned_CLAMS_data")

    # List all CSV files in the cleaned data folder
    csv_files = [f for f in os.listdir(cleaned_directory)
                 if os.path.isfile(os.path.join(cleaned_directory, f)) and f.endswith('.csv')]

    for file in csv_files:
        # Build the full file path before reading it
        file_path = os.path.join(cleaned_directory, file)
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            continue

        # Check that the required columns exist
        required_cols = ["VO2", "VCO2", "RER", "FLOW", "PRESSURE", "O2IN"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            print(f"Skipping {file} because the following required columns are missing: {missing_cols}")
            continue

        # Apply the quality conditions:
        # 1. Columns VO2, VCO2, RER, FLOW, and PRESSURE must not be 0.
        cond1 = (df["VO2"] != 0) & (df["VCO2"] != 0) & (df["RER"] != 0) & (df["FLOW"] != 0) & (df["PRESSURE"] != 0)
        # 2. O2IN must be at least 20.85.
        cond2 = df["O2IN"] >= 20.85
        # 3. VO2 must be greater than 0.
        cond3 = df["VO2"] > 0

        # Combined quality condition
        quality_mask = cond1 & cond2 & cond3
        df_qc = df[quality_mask].copy()

        # Save the quality-controlled file to the QC_Filtered directory.
        out_filename = os.path.join(qc_dir, file)
        try:
            df_qc.to_csv(out_filename, index=False)
            dropped_rows = len(df) - len(df_qc)
            print(f"Processed '{file}': dropped {dropped_rows} rows; saved QC file to '{out_filename}'.")
        except Exception as e:
            print(f"Error writing quality-controlled file for {file}: {e}")


def trim_all_clams_data(directory_path, trim_hours, keep_hours, start_dark):
    """Trims all cleaned CLAMS data files in the specified directory.

    Parameters:
    directory_path (string): path to the directory containing cleaned .csv files
    trim_hours (int): number of hours to trim from the beginning
    keep_hours (int): number of hours to keep in the resulting file

    Returns:
    Nothing. Saves the trimmed data to new CSV files in the "Trimmed_CLAMS_data" directory.
    """

    # Create a new directory for trimmed files if it doesn't exist
    trimmed_directory = os.path.join(directory_path, "Trimmed_CLAMS_data")
    if not os.path.exists(trimmed_directory):
        os.makedirs(trimmed_directory)

    # Get the path to the cleaned data files
    qc_directory = os.path.join(directory_path, "QC_Filtered")

    # List all files in the directory
    files = [f for f in os.listdir(qc_directory) if
             os.path.isfile(os.path.join(qc_directory, f)) and f.endswith('.csv')]

    for file in files:
        file_path = os.path.join(qc_directory, file)

        # Read the cleaned CSV file
        df = pd.read_csv(file_path)

        # Convert the 'DATE/TIME' column to datetime format
        df['DATE/TIME'] = pd.to_datetime(df['DATE/TIME'], errors='coerce')

        # Calculate the starting timestamp after trimming
        start_index = df[df['DATE/TIME'] >= df['DATE/TIME'].iloc[0] + timedelta(hours=trim_hours)].index[0]

        # Note the value in the "LED LIGHTNESS" column after trimming
        initial_led_value = df['LED LIGHTNESS'].iloc[start_index]

        # Find the index of the next change in the "LED LIGHTNESS" value
        while df['LED LIGHTNESS'].iloc[start_index] == initial_led_value:
            start_index += 1

        # Determine if the 1st light change does not match the cycle specified by the user and adjust start_index to the next light change if necessary
        if (start_dark and df['LED LIGHTNESS'].iloc[start_index] != 0) or (not start_dark and df['LED LIGHTNESS'].iloc[start_index] == 0):
            initial_led_value = df['LED LIGHTNESS'].iloc[start_index]
            while df['LED LIGHTNESS'].iloc[start_index] == initial_led_value:
                start_index += 1

        # Zero columns that contain accumulative variables to appropriately account for variable trimming times
        columns_to_zero = ['ACCO2', 'ACCCO2', 'FEED1 ACC', 'WHEEL ACC']
        for col in columns_to_zero:
                df[col] = (df[col] - df[col].iloc[start_index - 1]).round(2)

        # Calculate the ending timestamp
        end_time = df['DATE/TIME'].iloc[start_index] + timedelta(hours=keep_hours)

        # Filter the dataframe from calculated start_index to end_time
        df_result = df[(df.index >= start_index) & (df['DATE/TIME'] <= end_time)]

        # Save the resulting data to a new CSV file in the "Trimmed_CLAMS_data" directory
        file_name = os.path.basename(file_path)
        base_name, ext = os.path.splitext(file)
        ext = ext.lower()
        new_file_name = os.path.join(trimmed_directory, f"{base_name}_trimmed{ext}")
        df_result.to_csv(new_file_name, index=False)
        print(f"Trimming {file_name}")


def bin_clams_data(file_path, bin_hours):
    df = pd.read_csv(file_path)
    bin_hours = int(bin_hours)

    # Convert 'DATE/TIME' column to datetime format
    df['DATE/TIME'] = pd.to_datetime(df['DATE/TIME'])

    # Drop unnecessary columns
    columns_to_drop = ["STATUS1", "O2IN", "O2OUT", "DO2", "CO2IN", "CO2OUT", "DCO2", "XTOT", "YTOT", "LED HUE",
                       "LED SATURATION", "BIN"]
    df = df.drop(columns=columns_to_drop, errors='ignore')

    # Add AMB & AMB ACC columns to the original dataframe
    df['AMB'] = df['XAMB'] + df['YAMB']
    df['AMB ACC'] = df['AMB'].cumsum()

    # Create a new column for bin labels
    df['BIN'] = np.nan

    # For each unique "LED LIGHTNESS" value, assign bin labels
    for led_value in df['LED LIGHTNESS'].unique():
        subset = df[df['LED LIGHTNESS'] == led_value].copy()
        start_time = subset['DATE/TIME'].iloc[0]
        bin_label = 0
        bin_labels = []

        for timestamp in subset['DATE/TIME']:
            if (timestamp - start_time) >= timedelta(hours=bin_hours):
                bin_label += 1
                start_time = timestamp
            bin_labels.append(bin_label)

        df.loc[subset.index, 'BIN'] = bin_labels

    # Columns to retain the last value in the bin
    last_val_columns = ["INTERVAL", "CHAN", "DATE/TIME", "ACCO2", "ACCCO2", "FEED1 ACC", "WHEEL ACC", "AMB ACC"]

    # Columns to sum within the bin
    sum_columns = ["WHEEL", "FEED1", "AMB"]

    # Columns to average (excluding the ones we're taking the last value or summing)
    avg_columns = df.columns.difference(last_val_columns + sum_columns + ['BIN', 'LED LIGHTNESS'])

    # Group by "LED LIGHTNESS" and "BIN" and calculate the mean, sum, or last value as appropriate
    df_binned = df.groupby(['LED LIGHTNESS', 'BIN']).agg({**{col: 'last' for col in last_val_columns},
                                                          **{col: 'mean' for col in avg_columns},
                                                          **{col: 'sum' for col in sum_columns}}).reset_index()

    # Add start and end time columns
    start_times = df.groupby(['LED LIGHTNESS', 'BIN'])['DATE/TIME'].first().reset_index(name='DATE/TIME_start')
    end_times = df.groupby(['LED LIGHTNESS', 'BIN'])['DATE/TIME'].last().reset_index(name='DATE/TIME_end')
    df_binned = pd.merge(df_binned, start_times, on=['LED LIGHTNESS', 'BIN'])
    df_binned = pd.merge(df_binned, end_times, on=['LED LIGHTNESS', 'BIN'])

    # Add start and end interval columns
    start_intervals = df.groupby(['LED LIGHTNESS', 'BIN'])['INTERVAL'].first().reset_index(name='INTERVAL_start')
    end_intervals = df.groupby(['LED LIGHTNESS', 'BIN'])['INTERVAL'].last().reset_index(name='INTERVAL_end')
    df_binned = pd.merge(df_binned, start_intervals, on=['LED LIGHTNESS', 'BIN'])
    df_binned = pd.merge(df_binned, end_intervals, on=['LED LIGHTNESS', 'BIN'])

    # Calculate the duration of each bin in hours
    df_binned['DURATION'] = (df_binned['DATE/TIME_end'] - df_binned['DATE/TIME_start']).dt.total_seconds() / 3600

    # Drop rows with a duration of 0
    df_binned = df_binned[df_binned['DURATION'] != 0]

    # Drop existing BIN column & sort based on INTERVAL_start
    df_binned = df_binned.sort_values(by='INTERVAL_start')

    # Add a DAY column
    df_binned['DAY'] = (df_binned['BIN'] // (12 / bin_hours) + 1).astype(int)

    # Reset index and add a new 'HOUR' column starting from 1
    df_binned.reset_index(drop=True, inplace=True)
    df_binned['HOUR'] = df_binned.index

    # Add DAILY_BIN column
    df_binned['24 HOUR'] = df_binned['HOUR'] % ( 24 // bin_hours)

    # Convert HOUR & 24 HOUR columns to time
    df_binned['HOUR'] = (df_binned['HOUR'] + 1) * bin_hours
    df_binned['24 HOUR'] = (df_binned['24 HOUR'] + 1) * bin_hours

    # Reorder columns based on your request
    desired_order = ["CHAN", "INTERVAL_start", "INTERVAL_end", "DATE/TIME_start", "DATE/TIME_end", "DURATION",
                     "VO2", "ACCO2", "VCO2", "ACCCO2", "RER", "HEAT", "FLOW", "PRESSURE", "FEED1", "FEED1 ACC",
                     "AMB", "AMB ACC", "WHEEL", "WHEEL ACC", "ENCLOSURE TEMP", "ENCLOSURE SETPOINT", "LED LIGHTNESS", "DAY", "HOUR", "24 HOUR"]
    df_binned = df_binned[desired_order]

    # Round all variables to 4 decimal places
    df_binned = df_binned.round(4)

    # Save the binned data to a new CSV file
    output_path = file_path.replace(
        "Trimmed_CLAMS_data", f"{bin_hours}hour_bins_Binned_CLAMS_data"
    ).replace(
        ".csv", f"_{bin_hours}hour_bins.csv"
    )

    # Check if the directory exists, if not, create it
    output_directory = os.path.dirname(output_path)
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    df_binned.to_csv(output_path, index=False)


def process_directory(directory_path, bin_hours):
    # Get path to trimmed directory
    trimmed_directory = os.path.join(directory_path, "Trimmed_CLAMS_data")

    # Get a list of all .CSV files in the directory
    csv_files = [f for f in os.listdir(trimmed_directory) if
                 f.endswith('.csv') and os.path.isfile(os.path.join(trimmed_directory, f))]

    # Process each .CSV file
    for csv_file in csv_files:
        file_path = os.path.join(trimmed_directory, csv_file)
        bin_clams_data(file_path, bin_hours)
        print(f"Binning {csv_file}")


def extract_id_number(filename):
    # Extract the ID number from the filename
    match = re.search(r'ID(\d+)', filename)
    if match:
        return match.group(1)
    else:
        return None


def recombine_columns(directory_path, experiment_config_file, bin_hours):
    # Use bin_hours to create a directory for each binned version
    bin_hours = int(bin_hours)

    # Define Combined CLAMS data directory for each bin window
    combined_directory = os.path.join(directory_path, f"{bin_hours}hour_bins_Combined_CLAMS_data")
    if not os.path.exists(combined_directory):
        os.makedirs(combined_directory)

    # Define input directory
    input_directory = os.path.join(directory_path, f"{bin_hours}hour_bins_Binned_CLAMS_data")

    # Desired output variables
    output_variables = ['ACCCO2', 'ACCO2', 'FEED1 ACC', 'FEED1', 'RER', 'AMB', 'AMB ACC', 'VCO2', 'VO2', 'WHEEL ACC', 'WHEEL']

    # Define columns to include in the output
    selected_columns = ['ID', 'GROUP_LABEL', 'DAY', 'HOUR', '24 HOUR'] + output_variables

    # Read the experiment configuration
    config_df = pd.read_csv(experiment_config_file)
    print(f'CONFIGRESULTS: {config_df.columns}')

    # Create an empty DataFrame to store the combined data
    combined_data = pd.DataFrame(columns=selected_columns)

    # Loop through all files in the specified directory
    for filename in os.listdir(input_directory):
        if filename.endswith(".csv"):
            file_path = os.path.join(input_directory, filename)
            # Read the current .csv file into a DataFrame
            df = pd.read_csv(file_path)

            # Get the 'ID' number from the file name
            file_id = extract_id_number(filename)

            # Find the GROUP_LABEL for the current ID
            group_label = config_df[config_df['ID'] == int(file_id)]['GROUP_LABEL'].values
            if len(group_label) > 0:
                group_label = group_label[0]
            else:
                group_label = ""

            # Add columns 'ID', 'DAY', 'HOUR', '24 HOUR'
            df['ID'] = file_id
            df['GROUP_LABEL'] = group_label
            df['DAY'] = df['DAY'].astype(int)
            df['HOUR'] = df['HOUR'].astype(int)
            df['24 HOUR'] = df['24 HOUR'].astype(int)

            # Filter and reorder columns
            df = df[selected_columns]

            # Append the data to the combined DataFrame
            combined_data = pd.concat([combined_data, df], ignore_index=True)

    # Group the combined data by the output variables and save to separate .csv files
    for variable in output_variables:
        output_filename = os.path.join(combined_directory, f"{variable}.csv")
        variable_data = combined_data[['ID', 'GROUP_LABEL', 'DAY', 'HOUR', '24 HOUR', variable]]
        variable_data.to_csv(output_filename, index=False)


def reformat_csv(input_csv_path, output_csv_path):
    """Reformat a CLAMS CSV file to a "tidy" format."""
    df = pd.read_csv(input_csv_path)

    # Replace missing values in "GROUP_LABEL" with a placeholder value
    df["GROUP_LABEL"].fillna("NO_LABEL", inplace=True)

    # Extract the name of the last column
    last_column_name = df.columns[-1]

    # Pivot the table using "ID", "GROUP_LABEL", "DAY", and "24 HOUR" as indices
    pivot_table = df.pivot_table(index=["ID", "GROUP_LABEL", "DAY"],
                                 columns="24 HOUR", values=last_column_name,
                                 aggfunc="first").reset_index()

    # Flatten the column index and rename columns
    pivot_table.columns = ["ID", "GROUP_LABEL", "DAY"] + [f"{last_column_name}_{hour}" for hour in
                                                          pivot_table.columns[3:]]

    # Save the pivot table to a new CSV file
    pivot_table.to_csv(output_csv_path, index=False)


# Function to process all CSV files in a directory
def reformat_csvs_in_directory(input_dir):
    output_dir = os.path.join(input_dir, "Reformatted_CSVs")
    os.makedirs(output_dir, exist_ok=True)

    for filename in os.listdir(input_dir):
        if filename.endswith(".csv"):
            input_csv_path = os.path.join(input_dir, filename)
            output_csv_path = os.path.join(output_dir, f"reformatted_{filename}")
            reformat_csv(input_csv_path, output_csv_path)
            print(f"Reformatting '{filename}' to reformatted_'{filename}'")

