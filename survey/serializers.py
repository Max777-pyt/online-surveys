from rest_framework import serializers
from .models import *
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для пользователей: CRUD через API"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def validate(self, data):
        """Проверка данных при создании/обновлении"""
        if self.context['request'].method == 'POST':
            if User.objects.filter(username=data.get('username')).exists():
                raise serializers.ValidationError("Имя пользователя уже занято.")
        return data

    def create(self, validated_data):
        """Создание пользователя"""
        user = User.objects.create_user(**validated_data)
        return user

    def update(self, instance, validated_data):
        """Обновление пользователя с сохранением пароля"""
        instance.username = validated_data.get('username', instance.username)
        instance.email = validated_data.get('email', instance.email)
        if 'password' in validated_data:
            instance.set_password(validated_data['password'])
        instance.save()
        return instance

class SurveySerializer(serializers.ModelSerializer):
    """Сериализатор для опросов: CRUD через API"""
    def validate(self, data):
        """Проверка, что end_date позже start_date, если оба указаны"""
        start_date = data.get('start_date', self.instance.start_date if self.instance else None)
        end_date = data.get('end_date', self.instance.end_date if self.instance else None)
        if start_date and end_date and end_date <= start_date:
            raise serializers.ValidationError("Дата окончания должна быть позже даты начала.")
        return data

    class Meta:
        model = Survey
        fields = ['id', 'title', 'description', 'start_date', 'end_date', 'is_active']

class QuestionSerializer(serializers.ModelSerializer):
    """Сериализатор для вопросов"""
    class Meta:
        model = Question
        fields = ['id', 'survey', 'text', 'question_type']

class AnswerOptionSerializer(serializers.ModelSerializer):
    """Сериализатор для вариантов ответов"""
    class Meta:
        model = AnswerOption
        fields = ['id', 'question', 'text']

class UserResponseSerializer(serializers.ModelSerializer):
    """Сериализатор для ответов пользователей"""
    class Meta:
        model = UserResponse
        fields = ['id', 'question', 'selected_option', 'text_response']

class LoginSerializer(serializers.Serializer):
    """Сериализатор для логина через API"""
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

class ChangePasswordSerializer(serializers.Serializer):
    """Сериализатор для смены пароля через API"""
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)

class ResetPasswordSerializer(serializers.Serializer):
    """Сериализатор для сброса пароля через API"""
    user_id = serializers.IntegerField(required=True)
    new_password = serializers.CharField(required=True, write_only=True)