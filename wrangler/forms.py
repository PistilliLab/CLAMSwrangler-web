from django import forms


class UserInputForm(forms.Form):
    """
    Main input form for the user to provide the .csv files and the parameters for processing the data.
    """

    # file_input = forms.FileField(
    #     label='File Input',
    #     widget=forms.ClearableFileInput(),
    #     help_text='Select multiple .csv files.'
    # )
    trim_hours = forms.IntegerField(label='Trim Hours')
    keep_hours = forms.IntegerField(label='Keep Hours')
    bin_hours = forms.ChoiceField(label='Bin Hours', choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (6, '6'),
                                                              (8, '8'), (12, '12'), (24, '24'),])
    # bin_hours = forms.IntegerField(label='Bin Hours')

    def clean_file_input(self):
        """
        Validates if the input files provided are .csv files.

        Returns: validation error if the files are not .csv files.
        """
        files = self.cleaned_data['file_input']
        for file in files:
            if not file.name.endswith('.csv'):
                raise forms.ValidationError("Only .csv files are allowed.")
        return files
