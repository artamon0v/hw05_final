from django.test import TestCase, Client, override_settings
from django.urls import reverse
from posts.models import Group, Post, User, Comment
from django.core.files.uploadedfile import SimpleUploadedFile
import shutil
import tempfile
from django.conf import settings


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(dir=settings.BASE_DIR))
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.user = User.objects.create_user(username='admin')
        cls.group = Group.objects.create(
            title='Номер группы',
            slug='test-slug',
            description='Описание группы'
        )
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.user,
            group=cls.group,
            image=uploaded,
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.guest_client = Client()
        self.user = PostFormTests.user
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        posts_count = Post.objects.count()
        form_data = {'text': 'Тестовый пост'}
        response = self.authorized_client.post(
            reverse('posts:post_create'), data=form_data, follow=True
        )
        self.assertRedirects(
            response, reverse(
                'posts:profile',
                kwargs={'username': self.user.username}
            )
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(Post.objects.filter(text='Тестовый пост').exists())
        self.assertEqual(response.status_code, 200)

    def test_edit_post(self):
        """Редактирование поста прошло успешно."""
        new_form_data = {
            'group': PostFormTests.group.id,
            'text': 'Другой тестовый пост'
        }
        response = self.authorized_client.post(reverse(
            'posts:post_edit',
            kwargs={
                'post_id': PostFormTests.post.id
            }),
            data=new_form_data,
            follow=True
        )
        self.post.refresh_from_db()
        self.assertEqual(
            response.context['post'].text, new_form_data['text']
        )

    def test_not_create_post(self):
        """Валидная форма создает запись в Post."""
        posts_count = Post.objects.count()
        form_data = {'text': 'Тестовый пост'}
        response = self.guest_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response, '/auth/login/?next=/create/'
        )
        self.assertNotEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(Post.objects.filter(text='Тестовый пост').exists())
        self.assertEqual(response.status_code, 200)

    def test_no_edit_post(self):
        '''Проверка запрета редактирования неавторизованного пользователя'''
        posts_count = Post.objects.count()
        form_data = {'text': 'Тестовый текст',
                     'group': self.group.id}
        response = self.guest_client.post(reverse('posts:post_create'),
                                          data=form_data,
                                          follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(Post.objects.count(), posts_count + 1)

    def test_not_author_edit_post(self):
        '''Проверка запрета редактирования неавторизованного пользователя'''
        posts_count = Post.objects.count()
        form_data = {'text': 'Тестовый текст',
                     'group': self.group.id,
                     'author': self.user.username
                     }
        response = self.guest_client.post(reverse('posts:post_create'),
                                          data=form_data,
                                          follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(Post.objects.count(), posts_count + 1)

    def test_create_comment(self):
        """Создание комментариев."""
        comment_count = Comment.objects.count()
        form_data = {
            'text': 'Новый комментарий'
        }
        response = self.authorized_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': PostFormTests.post.pk}
            ),
            data=form_data,
            follow=True
        )
        comment = Comment.objects.first()
        self.assertRedirects(response, reverse(
            'posts:post_detail',
            kwargs={'post_id': PostFormTests.post.pk}
        ))
        self.assertEqual(Comment.objects.count(), comment_count + 1)
        self.assertEqual(comment.text, form_data['text'])
        self.assertEqual(comment.post, PostFormTests.post)
        self.assertEqual(comment.author, PostFormTests.user)

    def test_profile_check_context_contains_image(self):
        """Изображение передаётся в словаре context на страницу профайла."""
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.user.username})
        )
        self.assertTrue(response.context['page_obj'][0].image)

    def test_index_check_context_contains_image(self):
        """Изображение передаётся в словаре context на главную страницу."""
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertTrue(response.context['page_obj'][0].image)

    def test_group_check_context_contains_image(self):
        """Изображение передаётся в словаре context на страницу группы."""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        self.assertTrue(response.context['page_obj'][0].image)

    def test_post_check_context_contains_image(self):
        """Изображение передаётся в словаре context на страницу поста."""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        self.assertTrue(response.context['post'].image)