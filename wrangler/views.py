import os
import uuid
import shutil
import pandas as pd
from django.conf import settings
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.shortcuts import render, redirect
from django.http import Http404, JsonResponse, HttpResponse, HttpResponseRedirect
from wsgiref.util import FileWrapper
from .forms import UserInputForm
from clams_processing import clean_all_clams_data, trim_all_clams_data, process_directory, recombine_columns, \
    reformat_csvs_in_directory
from helpers import get_latest_version, zip_directory


def homepage_view(request):
    # version = str(get_latest_version())
    if request.method == 'POST':
        form = UserInputForm(request.POST, request.FILES)
        if form.is_valid():

            # Process the form data
            trim_hours = form.cleaned_data['trim_hours']
            keep_hours = form.cleaned_data['keep_hours']
            bin_hours = form.cleaned_data['bin_hours']
            start_cycle = form.cleaned_data['start_cycle']

            # Access the upload_dir session variable
            upload_dir = request.session.get('upload_dir', None)
            print(upload_dir)
            if upload_dir:
                experiment_config_path = os.path.join(settings.MEDIA_ROOT, upload_dir, 'config')
                experiment_config_file = os.path.join(experiment_config_path, 'experiment_config.csv')

                clean_all_clams_data(upload_dir)
                trim_all_clams_data(upload_dir, trim_hours, keep_hours, start_cycle)
                process_directory(upload_dir, 1)
                recombine_columns(upload_dir, experiment_config_file)
                reformat_csvs_in_directory(os.path.join(upload_dir, 'Combined_CLAMS_data'))

            # Zip the processed files and return
            zip_directory(upload_dir, os.path.join(settings.MEDIA_ROOT, f'{upload_dir}.zip'))

            return HttpResponseRedirect('/')

    else:
        form = UserInputForm()

    return render(request, 'home.html', {'form': form})


def upload_csv_files(request):
    """
    Uploads the files to the server and stores them in the session.

    Args:
        request:

    Returns: upload_id and message if the file is uploaded successfully.

    """
    if request.method == 'POST':
        # Check if the session already has an upload directory
        upload_id = request.session.get('upload_id')
        if not upload_id:
            # Generate unique ID for new upload session
            upload_id = str(uuid.uuid4())
            request.session['upload_id'] = upload_id  # Store it in the session

            # Create directory for this session
            upload_dir = os.path.join(settings.MEDIA_ROOT, upload_id)
            os.makedirs(upload_dir, exist_ok=True)
            request.session['upload_dir'] = upload_dir  # Store directory path in session
        else:
            # Use existing directory if session already started
            upload_dir = request.session.get('upload_dir', '')

        # Check if the request contains the config file
        config_file = request.FILES.get('config_file')
        if config_file:
            # Create the 'config' subfolder if it doesn't exist
            config_dir = os.path.join(upload_dir, 'config')
            os.makedirs(config_dir, exist_ok=True)

            # Save the config file to the 'config' subfolder
            config_file_path = os.path.join(config_dir, 'experiment_config.csv')
            with open(config_file_path, 'wb+') as destination:
                for chunk in config_file.chunks():
                    destination.write(chunk)

        # Save files uploaded in this request
        files = request.FILES.getlist('file')
        for file in files:
            file_path = os.path.join(upload_dir, file.name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)

        request.session['upload_dir'] = upload_dir  # Store directory path in session

        return JsonResponse({'message': 'File uploaded successfully', 'upload_id': upload_id})

    else:
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)


def download_zip(request, upload_id):
    file_path = os.path.join(settings.MEDIA_ROOT, f'{upload_id}.zip')
    if os.path.exists(file_path):
        with open(file_path, 'rb') as fh:
            response = HttpResponse(FileWrapper(fh), content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename={os.path.basename(file_path)}'
            return response
    raise Http404


def check_zip_exists(request, upload_id):
    file_path = os.path.join(settings.MEDIA_ROOT, f'{upload_id}.zip')
    return JsonResponse({'exists': os.path.exists(file_path)})


def download_config_template(request):
    """Download the experiment configuration template file.
    The template file contains the expected columns for the experiment configuration file.

    Returns: HttpResponse object with the experiment configuration template file.
    """

    # Path to the experiment configuration file
    config_file = os.path.join(settings.MEDIA_ROOT, 'config', 'experiment_config.csv')

    if os.path.exists(config_file):
        with open(config_file, 'rb') as fh:
            response = HttpResponse(FileWrapper(fh), content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename=experiment_config.csv'
            return response
    raise Http404


def clear_session(request):
    upload_dir = request.session.get('upload_dir', None)
    if upload_dir and os.path.exists(upload_dir):
        shutil.rmtree(upload_dir)  # Delete the session folder and its contents

    request.session.flush()  # Clear all session data

    return JsonResponse({'message': 'Session cleared successfully'})