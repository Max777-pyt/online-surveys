from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *


router = DefaultRouter()
router.register(r'users', UserViewSet, basename='users')
router.register(r'surveys', SurveyViewSet, basename='surveys')
router.register(r'questions', QuestionViewSet, basename='questions')
router.register(r'answers', AnswerOptionViewSet, basename='answers')
router.register(r'responses', UserResponseViewSet, basename='responses')


urlpatterns = [
    path('', survey_list, name='survey_list'),

    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register_view, name='register'),
    path('profile/', profile_view, name='profile'),
    path('create-survey/', create_survey, name='create_survey'),
    path('survey/<int:survey_id>/', survey_detail, name='survey_detail'),
    path('survey/<int:survey_id>/submit/', submit_response, name='submit_response'),
    path('survey/<int:survey_id>/results/', survey_results, name='survey_results'),
    path('survey/<int:survey_id>/add-question/', add_question, name='add_question'),
    path('survey/<int:survey_id>/edit/', edit_survey, name='edit_survey'),
    path('survey/<int:survey_id>/delete/', delete_survey, name='delete_survey'),
    path('manage-users/', manage_users, name='manage_users'),
    path('create-user/', create_user, name='create_user'),


    path('api/', include(router.urls)),
    path('api/register/', RegisterView.as_view(), name='api_register'),
    path('api/login/', LoginView.as_view(), name='api_login'),
    path('api/logout/', LogoutView.as_view(), name='api_logout'),
    path('api/change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('api/reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('api/surveys/<int:survey_id>/statistics/', SurveyStatisticsView.as_view(), name='survey-statistics'),
    path('api/surveys/<int:survey_id>/questions/', SurveyQuestionsView.as_view(), name='survey-questions'),
    path('api/surveys/<int:survey_id>/answers/', SurveyAnswersView.as_view(), name='survey-answers'),
    path('api/surveys/<int:survey_id>/questions/<int:question_id>/answers/', SurveyAnswersByQuestionView.as_view(), name='survey-answers-by-question'),
]