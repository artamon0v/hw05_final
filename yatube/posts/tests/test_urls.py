from django.test import TestCase, Client
from http import HTTPStatus
from posts.models import Group, Post, User


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = User.objects.create_user(username='admin')
        cls.group = Group.objects.create(
            title='Номер группы',
            slug='test-slug',
            description='Описание группы'
        )
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.user,
            group=cls.group
        )

    def setUp(self):
        self.guest_client = Client()
        self.user = PostURLTests.user
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_guest_pages(self):
        """Страницы доступны любому пользователю"""
        url_guest_names = [
            '/',
            '/group/test-slug/',
            f'/posts/{PostURLTests.post.id}/',
            f'/profile/{PostURLTests.user.username}/',
        ]
        for address in url_guest_names:
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(
                    response.status_code, HTTPStatus.OK
                )

    # Проверяем доступность страниц для авторизованного пользователя
    def test_authorized_pages(self):
        """Страницы доступны авторизованному пользователю"""
        url_authorized_names = [
            '/create/',
            f'/posts/{self.post.id}/edit/',
        ]
        for address in url_authorized_names:
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertEqual(
                    response.status_code, HTTPStatus.OK
                )

    def test_404(self):
        """Cервер возвращает код 404, если страница не найдена."""
        response = self.guest_client.get('/notfound/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    # Проверяем редиректы для неавторизованного пользователя
    def test_all_redirects_anonymous_on_admin_login(self):
        """Редирект неавторизованного пользователя"""
        test_redirect = {
            '/create/': '/auth/login/?next=/create/',
            f'/posts/{PostURLTests.post.id}/edit/':
                f'/auth/login/?next=/posts/{PostURLTests.post.id}/edit/'
        }
        for urls, redirect_url in test_redirect.items():
            with self.subTest(urls=urls):
                response = self.guest_client.get(urls)
                self.assertRedirects(response, redirect_url)

    # Проверка вызываемых шаблонов для каждого адреса
    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            '/notfound': 'core/404.html',
            '/create/': 'posts/create_post.html',
            '/group/test-slug/': 'posts/group_list.html',
            f'/posts/{PostURLTests.post.id}/': 'posts/post_detail.html',
            f'/profile/{PostURLTests.user.username}/': 'posts/profile.html',
            f'/posts/{PostURLTests.post.id}/edit/': 'posts/create_post.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(template=template):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)
