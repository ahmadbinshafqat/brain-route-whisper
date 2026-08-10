from django import forms


class TripCreateForm(forms.Form):
    title = forms.CharField(max_length=160, initial='My walking route')
    origin_optional = forms.CharField(
        max_length=255,
        required=False,
        label='Optional starting point',
        help_text='If provided, the route starts near this address/coordinate.'
    )
    stops_text = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 10, 'placeholder': 'Paste 5-20 places, one per line'}),
        label='Stops',
        help_text='Use addresses/place names, or "Label | lat,lng" for offline coordinates.'
    )

    def clean_stops_text(self):
        value = self.cleaned_data['stops_text']
        lines = [line.strip() for line in value.splitlines() if line.strip()]
        if len(lines) < 5 or len(lines) > 20:
            raise forms.ValidationError('Please paste between 5 and 20 stops.')
        return '\n'.join(lines)
