from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from rest_framework import viewsets, generics, status, permissions
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate, logout, login
from rest_framework.views import APIView
from .serializers import *
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

# HTML Views
def survey_list(request):
    """Отображает список всех опросов с фильтрацией и сортировкой"""
    surveys = Survey.objects.all()
    for survey in surveys:
        survey.update_status()  # Обновляем статус перед отображением
    question_id = request.GET.get('question')
    if question_id:
        surveys = surveys.filter(questions__id=question_id)
    sort_by = request.GET.get('sort', 'start_date')
    if sort_by in ['start_date', '-start_date', 'end_date', '-end_date']:
        surveys = surveys.order_by(sort_by)
    else:
        surveys = surveys.order_by('start_date')
    questions = Question.objects.all()
    return render(request, 'survey_list.html', {'surveys': surveys, 'questions': questions})

@login_required(login_url='/login/')
def survey_detail(request, survey_id):
    """Отображает детали конкретного опроса"""
    survey = Survey.objects.get(id=survey_id)
    survey.update_status()
    return render(request, 'survey_detail.html', {'survey': survey})

@login_required(login_url='/login/')
def survey_results(request, survey_id):
    """Отображает результаты опроса для всех зарегистрированных пользователей"""
    survey = Survey.objects.get(id=survey_id)
    survey.update_status()
    results = {}
    for question in survey.questions.all():
        responses = UserResponse.objects.filter(question=question)
        if question.question_type in ['single', 'multiple']:
            options_stats = {option.text: responses.filter(selected_option=option).count()
                            for option in question.options.all()}
            results[question.text] = {'type': question.question_type, 'stats': options_stats}
        else:
            text_answers = [r.text_response for r in responses if r.text_response]
            results[question.text] = {'type': 'text', 'answers': text_answers}
    return render(request, 'survey_results.html', {'survey': survey, 'results': results})

@login_required(login_url='/login/')
def submit_response(request, survey_id):
    """Обрабатывает отправку ответов на опрос"""
    survey = Survey.objects.get(id=survey_id)
    survey.update_status()
    if not survey.is_active:
        messages.error(request, "Этот опрос завершён, ответы больше не принимаются.")
        return redirect('survey_list')

    if request.method == 'POST':
        for question in survey.questions.all():
            response_data = {'question': question, 'user_id': request.user.id}
            if question.question_type == 'text':
                text = request.POST.get(f'text_{question.id}')
                if text:
                    response_data['text_response'] = text
                    UserResponse.objects.create(**response_data)
            else:
                option_ids = request.POST.getlist(f'option_{question.id}')
                for option_id in option_ids:
                    option = AnswerOption.objects.get(id=option_id)
                    response_data['selected_option'] = option
                    UserResponse.objects.create(**response_data)
        messages.success(request, "Ваши ответы успешно отправлены!")
        return redirect('survey_list')
    return render(request, 'survey_detail.html', {'survey': survey})

def login_view(request):
    """Логин через HTML-форму"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f"Добро пожаловать, {username}!")
            return redirect('survey_list')
        else:
            messages.error(request, "Неправильное Имя или Пароль")
    return render(request, 'login.html')

def register_view(request):
    """Регистрация через HTML-форму"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        if password != password_confirm:
            messages.error(request, "Пароли не совпадают.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Имя пользователя уже занято.")
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            user.save()
            login(request, user)
            messages.success(request, f"Добро пожаловать, {username}! Ваш аккаунт был успешно создан")
            return redirect('survey_list')
    return render(request, 'register.html')

def logout_view(request):
    """Выход через HTML"""
    logout(request)
    messages.success(request, "Вы вышли из системы. Будем рады видеть Вас снова")
    return redirect('survey_list')

@login_required
def profile_view(request):
    """Редактирование профиля через HTML"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = request.user
        if username and username != user.username and not User.objects.filter(username=username).exists():
            user.username = username
        if email and email != user.email:
            user.email = email
        if password:
            user.set_password(password)
        user.save()
        messages.success(request, "Ваш профиль был обновлён")
        return redirect('survey_list')
    return render(request, 'profile.html', {'user': request.user})

def admin_required(user):
    """Проверка, является ли пользователь админом"""
    return user.is_staff

@login_required
@user_passes_test(admin_required)
def create_survey(request):
    """Создание опроса через HTML"""
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        survey = Survey.objects.create(
            title=title,
            description=description,
            start_date=start_date,
            end_date=end_date,
            is_active=True
        )
        messages.success(request, f"Опрос '{title}' успешно создан!")
        return redirect('survey_list')
    return render(request, 'create_survey.html')

@login_required
@user_passes_test(admin_required)
def add_question(request, survey_id):
    """Добавление вопроса через HTML"""
    survey = Survey.objects.get(id=survey_id)
    if request.method == 'POST':
        text = request.POST.get('text')
        question_type = request.POST.get('question_type')
        question = Question.objects.create(survey=survey, text=text, question_type=question_type)
        if question_type in ['single', 'multiple']:
            options = request.POST.getlist('options')
            for option_text in options:
                if option_text.strip():
                    AnswerOption.objects.create(question=question, text=option_text)
        messages.success(request, f"Вопрос добавлен к опросу '{survey.title}'!")
        return redirect('survey_detail', survey_id=survey.id)
    return render(request, 'add_question.html', {'survey': survey})

@login_required
@user_passes_test(admin_required)
def edit_survey(request, survey_id):
    """Редактирование опроса через HTML с отображением текущих дат"""
    survey = Survey.objects.get(id=survey_id)
    if request.method == 'POST':
        survey.title = request.POST.get('title')
        survey.description = request.POST.get('description')
        survey.start_date = request.POST.get('start_date')
        survey.end_date = request.POST.get('end_date')
        survey.is_active = request.POST.get('is_active') == 'on'
        survey.save()
        messages.success(request, "Опрос обновлён успешно!")
        return redirect('survey_detail', survey_id=survey.id)
    return render(request, 'edit_survey.html', {'survey': survey})

@login_required
@user_passes_test(admin_required)
def delete_survey(request, survey_id):
    """Удаление опроса через HTML"""
    survey = Survey.objects.get(id=survey_id)
    if request.method == 'POST':
        survey.delete()
        messages.success(request, "Опрос удален!")
        return redirect('survey_list')
    return render(request, 'delete_confirm.html', {'object': survey, 'type': 'survey'})

@login_required
@user_passes_test(admin_required)
def manage_users(request):
    """Управление пользователями через HTML"""
    users = User.objects.all()
    if request.method == 'POST':
        action = request.POST.get('action')
        user_id = request.POST.get('user_id')
        user = User.objects.get(id=user_id)
        if action == 'delete':
            user.delete()
            messages.success(request, "Пользователь удален!")
        elif action == 'edit':
            user.username = request.POST.get('username')
            user.email = request.POST.get('email')
            if request.POST.get('password'):
                user.set_password(request.POST.get('password'))
            user.save()
            messages.success(request, "Пользователь обновлен успешно!")
    return render(request, 'manage_users.html', {'users': users})

@login_required
@user_passes_test(admin_required)
def create_user(request):
    """Создание пользователя через HTML"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        if not User.objects.filter(username=username).exists():
            User.objects.create_user(username=username, email=email, password=password)
            messages.success(request, f"Пользователь '{username}' успешно создан!")
            return redirect('manage_users')
        else:
            messages.error(request, "Имя пользователя уже занято.")
    return render(request, 'create_user.html')

# API Views
class IsAdminOrReadOnly(permissions.BasePermission):
    """Разрешение: только админ может изменять, остальные — читать"""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_staff

class UserViewSet(viewsets.ModelViewSet):
    """CRUD для пользователей через API"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminOrReadOnly]

class SurveyViewSet(viewsets.ModelViewSet):
    """CRUD для опросов через API"""
    queryset = Survey.objects.all()
    serializer_class = SurveySerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['questions']
    ordering_fields = ['start_date', 'end_date']

class QuestionViewSet(viewsets.ModelViewSet):
    """CRUD для вопросов через API"""
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    permission_classes = [IsAdminOrReadOnly]

class AnswerOptionViewSet(viewsets.ModelViewSet):
    """CRUD для вариантов ответов через API"""
    queryset = AnswerOption.objects.all()
    serializer_class = AnswerOptionSerializer
    permission_classes = [IsAdminOrReadOnly]

class UserResponseViewSet(viewsets.ModelViewSet):
    """CRUD для ответов пользователей через API"""
    queryset = UserResponse.objects.all()
    serializer_class = UserResponseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserResponse.objects.filter(user_id=self.request.user)

class SurveyStatisticsView(APIView):
    """Статистика опроса через API"""
    permission_classes = [IsAdminOrReadOnly]

    def get(self, request, survey_id):
        survey = Survey.objects.get(id=survey_id)
        responses = UserResponse.objects.filter(question__survey=survey)
        stats = {
            'total_responses': responses.count(),
            'by_question': {}
        }
        for question in survey.questions.all():
            question_responses = responses.filter(question=question)
            if question.question_type in ['single', 'multiple']:
                options_count = {
                    option.text: question_responses.filter(selected_option=option).count()
                    for option in question.options.all()
                }
                stats['by_question'][question.text] = {
                    'type': question.question_type,
                    'responses': question_responses.count(),
                    'options': options_count
                }
            else:
                text_answers = [r.text_response for r in question_responses if r.text_response]
                stats['by_question'][question.text] = {
                    'type': 'text',
                    'responses': question_responses.count(),
                    'answers': text_answers
                }
        return Response(stats, status=status.HTTP_200_OK)

class SurveyQuestionsView(generics.ListAPIView):
    """Список вопросов опроса через API"""
    serializer_class = QuestionSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        survey_id = self.kwargs['survey_id']
        return Question.objects.filter(survey_id=survey_id)

class SurveyAnswersView(generics.ListAPIView):
    """Список ответов на опрос через API"""
    serializer_class = UserResponseSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        survey_id = self.kwargs['survey_id']
        return UserResponse.objects.filter(question__survey_id=survey_id)

class SurveyAnswersByQuestionView(generics.ListAPIView):
    """Список ответов на конкретный вопрос через API"""
    serializer_class = UserResponseSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        survey_id = self.kwargs['survey_id']
        question_id = self.kwargs['question_id']
        return UserResponse.objects.filter(question__survey_id=survey_id, question_id=question_id)

class RegisterView(generics.CreateAPIView):
    """Регистрация через API"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        login(self.request, user)
        messages.success(self.request, f"Добро пожаловать, {user.username}! Ваш аккаунт создан.")

class LoginView(generics.GenericAPIView):
    """Логин через API"""
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            messages.success(request, f"С возвращением, {username}!")
            return Response({"message": "Вы успешно вошли"}, status=200)
        messages.error(request, "Неверное имя пользователя или пароль.")
        return Response({"error": "Неверные учетные данные"}, status=400)

class LogoutView(APIView):
    """Выход через API"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        logout(request)
        messages.success(request, "Вы вышли из системы.")
        return redirect('survey_list')

    def post(self, request):
        logout(request)
        messages.success(request, "Вы вышли из системы.")
        return Response(status=204)

class ChangePasswordView(generics.GenericAPIView):
    """Смена пароля через API"""
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']
        if not user.check_password(old_password):
            messages.error(request, "Неверный старый пароль.")
            return Response({"error": "Неверный старый пароль"}, status=400)
        user.set_password(new_password)
        user.save()
        messages.success(request, "Пароль успешно изменён.")
        return Response({"message": "Пароль успешно изменён"}, status=200)

class ResetPasswordView(generics.GenericAPIView):
    """Сброс пароля через API"""
    permission_classes = [IsAdminOrReadOnly]
    serializer_class = ResetPasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = serializer.validated_data['user_id']
        new_password = serializer.validated_data['new_password']
        try:
            user = User.objects.get(id=user_id)
            user.set_password(new_password)
            user.save()
            messages.success(request, "Пароль успешно сброшен.")
            return Response({"message": "Пароль успешно сброшен"}, status=200)
        except User.DoesNotExist:
            messages.error(request, "Пользователь не найден.")
            return Response({"error": "Пользователь не найден"}, status=404)