from django import forms
from posts.models import Comment, Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        labels = {
            'text': 'Текст поста',
            'group': 'Группа',
        }
        help_texts = {
            'text': 'Введите текст поста',
            'group': 'Выберите группу к которой будет относиться пост'
        }
        fields = ["text", "group", 'image']


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["text"]
