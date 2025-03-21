import os
from celery import shared_task
from django.conf import settings
from clams_processing import (
    clean_all_clams_data, trim_all_clams_data, process_directory,
    recombine_columns, reformat_csvs_in_directory, merge_fragmented_runs_by_id,
    quality_control
)
from helpers import zip_directory


@shared_task
def process_files_task(upload_id, trim_hours, keep_hours, bin_hours, start_cycle):
    try:
        upload_dir = os.path.join(settings.MEDIA_ROOT, upload_id)
        experiment_config_path = os.path.join(upload_dir, 'config')
        # the views.upload_csv_files function renames it to experiment_config.csv
        experiment_config_file = os.path.join(experiment_config_path, 'experiment_config.csv')

        # merge_fragmented_runs_by_id(upload_dir, experiment_config_file)

        clean_all_clams_data(upload_dir)
        quality_control(upload_dir)
        trim_all_clams_data(upload_dir, trim_hours, keep_hours, start_cycle)

        # Loop through the bin hours and process the data
        for bin_hour in bin_hours:
            process_directory(upload_dir, bin_hour)
            recombine_columns(upload_dir, experiment_config_file, bin_hour)
            reformat_csvs_in_directory(os.path.join(upload_dir, f'{bin_hour}hour_bins_Combined_CLAMS_data'))

        # Zip the processed files
        zip_file_path = os.path.join(settings.MEDIA_ROOT, f'{upload_id}.zip')
        zip_directory(upload_dir, zip_file_path)

        return {'upload_id': upload_id}
    except Exception as e:
        # Log the exception (optional)
        print(f"Error processing files: {e}")
        return {'error': str(e)}
