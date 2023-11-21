from django import forms


class UserInputForm(forms.Form):
    # file_input = forms.FileField(
    #     label='File Input',
    #     widget=forms.ClearableFileInput(),
    #     help_text='Select multiple .csv files.'
    # )
    trim_hours = forms.IntegerField(label='Trim Hours')
    keep_hours = forms.IntegerField(label='Keep Hours')
    bin_hours = forms.IntegerField(label='Bin Hours')

    def clean_file_input(self):
        files = self.cleaned_data['file_input']
        for file in files:
            if not file.name.endswith('.csv'):
                raise forms.ValidationError("Only .csv files are allowed.")
        return files
