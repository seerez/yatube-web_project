from http import HTTPStatus

from django.test import Client, TestCase

from ..models import Group, Post, User


class PostsUrlTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(
            username='user'
        )
        cls.user_reader = User.objects.create_user(
            username='reader'
        )
        cls.group = Group.objects.create(
            title='Группа',
            slug='test-slug',
            description='Описание'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group
        )
        # страницы для неавторизованных пользователей
        cls.guest_url = {
            '/': 'posts/index.html',
            f'/group/{cls.group.slug}/': 'posts/group_list.html',
            f'/profile/{cls.user.username}/': 'posts/profile.html',
            f'/posts/{cls.post.id}/': 'posts/post_detail.html',
        }
        # страницы авторизированных пользователей
        cls.auth_user_url = {
            f'/posts/{PostsUrlTests.post.id}/edit/': 'posts/post_edit.html',
            '/create/': '/posts/post_create.html'
        }

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем второй клиент
        self.authorized_client = Client()
        # Авторизуем пользователя
        self.authorized_client.force_login(self.user)
        self.client_reader = Client()
        self.client_reader.force_login(self.user_reader)

    def test_guest_url(self):
        for path in self.guest_url.keys():
            with self.subTest(path=path):
                response = self.guest_client.get(path)
                self.assertEqual(response.status_code, HTTPStatus.OK, (
                    f'Статус код страницы {path} не равен 200'
                )
                )

    def test_guest_redirect_post_edit(self):
        """Проверка редиректа у анонимного пользователя"""
        response = self.guest_client.get(
            f'/posts/{PostsUrlTests.post.id}/edit/'
        )
        self.assertRedirects(
            response,
            f'/auth/login/?next=/posts/{self.post.id}/edit/'
        )

    def test_auth_url(self):
        for path in self.guest_url.keys():
            with self.subTest(path=path):
                response = self.authorized_client.get(path)
                self.assertEqual(response.status_code, HTTPStatus.OK, (
                    f'Статус код страницы {path} не равен 200'
                )
                )

    def test_auth_not_author(self):
        response = self.client_reader.get(
            f'/posts/{PostsUrlTests.post.id}/edit/',
            follow=True
        )
        self.assertRedirects(response, f'/posts/{self.post.id}/')
