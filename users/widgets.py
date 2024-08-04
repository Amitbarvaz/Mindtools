from django.forms import Textarea


class CharacterCountTextarea(Textarea):
    template_name = 'admin/users/widgets/textarea_with_counter.html'

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['widget']['attrs']['id'] = f'{name}_id'
        return context
