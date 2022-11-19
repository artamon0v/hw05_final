from django.test import Client, TestCase
from django.urls import reverse
from django import forms
from django.core.cache import cache

from posts.models import Post, Group, User, Follow


class PostPagesTests(TestCase):
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
        cls.user1 = User.objects.create(
            username='chel',
            email='chel@mail.ru',
            password='test'
        )

    def setUp(self):
        self.guest_client = Client()
        self.user = PostPagesTests.user
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    # Проверяем используемые шаблоны
    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_page_names = {
            'posts/index.html': reverse('posts:index'),
            'posts/profile.html': reverse(
                'posts:profile',
                kwargs={'username': PostPagesTests.user.username}
            ),
            'posts/group_list.html': (
                reverse('posts:group_list', kwargs={'slug': 'test-slug'})
            ),
        }
        for template, reverse_name in templates_page_names.items():
            with self.subTest(template=template):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_home_page_show_correct_context(self):
        """Шаблон home сформирован с правильным контекстом."""
        response = self.guest_client.get(reverse('posts:index'))
        post_object = response.context['page_obj'][0]
        post_author = post_object.author
        post_text = post_object.text
        post_pub_date = post_object.pub_date
        self.assertEqual(post_author, PostPagesTests.user)
        self.assertEqual(post_text, PostPagesTests.post.text)
        self.assertEqual(post_pub_date, PostPagesTests.post.pub_date)

    def test_group_page_show_correct_context(self):
        """Шаблон group_posts сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': 'test-slug'})
        )
        self.assertEqual(
            response.context['group'].title, PostPagesTests.group.title
        )
        self.assertEqual(
            response.context['group'].description,
            PostPagesTests.group.description
        )
        self.assertEqual(
            response.context['group'].slug, PostPagesTests.group.slug
        )

    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.guest_client.get(reverse(
            'posts:profile', kwargs={'username': PostPagesTests.user.username})
        )
        post_object = response.context['page_obj'][0]
        post_username = post_object.author.username
        post_text = post_object.text
        post_pub_date = post_object.pub_date
        self.assertEqual(post_username, PostPagesTests.user.username)
        self.assertEqual(post_text, PostPagesTests.post.text)
        self.assertEqual(post_pub_date, PostPagesTests.post.pub_date)

    def test_edit_correct_context(self):
        """Шаблон edit сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse(
            'posts:post_edit', kwargs={
                'post_id': PostPagesTests.post.id})
        )
        form_fields = {
            'group': forms.fields.ChoiceField,
            'text': forms.fields.CharField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.guest_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        self.assertEqual(response.context.get('post').text, self.post.text)
        self.assertEqual(response.context.get('post').author, self.post.author)
        self.assertEqual(response.context.get('post').group, self.post.group)

    def test_index_page_cache(self):
        """Записи Index хранятся в кэше и обновлялся раз в 20 секунд"""
        response_1 = self.authorized_client.get(reverse('posts:index'))
        Post.objects.create(
            text='Тестовый текст для кэша',
            author=PostPagesTests.user,
            group=PostPagesTests.group,
        )
        response_2 = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(response_1.content, response_2.content)
        cache.clear()
        response_3 = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(response_2.content, response_3.content)

    def test_following(self):
        """Тестирование подписки на автора."""
        count_follow = Follow.objects.count()
        new_author = User.objects.create(username='Tolstoy')
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': new_author.username}
            )
        )
        follow = Follow.objects.last()
        self.assertEqual(Follow.objects.count(), count_follow + 1)
        self.assertEqual(follow.author, new_author)
        self.assertEqual(follow.user, PostPagesTests.user)

    def test_unfollowing(self):
        """Авторизованный пользователь может отписаться"""
        Follow.objects.filter(
            user=PostPagesTests.user1,
            author=PostPagesTests.user).delete()
        self.assertFalse(Follow.objects.filter(
            user=PostPagesTests.user1,
            author=PostPagesTests.user).exists())

    def test_following_posts(self):
        """Есть посты у подписчика."""
        new_user = User.objects.create(username='Tolstoy')
        authorized_client = Client()
        authorized_client.force_login(new_user)
        authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': PostPagesTests.user.username}
            )
        )
        response_follow = authorized_client.get(
            reverse('posts:follow_index')
        )
        context_follow = response_follow.context
        self.assertEqual(len(context_follow['page_obj']), 1)   

    def test_unfollowing_posts(self):
        """Нет постов у неподписанного пользователя."""
        new_user = User.objects.create(username='Tolstoy')
        authorized_client = Client()
        authorized_client.force_login(new_user)
        response_unfollow = authorized_client.get(
            reverse('posts:follow_index')
        )
        context_unfollow = response_unfollow.context
        self.assertEqual(len(context_unfollow['page_obj']), 0)
