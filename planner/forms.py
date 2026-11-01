from django import forms


class TripForm(forms.Form):
    OPTIMIZATION_BALANCED = "balanced"
    OPTIMIZATION_DISTANCE = "distance"

    OPTIMIZATION_CHOICES = (
        (OPTIMIZATION_BALANCED, "Balanced optimization"),
        (OPTIMIZATION_DISTANCE, "Minimize total distance"),
    )

    stops = forms.CharField(
        label="Places to visit",
        widget=forms.Textarea(
            attrs={
                "rows": 10,
                "placeholder": "Eiffel Tower\nLouvre Museum\nNotre-Dame Cathedral\nLuxembourg Gardens\nArc de Triomphe",
            }
        ),
        help_text="Enter one stop per line. Use 5-20 stops for best results.",
    )
    optimization_goal = forms.ChoiceField(
        label="Route preference",
        choices=OPTIMIZATION_CHOICES,
        initial=OPTIMIZATION_BALANCED,
        help_text="Balanced uses the original Route Whisper heuristic. Distance applies a stronger improvement pass.",
    )
    preserve_order = forms.BooleanField(
        label="Preserve my pasted stop order",
        required=False,
        help_text="Skip optimization and keep stops exactly as entered.",
    )
    anchor_stop = forms.CharField(
        label="Start from this stop (optional)",
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={"placeholder": "Example: Louvre Museum or 2"}),
        help_text="Enter a stop name or line number to force the route to start there.",
    )

    def clean_stops(self):
        value = self.cleaned_data["stops"]
        lines = [line.strip() for line in value.splitlines() if line.strip()]
        if len(lines) < 2:
            raise forms.ValidationError("Enter at least 2 stops to plan a route.")
        if len(lines) > 20:
            raise forms.ValidationError("Please limit each trip to 20 stops.")
        return "\n".join(lines)

    def clean_anchor_stop(self):
        return self.cleaned_data.get("anchor_stop", "").strip()

    def get_preferences(self):
        return {
            "optimization_goal": self.cleaned_data.get("optimization_goal", self.OPTIMIZATION_BALANCED),
            "preserve_order": bool(self.cleaned_data.get("preserve_order")),
            "anchor_stop": self.cleaned_data.get("anchor_stop", "").strip(),
        }
