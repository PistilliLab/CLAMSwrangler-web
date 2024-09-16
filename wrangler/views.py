import os
import uuid
import shutil
from django.conf import settings
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse, HttpResponseNotFound, HttpResponseForbidden, FileResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from wsgiref.util import FileWrapper
from .forms import UserInputForm
from .tasks import process_files_task
from celery.result import AsyncResult


def homepage_view(request):
    # version = str(get_latest_version())
    if request.method == 'POST':
        form = UserInputForm(request.POST, request.FILES)
        if form.is_valid():

            # Retrieve the form data
            trim_hours = form.cleaned_data['trim_hours']
            keep_hours = form.cleaned_data['keep_hours']
            bin_hours = form.cleaned_data['bin_hours']
            start_cycle = form.cleaned_data['start_cycle']

            # Get upload_id from session
            upload_id = request.session.get('upload_id')
            if not upload_id:
                return JsonResponse({'error': 'No upload session found'}, status=400)

            # Enqueue the processing task
            task = process_files_task.delay(upload_id, trim_hours, keep_hours, bin_hours, start_cycle)

            # Redirect to the processing page with the task ID
            return redirect('processing', task_id=task.id)
        else:
            return render(request, 'home.html', {'form': form})
    else:
        form = UserInputForm()
        return render(request, 'home.html', {'form': form})


def processing_view(request, task_id):
    return render(request, 'processing.html', {'task_id': task_id})


def download_view(request, upload_id):
    # Check if the upload_id matches the session's upload_id
    session_upload_id = request.session.get('upload_id')
    if upload_id != session_upload_id:
        return HttpResponseForbidden('You are not authorized to access this file.')

    file_path = os.path.join(settings.MEDIA_ROOT, f'{upload_id}.zip')
    if os.path.exists(file_path):
        return render(request, 'download.html', {'upload_id': upload_id})
    else:
        return HttpResponseNotFound('File not found.')


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

        upload_dir = os.path.join(settings.MEDIA_ROOT, upload_id)
        os.makedirs(upload_dir, exist_ok=True)
        request.session['upload_dir'] = upload_dir  # Store directory path in session

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


def task_status(request, task_id):
    result = AsyncResult(task_id)
    response_data = {'status': result.status}
    if result.status == 'SUCCESS':
        # Ensure result.result is not None
        task_result = result.result or {}
        response_data.update(task_result)
    elif result.status == 'FAILURE':
        # Handle exceptions properly
        response_data['error'] = str(result.result)
    return JsonResponse(response_data)


def download_zip_file(request, upload_id):
    # Check if the upload_id matches the session's upload_id
    session_upload_id = request.session.get('upload_id')
    if upload_id != session_upload_id:
        return HttpResponseForbidden('You are not authorized to access this file.')

    file_path = os.path.join(settings.MEDIA_ROOT, f'{upload_id}.zip')
    if os.path.exists(file_path):
        response = FileResponse(open(file_path, 'rb'), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename={upload_id}.zip'
        return response
    else:
        return HttpResponseNotFound('File not found.')


def check_zip_exists(request, upload_id):
    file_path = os.path.join(settings.MEDIA_ROOT, f'{upload_id}.zip')
    return JsonResponse({'exists': os.path.exists(file_path)})


def download_config_template(request):
    """Download the experiment configuration template file.
    The template file contains the expected columns for the experiment configuration file.

    Returns: HttpResponse object with the experiment configuration template file.
    """

    # Path to the experiment configuration file
    config_file = os.path.join(settings.MEDIA_ROOT, 'templates', 'experiment_config.csv')

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
