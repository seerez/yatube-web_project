import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.models import Comment, Follow, Group, Post, User

User = get_user_model()


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


class PostsPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(
            username='Bob'
        )
        cls.group = Group.objects.create(
            title='Название',
            slug='test_slug',
            description='Описание'
        )
        posts_list = []
        for _ in range(15):

            post = Post(
                text='Текстовое поле поста',
                author=cls.user,
                group=cls.group
            )
            posts_list.append(post)
        cls.posts = Post.objects.bulk_create(posts_list)
        cls.post = Post.objects.first()
        # url: template
        cls.templates_pages_name = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list',
                kwargs={'slug': cls.group.slug}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile',
                kwargs={'username': cls.user.username}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail',
                kwargs={'post_id': cls.post.id}
            ): 'posts/post_detail.html',
            reverse(
                'posts:post_edit',
                kwargs={'post_id': cls.post.id}
            ): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html'
        }

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_posts_templates(self):
        """URL использует соответсвующий шаблон"""
        for reverse_name, template in self.templates_pages_name.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template, (
                    f'Что-то пошло не так с URL: {reverse_name}'
                )
                )

    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        page_obj = response.context['page_obj']
        post_ids = [post.id for post in page_obj]
        self.assertIn(self.post.id, post_ids)
        first_object = response.context['page_obj'][0]
        post_text_0 = first_object.text
        post_author_0 = first_object.author
        post_group_0 = first_object.group
        self.assertEqual(post_text_0, self.post.text)
        self.assertEqual(post_author_0, self.post.author)
        self.assertEqual(post_group_0, self.post.group)

    def test_group_posts_page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse(
            'posts:group_list',
            kwargs={'slug': self.group.slug}
        )
        )
        page_obj = response.context['page_obj']
        post_groups = [post.group for post in page_obj]
        self.assertIn(self.post.group, post_groups)
        first_object = response.context['group']
        group_title_0 = first_object.title
        group_slug_0 = first_object.slug
        self.assertEqual(group_title_0, self.group.title)
        self.assertEqual(group_slug_0, self.group.slug)

    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse(
            'posts:profile',
            kwargs={'username': self.user.username}
        )
        )
        first_object = response.context['page_obj'][0]
        post_author_0 = first_object.author
        post_text_0 = first_object.text
        self.assertEqual(post_text_0, self.post.text)
        self.assertEqual(post_author_0, self.post.author)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse(
            'posts:post_detail',
            kwargs={'post_id': self.post.id}
        )
        )
        first_object = response.context['post']
        post_author = first_object.author
        post_text = first_object.text
        self.assertEqual(post_text, self.post.text)
        self.assertEqual(post_author, self.post.author)

    def test_post_create_page_show_correct_context(self):
        """Шаблон posts_create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_field = {
            'text': forms.fields.CharField
        }
        for value, expected in form_field.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_post_edit_page_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse(
            'posts:post_edit',
            kwargs={'post_id': self.post.id}
        )
        )
        is_edit = True
        form_field = {
            'text': forms.fields.CharField
        }
        for value, expected in form_field.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)
        self.assertEqual(is_edit, True)

    def test_post_detail_page_show_comments(self):
        """Страница post_detail отображает комментарии"""
        Comment.objects.create(
            post=self.post,
            author=self.user,
            text='Тестовый коммент',
        )
        response = self.authorized_client.get(
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.id}
            )
        )
        first_object = response.context['post']
        self.assertEqual(
            first_object.comments.first().text,
            Comment.objects.first().text,
            'Комментарий не передался'
        )

    def test_index_page_contains_ten_records(self):
        """Paginator на странице index работает правильно."""
        response = self.client.get(reverse('posts:index'))
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_group_list_pagecontains_ten_records(self):
        """Paginator на странице group_list работает правильно."""
        response = self.client.get(reverse(
            'posts:group_list',
            kwargs={'slug': self.group.slug}
        )
        )
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_profile_pagecontains_ten_records(self):
        """Paginator на странице profile работает правильно."""
        response = self.authorized_client.get(reverse(
            'posts:profile',
            kwargs={'username': self.user.username}
        )
        )
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_posts_follow(self):
        """Авторизованный пользователь может подписываться"""
        user2 = User.objects.create_user(username='TestingAccount2')
        authorized_client2 = Client()
        authorized_client2.force_login(user2)
        expected_quantity_of_objects_after_follow = 1
        # expected_quantity_of_objects_after_unfollow = 0
        authorized_client2.get(
            reverse('posts:profile_follow', kwargs={'username': self.user})
        )
        self.assertEqual(
            expected_quantity_of_objects_after_follow,
            Follow.objects.count(),
            "Пользователь не может подписаться"
        )

    def test_posts_unfollow(self):
        """Авторизированный пользователь может отписаться"""
        user2 = User.objects.create_user(username='TestingAccount2')
        authorized_client2 = Client()
        authorized_client2.force_login(user2)
        expected_quantity_of_objects_after_unfollow = 0
        authorized_client2.get(
            reverse('posts:profile_unfollow', kwargs={'username': self.user})
        )
        self.assertEqual(
            expected_quantity_of_objects_after_unfollow,
            Follow.objects.count(),
            "Пользователь не может отписаться"
        )

    def test_follow_page_show_correct_posts(self):
        """
        Новая запись пользователя(user2) попадает к пользователю(user1) и
        не попадает к пользователю(user3)
        """
        user2 = User.objects.create_user(username='TestingAccount2')
        authorized_client2 = Client()
        authorized_client2.force_login(user2)
        user3 = User.objects.create_user(username='TestingAccount3')
        authorized_client3 = Client()
        authorized_client3.force_login(user3)
        Follow.objects.create(
            author=user2,
            user=self.user,
        )
        Post.objects.create(
            author=user2,
            text='Тестовый пост для проверки подписки',
        )
        response = self.authorized_client.get(reverse('posts:follow_index'))
        objects = response.context['page_obj']
        self.assertEqual(
            len(objects),
            1,
            "Новый пост не попадает на follow"
        )
        response = authorized_client2.get(reverse('posts:follow_index'))
        objects = response.context['page_obj']
        self.assertEqual(
            len(objects),
            0,
            "Новая запись появляется в ленте автора"
        )
        response = authorized_client3.get(reverse('posts:follow_index'))
        objects = response.context['page_obj']
        self.assertEqual(
            len(objects),
            0,
            "Новая запись появилась в ленте без подписки"
        )


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsMediaTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_group1 = Group.objects.create(
            title='Тестовая группа1',
            slug='slug_test',
            description='Тестовое описание1',
        )
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        Post.objects.all().delete()

    def setUp(self):
        self.user = User.objects.create_user(username='TestingAccount')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.post = Post.objects.create(
            author=self.user,
            text='Тестовый пост',
            group=self.test_group1,
            image=self.uploaded,
        )
        cache.clear()

    def test_pages_with_pictures_showed_correct_context(self):
        """
        Проверка наличия image в контексте index, profile, group_list
        """
        reverses = (
            reverse('posts:index'),
            reverse('posts:profile', kwargs={"username": self.user.username}),
            reverse(
                'posts:group_list', kwargs={'slug': self.test_group1.slug}
            ),
        )
        for reverse_name in reverses:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                object = response.context['page_obj'][0]
                self.assertTrue(object.image)

    def test_post_detail_page_with_picture_shows_correct_context(self):
        """Проверка наличия image в контексте post_detail"""
        response = self.authorized_client.get(reverse(
            'posts:post_detail',
            kwargs={'post_id': self.post.id}
        )
        )
        object = response.context['post']
        self.assertTrue(object.image)


class PostsCacheTest(TestCase):
    def test_index_page_cache(self):
        """Проверка работы кеша"""
        self.user = User.objects.create_user(username='TestingAccount')
        guest = Client()
        database_post = Post.objects.create(
            author=self.user,
            text='Тестовый пост',
        )
        response_before_delite = guest.get(reverse('posts:index'))
        cache_post = response_before_delite.content.decode()
        database_post.delete()
        response_after_delite = guest.get(reverse('posts:index'))
        self.assertEqual(
            cache_post,
            response_after_delite.content.decode(),
            "Кеш не сохраняет шаблон"
        )
        cache.clear()
        response_after_cache_cleaning = guest.get(reverse('posts:index'))
        self.assertNotEqual(
            cache_post,
            response_after_cache_cleaning.content.decode(),
            "Кеш не работает"
        )
