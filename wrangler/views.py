import os
import uuid
import pandas as pd
from django.conf import settings
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.shortcuts import render, redirect
from django.http import Http404, JsonResponse
from .forms import UserInputForm
from clams_processing import clean_all_clams_data, trim_all_clams_data, process_directory, recombine_columns, \
    reformat_csvs_in_directory
from helpers import get_latest_version, initialize_experiment_config_file


def homepage_view(request):
    # version = str(get_latest_version())
    if request.method == 'POST':
        form = UserInputForm(request.POST, request.FILES)
        if form.is_valid():
            # Process the form data
            trim_hours = form.cleaned_data['trim_hours']
            keep_hours = form.cleaned_data['keep_hours']
            bin_hours = form.cleaned_data['bin_hours']

            # Access the upload_dir session variable
            upload_dir = request.session.get('upload_dir', None)
            print(upload_dir)
            if upload_dir:
                experiment_config_path = os.path.join(settings.MEDIA_ROOT, 'config')
                experiment_config_file = os.path.join(experiment_config_path, 'config.csv')

                # Check if the experiment configuration file exists
                if not os.path.exists(experiment_config_file):
                    # Initialize a new experiment configuration file
                    initialize_experiment_config_file(experiment_config_path)

                    # Check if the user provided a config file to be copied
                    # selected_config_file = config_file_entry.get()
                    if os.path.exists(experiment_config_file):
                        try:
                            # Read the selected config file
                            config_df = pd.read_csv(experiment_config_file)
                            print(config_df.columns)
                            expected_columns = ["ID", "GROUP_LABEL"]
                            if all(col in config_df.columns for col in expected_columns):
                                # Copy the selected config file to the new experiment configuration file
                                config_file_dest = os.path.join(experiment_config_path, 'config.csv')
                                config_df.to_csv(config_file_dest, index=False, columns=expected_columns)
                        except (pd.errors.EmptyDataError, pd.errors.ParserError, ValueError) as e:
                            # Handle errors while reading/copying the selected config file
                            print(f"Error copying config file: {str(e)}\n")

                clean_all_clams_data(upload_dir)
                trim_all_clams_data(upload_dir, trim_hours, keep_hours, "Start Dark")
                process_directory(upload_dir, bin_hours)
                recombine_columns(upload_dir, experiment_config_file)
                reformat_csvs_in_directory(os.path.join(upload_dir, 'Combined_CLAMS_data'))

            # Code to return processed files back to user

    else:
        form = UserInputForm()

    return render(request, 'home.html', {'form': form})


def upload_csv_files(request):
    if request.method == 'POST':
        # Generate unique ID for each upload session
        upload_id = str(uuid.uuid4())
        upload_dir = os.path.join(settings.MEDIA_ROOT, upload_id)

        # Create directory for upload session
        os.makedirs(upload_dir, exist_ok=True)

        # Iterate through the files received in the POST request
        files = request.FILES.getlist('file')
        for file in files:
            # Save each file to the unique directory
            file_path = os.path.join(upload_dir, file.name)
            with open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)

        # If file upload successful, assign upload_dir to session variable
        request.session['upload_dir'] = upload_dir

        return JsonResponse({'message': 'File uploaded successfully', 'upload_id': upload_id})

    else:
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)
