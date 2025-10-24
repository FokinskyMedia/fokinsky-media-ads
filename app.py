from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, DecimalField, DateField
from wtforms.validators import DataRequired, Optional
from datetime import date, datetime
import os

# Создаем экземпляры
app = Flask(__name__)
db = SQLAlchemy()

# Конфигурация
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-here-change-this'

# Инициализируем базу данных
db.init_app(app)

# МОДЕЛИ
class Blogger(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    platform = db.Column(db.String(50))
    link = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    orders = db.relationship('Order', backref='blogger', lazy=True)

class Advertiser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    telegram = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    orders = db.relationship('Order', backref='advertiser', lazy=True)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    month = db.Column(db.String(50))
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    orders = db.relationship('Order', backref='project', lazy=True)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date)
    blogger_id = db.Column(db.Integer, db.ForeignKey('blogger.id'))
    advertiser_id = db.Column(db.Integer, db.ForeignKey('advertiser.id'))
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    product = db.Column(db.String(300))
    cost = db.Column(db.Float, default=0)
    blogger_fee = db.Column(db.Float, default=0)
    status = db.Column(db.String(50), default='planned')
    link = db.Column(db.String(300))

# ФОРМЫ
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

# ФУНКЦИИ
def calculate_stats():
    total_orders = Order.query.count()
    total_revenue = db.session.query(db.func.sum(Order.cost)).scalar() or 0
    total_paid_out = db.session.query(db.func.sum(Order.blogger_fee)).scalar() or 0
    profit = (total_revenue - total_paid_out) or 0
    active_projects = Project.query.filter_by(status='active').count()
    return {
        'total_orders': total_orders,
        'revenue': total_revenue,
        'paid_out': total_paid_out,
        'profit': profit,
        'active_projects': active_projects
    }

def upcoming_exits(day=None):
    if day is None:
        day = date.today().day
    today = date.today()
    orders = Order.query.order_by(Order.date.asc()).all()
    upcoming = [o for o in orders if o.date and o.date.month == today.month and o.date.day >= day]
    return upcoming[:10]

# МАРШРУТЫ
@app.route('/')
def index():
    projects = Project.query.order_by(Project.id.desc()).all()
    stats = calculate_stats()
    upcoming = upcoming_exits()
    return render_template('index.html', projects=projects, stats=stats, upcoming=upcoming)

@app.route('/bloggers')
def bloggers():
    items = Blogger.query.order_by(Blogger.name).all()
    return render_template('bloggers.html', bloggers=items)

@app.route('/blogger/add', methods=['GET','POST'])
def add_blogger():
    form = BloggerForm()
    if form.validate_on_submit():
        b = Blogger(name=form.name.data.strip(), platform=form.platform.data, link=form.link.data)
        db.session.add(b)
        db.session.commit()
        flash('Блогер добавлен', 'success')
        return redirect(url_for('bloggers'))
    return render_template('blogger_form.html', form=form)

@app.route('/blogger/<int:id>/edit', methods=['GET','POST'])
def edit_blogger(id):
    b = Blogger.query.get_or_404(id)
    form = BloggerForm(obj=b)
    if form.validate_on_submit():
        b.name = form.name.data.strip()
        b.platform = form.platform.data
        b.link = form.link.data
        db.session.commit()
        flash('Сохранено', 'success')
        return redirect(url_for('bloggers'))
    return render_template('blogger_form.html', form=form)

@app.route('/blogger/<int:id>/delete', methods=['POST'])
def delete_blogger(id):
    b = Blogger.query.get_or_404(id)
    db.session.delete(b)
    db.session.commit()
    flash('Удалено', 'info')
    return redirect(url_for('bloggers'))

@app.route('/advertisers')
def advertisers():
    items = Advertiser.query.order_by(Advertiser.name).all()
    return render_template('advertisers.html', items=items)

@app.route('/advertiser/add', methods=['GET','POST'])
def add_advertiser():
    form = AdvertiserForm()
    if form.validate_on_submit():
        a = Advertiser(name=form.name.data.strip(), telegram=form.telegram.data)
        db.session.add(a)
        db.session.commit()
        flash('Добавлено', 'success')
        return redirect(url_for('advertisers'))
    return render_template('advertiser_form.html', form=form)

@app.route('/advertiser/<int:id>/edit', methods=['GET','POST'])
def edit_advertiser(id):
    a = Advertiser.query.get_or_404(id)
    form = AdvertiserForm(obj=a)
    if form.validate_on_submit():
        a.name = form.name.data.strip()
        a.telegram = form.telegram.data
        db.session.commit()
        flash('Сохранено', 'success')
        return redirect(url_for('advertisers'))
    return render_template('advertiser_form.html', form=form)

@app.route('/advertiser/<int:id>/delete', methods=['POST'])
def delete_advertiser(id):
    a = Advertiser.query.get_or_404(id)
    db.session.delete(a)
    db.session.commit()
    flash('Удалено', 'info')
    return redirect(url_for('advertisers'))

@app.route('/projects')
def projects():
    items = Project.query.order_by(Project.id.desc()).all()
    return render_template('projects.html', projects=items)

@app.route('/project/add', methods=['GET','POST'])
def add_project():
    form = ProjectForm()
    if form.validate_on_submit():
        p = Project(name=form.name.data.strip(), month=form.month.data, description=form.description.data, status=form.status.data)
        db.session.add(p)
        db.session.commit()
        flash('Проект добавлен', 'success')
        return redirect(url_for('projects'))
    return render_template('project_form.html', form=form)

@app.route('/project/<int:id>/edit', methods=['GET','POST'])
def edit_project(id):
    p = Project.query.get_or_404(id)
    form = ProjectForm(obj=p)
    if form.validate_on_submit():
        p.name = form.name.data.strip()
        p.month = form.month.data
        p.description = form.description.data
        p.status = form.status.data
        db.session.commit()
        flash('Сохранено', 'success')
        return redirect(url_for('projects'))
    return render_template('project_form.html', form=form)

@app.route('/project/<int:id>/view')
def view_project(id):
    p = Project.query.get_or_404(id)
    orders = Order.query.filter_by(project_id=id).order_by(Order.date.asc()).all()
    return render_template('project_view.html', project=p, orders=orders)

@app.route('/project/<int:id>/delete', methods=['POST'])
def delete_project(id):
    p = Project.query.get_or_404(id)
    db.session.delete(p)
    db.session.commit()
    flash('Удалено', 'info')
    return redirect(url_for('projects'))

@app.route('/orders')
def orders():
    items = Order.query.order_by(Order.date.desc()).all()
    return render_template('orders.html', orders=items)

@app.route('/order/add', methods=['GET','POST'])
def add_order():
    form = OrderForm()
    # Заполняем выборы
    form.blogger.choices = [(b.id, b.name) for b in Blogger.query.order_by(Blogger.name).all()]
    form.advertiser.choices = [(a.id, a.name) for a in Advertiser.query.order_by(Advertiser.name).all()]
    form.project.choices = [(p.id, p.name) for p in Project.query.order_by(Project.name).all()]
    
    if form.validate_on_submit():
        o = Order(
            date=form.date.data,
            blogger_id=form.blogger.data,
            advertiser_id=form.advertiser.data,
            product=form.product.data,
            cost=form.cost.data or 0,
            blogger_fee=form.blogger_fee.data or 0,
            status=form.status.data,
            link=form.link.data,
            project_id=form.project.data
        )
        db.session.add(o)
        db.session.commit()
        flash('Сделка добавлена', 'success')
        return redirect(url_for('orders'))
    return render_template('order_form.html', form=form)

@app.route('/order/<int:id>/edit', methods=['GET','POST'])
def edit_order(id):
    o = Order.query.get_or_404(id)
    form = OrderForm(obj=o)
    # Заполняем выборы
    form.blogger.choices = [(b.id, b.name) for b in Blogger.query.order_by(Blogger.name).all()]
    form.advertiser.choices = [(a.id, a.name) for a in Advertiser.query.order_by(Advertiser.name).all()]
    form.project.choices = [(p.id, p.name) for p in Project.query.order_by(Project.name).all()]
    
    if form.validate_on_submit():
        o.date = form.date.data
        o.blogger_id = form.blogger.data
        o.advertiser_id = form.advertiser.data
        o.product = form.product.data
        o.cost = form.cost.data or 0
        o.blogger_fee = form.blogger_fee.data or 0
        o.status = form.status.data
        o.link = form.link.data
        o.project_id = form.project.data
        db.session.commit()
        flash('Сохранено', 'success')
        return redirect(url_for('orders'))
    return render_template('order_form.html', form=form)

@app.route('/order/<int:id>/delete', methods=['POST'])
def delete_order(id):
    o = Order.query.get_or_404(id)
    db.session.delete(o)
    db.session.commit()
    flash('Удалено', 'info')
    return redirect(url_for('orders'))
port = int(os.environ.get("PORT", 5000))
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("База данных создана!")
    
    app.run(host='0.0.0.0', port=port, debug=True)