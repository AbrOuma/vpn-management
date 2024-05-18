from django import forms
from apps.users.models import VPNUser
from .models import Device
from apps.server.models import ServerConfig

class DeviceForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': "e.g. John's iPhone"
        })
    )
    device_type = forms.ChoiceField(
        choices=Device.DeviceType.choices
    )
    server = forms.ModelChoiceField(
        queryset=ServerConfig.objects.all(),
        help_text='Which server this device belongs to'
    )
    user = forms.ModelChoiceField(
        queryset=VPNUser.objects.filter(status='active'),
        required=False,
        help_text='Optional - assign to a VPN user'
    )


class DeviceEditForm(forms.ModelForm):
    """
    Edit form for devices.
    Only allows changing fields that do not affect the VPN connection.
    IP address, public key and preshared key are never editable.
    """
    class Meta:
        model  = Device
        fields = ['name', 'device_type', 'user']
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': "e.g. John's iPhone"
            }),
        }
        help_texts = {
            'user': 'Reassigning a user does not affect the VPN connection.',
        }
