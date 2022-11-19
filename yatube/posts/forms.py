from django.forms import ModelForm
from .models import Post, Comment
from django.utils.translation import gettext_lazy as _


class PostForm(ModelForm):
    class Meta:
        model = Post
        fields = ('group', 'text', 'image')
        help_texts = {
            'name': _('Введите текст поста и выберите группу'),
        }


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
