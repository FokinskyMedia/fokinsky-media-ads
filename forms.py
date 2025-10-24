from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, DecimalField, DateField
from wtforms.validators import DataRequired, Optional

class BloggerForm(FlaskForm):
    name = StringField('Имя', validators=[DataRequired()])
    platform = SelectField('Платформа', choices=[
        ('tiktok','TikTok'),
        ('tg','Telegram'),
        ('insta','Instagram'),
        ('youtube','YouTube')
    ])
    link = StringField('Ссылка', validators=[Optional()])

class AdvertiserForm(FlaskForm):
    name = StringField('Название', validators=[DataRequired()])
    telegram = StringField('Telegram', validators=[Optional()])

class ProjectForm(FlaskForm):
    name = StringField('Название', validators=[DataRequired()])
    month = StringField('Месяц', validators=[Optional()])
    description = TextAreaField('Описание', validators=[Optional()])
    status = SelectField('Статус', choices=[
        ('active','Активный'),
        ('finished','Завершен')
    ])

class OrderForm(FlaskForm):
    date = DateField('Дата выхода', validators=[Optional()], format='%Y-%m-%d')
    blogger = SelectField('Блогер', coerce=int, validators=[Optional()])
    advertiser = SelectField('Рекламодатель', coerce=int, validators=[Optional()])
    project = SelectField('Проект', coerce=int, validators=[Optional()])
    product = StringField('Продукт', validators=[Optional()])
    cost = DecimalField('Стоимость', validators=[Optional()])
    blogger_fee = DecimalField('Блогеру забирают', validators=[Optional()])
    status = SelectField('Статус', choices=[
        ('planned','Запланирован'),
        ('published','Опубликован'),
        ('paid','Оплачен')
    ])
    link = StringField('Ссылка на пост', validators=[Optional()])