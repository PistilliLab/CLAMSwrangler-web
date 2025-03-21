from django import forms


class UserInputForm(forms.Form):
    """
    Main input form for the user to provide the .csv files and the parameters for processing the data.
    """

    trim_hours = forms.IntegerField(label='Trim Hours', widget=forms.NumberInput(attrs={'class': 'form-control'}))
    keep_hours = forms.IntegerField(label='Keep Hours', widget=forms.NumberInput(attrs={'class': 'form-control'}))
    bin_hours = forms.MultipleChoiceField(
        label='Bin Hours',
        choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (6, '6'), (12, '12'), (24, '24')],
        widget=forms.CheckboxSelectMultiple()
    )
    # bin_hours = forms.IntegerField(label='Bin Hours')
    start_cycle = forms.ChoiceField(
        label='Start Cycle',
        choices=[('Start Light', 'Start Light'), ('Start Dark', 'Start Dark')]
    )
