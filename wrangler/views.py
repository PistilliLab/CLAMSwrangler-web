from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.shortcuts import render, redirect
from django.http import Http404, JsonResponse
from .forms import UserInputForm
from clams_processing import clean_all_clams_data, trim_all_clams_data, process_directory, recombine_columns, \
    reformat_csvs_in_directory
from helpers import get_latest_version


def homepage_view(request):
    # version = str(get_latest_version())
    if request.method == 'POST':
        form = UserInputForm(request.POST, request.FILES)
        if form.is_valid():
            # Process the form data
            trim_hours = form.cleaned_data['trim_hours']
            keep_hours = form.cleaned_data['keep_hours']
            bin_hours = form.cleaned_data['bin_hours']
            files = request.FILES.getlist('file_input')

            # Call your processing function
            # processed_files = your_processing_function(files, text, number)

            # Code to return processed files back to user

    else:
        form = UserInputForm()

    return render(request, 'home.html', {'form': form})


def upload_csv_files(request):
    if request.method == 'POST':
        file = request.FILES.get('file')
        # Save the file, process it, etc...

        return JsonResponse({'message': 'File uploaded successfully'})

    return JsonResponse({'error': 'Failed to upload file'}, status=400)
