from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Survey, Question, AnswerOption, UserResponse
from django.utils import timezone
from datetime import date


class SurveyTests(TestCase):
    def setUp(self):
        self.client = APIClient()  # Для публичных запросов и неавторизованных
        self.admin_client = APIClient()  # Для админа
        self.user_client = APIClient()  # Для обычного пользователя

        # Создаём админа и пользователя
        self.admin = User.objects.create_user(username='admin', password='admin123', is_staff=True)
        self.user = User.objects.create_user(username='testuser', password='test123')

        # Логиним админа и пользователя через сессии
        self.admin_client.login(username='admin', password='admin123')
        self.user_client.login(username='testuser', password='test123')

        # Данные для опроса с объектами date
        self.survey_data = {
            'title': 'Test Survey',
            'description': 'Test description',
            'start_date': date(2025, 3, 1),
            'end_date': date(2025, 3, 10),
            'is_active': True
        }
        self.survey = Survey.objects.create(**self.survey_data)

    # Тесты для User через API
    def test_create_user_api(self):
        response = self.client.post(reverse('api_register'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpass123'
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(User.objects.count(), 3)
        self.assertEqual(User.objects.last().username, 'newuser')

    def test_get_all_users_api(self):
        response = self.admin_client.get('/api/users/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)  # admin и testuser

    def test_get_user_by_id_api(self):
        response = self.admin_client.get(f'/api/users/{self.user.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['username'], 'testuser')

    def test_update_user_api(self):
        response = self.admin_client.patch(f'/api/users/{self.user.id}/', {
            'email': 'newemail@example.com'
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.get(id=self.user.id).email, 'newemail@example.com')

    def test_delete_user_api(self):
        response = self.admin_client.delete(f'/api/users/{self.user.id}/')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(User.objects.count(), 1)

    def test_login_user_api(self):
        response = self.client.post(reverse('api_login'), {
            'username': 'testuser',
            'password': 'test123'
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['message'], 'Вы успешно вошли')

    def test_logout_user_api(self):
        response = self.user_client.post(reverse('api_logout'))
        self.assertEqual(response.status_code, 204)

    def test_change_password_api(self):
        response = self.user_client.post(reverse('change-password'), {
            'old_password': 'test123',
            'new_password': 'newpass456'
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['message'], 'Пароль успешно изменён')

    def test_reset_password_api(self):
        response = self.admin_client.post(reverse('reset-password'), {
            'user_id': self.user.id,
            'new_password': 'resetpass789'
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['message'], 'Пароль успешно сброшен')

    # Тесты для Survey через API
    def test_create_survey_api(self):
        response = self.admin_client.post(reverse('surveys-list'), self.survey_data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Survey.objects.count(), 2)

    def test_get_all_surveys_api(self):
        response = self.admin_client.get(reverse('surveys-list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_filter_surveys_by_questions_api(self):
        question = Question.objects.create(survey=self.survey, text='Q1', question_type='text')
        response = self.admin_client.get(f"{reverse('surveys-list')}?questions={question.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_sort_surveys_by_date_api(self):
        response = self.admin_client.get(f"{reverse('surveys-list')}?ordering=-start_date")
        self.assertEqual(response.status_code, 200)

    def test_get_survey_by_id_api(self):
        response = self.admin_client.get(reverse('surveys-detail', kwargs={'pk': self.survey.id}))
        self.assertEqual(response.status_code, 200)

    def test_update_survey_api(self):
        response = self.admin_client.patch(reverse('surveys-detail', kwargs={'pk': self.survey.id}), {
            'title': 'Updated Survey'
        }, format='json')
        self.assertEqual(response.status_code, 200)

    def test_delete_survey_api(self):
        response = self.admin_client.delete(reverse('surveys-detail', kwargs={'pk': self.survey.id}))
        self.assertEqual(response.status_code, 204)

    def test_survey_status_update(self):
        past_survey = Survey.objects.create(
            title='Past Survey',
            description='Expired',
            start_date=date(2025, 2, 1),
            end_date=date(2025, 3, 1),  # Прошедшая дата
            is_active=True
        )
        past_survey.update_status()
        self.assertFalse(past_survey.is_active)
        response = self.user_client.get(reverse('survey_results', kwargs={'survey_id': past_survey.id}))
        self.assertEqual(response.status_code, 200)  # Результаты доступны
        response = self.user_client.get(reverse('survey_list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('Past Survey', response.content.decode())  # Все опросы отображаются

    def test_unauthorized_access_to_survey_detail(self):
        response = self.client.get(reverse('survey_detail', kwargs={'survey_id': self.survey.id}))
        self.assertEqual(response.status_code, 302)  # Перенаправление
        self.assertIn('/login/', response.url)  # На страницу входа

    def test_unauthorized_access_to_survey_results(self):
        response = self.client.get(reverse('survey_results', kwargs={'survey_id': self.survey.id}))
        self.assertEqual(response.status_code, 302)  # Перенаправление
        self.assertIn('/login/', response.url)  # На страницу входа

    # Тесты для Question через API
    def test_create_question_api(self):
        response = self.admin_client.post(reverse('questions-list'), {
            'survey': self.survey.id,
            'text': 'Q1',
            'question_type': 'single'
        }, format='json')
        self.assertEqual(response.status_code, 201)

    # Тесты для AnswerOption через API
    def test_create_answer_option_api(self):
        question = Question.objects.create(survey=self.survey, text='Q1', question_type='single')
        response = self.admin_client.post(reverse('answers-list'), {
            'question': question.id,
            'text': 'Option 1'
        }, format='json')
        self.assertEqual(response.status_code, 201)

    # Тесты для UserResponse через API
    def test_create_user_response_api(self):
        question = Question.objects.create(survey=self.survey, text='Q1', question_type='single')
        option = AnswerOption.objects.create(question=question, text='Option 1')
        response = self.user_client.post(reverse('responses-list'), {
            'question': question.id,
            'selected_option': option.id
        }, format='json')
        self.assertEqual(response.status_code, 201)

class SurveyIntegrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(username='admin', password='admin123', is_staff=True)
        self.user = User.objects.create_user(username='testuser', password='test123')
        self.client.login(username='admin', password='admin123')
        self.user_client = APIClient()
        self.user_client.login(username='testuser', password='test123')

    def test_full_survey_flow(self):
        survey_data = {
            'title': 'Integration Test Survey',
            'description': 'Testing full flow',
            'start_date': date(2025, 3, 1),
            'end_date': date(2025, 3, 10),
            'is_active': True
        }
        survey_response = self.client.post(reverse('surveys-list'), survey_data, format='json')
        survey_id = survey_response.data['id']

        question_data = {'survey': survey_id, 'text': 'Do you like this survey?', 'question_type': 'single'}
        question_response = self.client.post(reverse('questions-list'), question_data, format='json')
        question_id = question_response.data['id']

        option_data = {'question': question_id, 'text': 'Yes'}
        option_response = self.client.post(reverse('answers-list'), option_data, format='json')
        option_id = option_response.data['id']

        response_data = {'question': question_id, 'selected_option': option_id}
        user_response = self.user_client.post(reverse('responses-list'), response_data, format='json')

        stats_response = self.client.get(reverse('survey-statistics', kwargs={'survey_id': survey_id}))

        self.assertEqual(survey_response.status_code, 201)
        self.assertEqual(question_response.status_code, 201)
        self.assertEqual(option_response.status_code, 201)
        self.assertEqual(user_response.status_code, 201)
        self.assertEqual(stats_response.status_code, 200)
        self.assertEqual(stats_response.data['total_responses'], 1)