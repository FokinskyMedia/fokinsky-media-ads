from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, DecimalField, DateField
from wtforms.validators import DataRequired, Optional
from datetime import date, datetime
import os

def allowed_file(filename):
    allowed_extensions = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

# Создаем экземпляры
app = Flask(__name__)
db = SQLAlchemy()

# Конфигурация
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-here-change-this'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Инициализируем базу данных
db.init_app(app)


# МОДЕЛИ
class Blogger(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    platform = db.Column(db.String(50))
    link = db.Column(db.String(300))
    contact_link = db.Column(db.String(300))  # Ссылка на ТГ блогера
    rkn_info = db.Column(db.String(300))     # РКН (ссылка или номер заявления)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Advertiser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    telegram = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Month(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    projects = db.relationship('Project', backref='month', lazy=True)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    month_id = db.Column(db.Integer, db.ForeignKey('month.id')) 
    advertiser_id = db.Column(db.Integer, db.ForeignKey('advertiser.id'))  # ✅ ДОБАВЛЕНО
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    advertiser = db.relationship('Advertiser', backref='projects')  # ✅ ДОБАВЛЕНО

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date)
    blogger_id = db.Column(db.Integer, db.ForeignKey('blogger.id'))
    advertiser_id = db.Column(db.Integer, db.ForeignKey('advertiser.id'), nullable=True)  # ✅ ДОБАВИТЬ
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True)
    month_id = db.Column(db.Integer, db.ForeignKey('month.id'), nullable=True)
    product = db.Column(db.String(200))
    cost = db.Column(db.Float)
    blogger_fee = db.Column(db.Float)
    status = db.Column(db.String(50))
    notes = db.Column(db.Text)
    link = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связи
    blogger = db.relationship('Blogger', backref='orders')
    advertiser = db.relationship('Advertiser', backref='orders')
    project = db.relationship('Project', backref='orders')
    month = db.relationship('Month', backref='orders')

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    filename = db.Column(db.String(300))
    file_type = db.Column(db.String(50))
    project_id = db.Column(db.Integer, db.ForeignKey('project.id', ondelete='CASCADE'))
    order_id = db.Column(db.Integer, db.ForeignKey('order.id', ondelete='CASCADE'))      
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.Text)

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
    contact_link = StringField('Связь с блогером (ТГ)', validators=[Optional()])
    rkn_info = StringField('РКН (ссылка/номер)', validators=[Optional()])

class AdvertiserForm(FlaskForm):
    name = StringField('Название', validators=[DataRequired()])
    telegram = StringField('Telegram', validators=[Optional()])

class ProjectForm(FlaskForm):
    name = StringField('Название', validators=[DataRequired()])
    description = TextAreaField('Описание', validators=[Optional()])
    status = SelectField('Статус', choices=[
        ('active','Активный'),
        ('finished','Завершен')
    ])

class OrderForm(FlaskForm):
    date = StringField('Дата выхода (дд.мм.гггг)', validators=[Optional()])
    blogger = SelectField('Блогер', coerce=int, validators=[Optional()])
    advertiser = SelectField('Рекламодатель', coerce=int, validators=[Optional()])
    project = SelectField('Проект', coerce=lambda x: int(x) if x else None, validators=[Optional()])  # ✅ ИСПРАВЛЕНО
    product = StringField('Продукт', validators=[Optional()])
    cost = DecimalField('Стоимость', validators=[Optional()])
    blogger_fee = DecimalField('Блогеру забирают', validators=[Optional()])
    status = SelectField('Статус', choices=[
        ('negotiation','На согласовании'),
        ('agreed','Согласован'),  
        ('paid','Опл'),
        ('published','Выложил')
    ])
    notes = TextAreaField('Заметки', validators=[Optional()])
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
    months = Month.query.order_by(Month.created_at.desc()).all()
    stats = calculate_stats()
    upcoming = upcoming_exits()
    total_projects = Project.query.count()
    total_months = len(months)
    
    # ✅ ДОБАВЛЕНО: Получаем активные проекты с расчетом дохода
    active_projects = Project.query.filter_by(status='active').all()
    projects_with_profit = []
    for project in active_projects:
        profit = 0
        for order in project.orders:
            if order.cost and order.blogger_fee:
                profit += (order.cost - order.blogger_fee)
        projects_with_profit.append({
            'project': project,
            'profit': profit
        })
    
    return render_template('index.html', 
                         months=months,
                         stats=stats, 
                         upcoming=upcoming,
                         total_projects=total_projects,
                         total_months=total_months,
                         active_projects=projects_with_profit)  # ✅ ДОБАВЛЕНО

@app.route('/month/<int:id>')
def view_month(id):
    month = Month.query.get_or_404(id)
    # ✅ ДОБАВЛЕНО: Получаем сделки без проекта для этого месяца
    orders_without_project = Order.query.filter_by(month_id=id, project_id=None).all()
    return render_template('month_view.html', month=month, orders=orders_without_project)

@app.route('/bloggers')
def bloggers():
    search_query = request.args.get('search', '')
    platform_filter = request.args.get('platform', '')
    
    query = Blogger.query
    
    if search_query:
        query = query.filter(Blogger.name.ilike(f'%{search_query}%'))
    
    if platform_filter:
        query = query.filter(Blogger.platform == platform_filter)
    
    # ✅ ИСПРАВЛЕНО: Убираем дубликаты блогеров по имени
    items = query.distinct(Blogger.name).order_by(Blogger.name).all()
    return render_template('bloggers.html', bloggers=items, search_query=search_query, platform_filter=platform_filter)

@app.route('/blogger/add', methods=['GET','POST'])
def add_blogger():
    form = BloggerForm()
    if form.validate_on_submit():
        b = Blogger(
            name=form.name.data.strip(), 
            platform=form.platform.data, 
            link=form.link.data,
            contact_link=form.contact_link.data,  # ✅ ДОБАВЛЕНО
            rkn_info=form.rkn_info.data           # ✅ ДОБАВЛЕНО
        )
        db.session.add(b)
        db.session.commit()
        flash('Блогер добавлен', 'success')  # ← ЭТА СТРОКА ДОЛЖНА БЫТЬ ПОЛНОЙ
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
        b.contact_link = form.contact_link.data  # ✅ ДОБАВЛЕНО
        b.rkn_info = form.rkn_info.data          # ✅ ДОБАВЛЕНО
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
    search_query = request.args.get('search', '')
    
    query = Advertiser.query
    
    if search_query:
        query = query.filter(Advertiser.name.ilike(f'%{search_query}%'))
    
    items = query.order_by(Advertiser.name).all()
    return render_template('advertisers.html', items=items, search_query=search_query)

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

@app.route('/months')
def months():
    items = Month.query.order_by(Month.created_at.desc()).all()
    return render_template('months.html', months=items)

@app.route('/month/add', methods=['GET','POST'])
def add_month():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if name:
            # ✅ ПРОСТО СОЗДАЕМ МЕСЯЦ БЕЗ АКТИВАЦИИ
            m = Month(name=name)
            db.session.add(m)
            db.session.commit()
            flash('Месяц создан', 'success')
            return redirect(url_for('months'))
        else:
            flash('Введите название месяца', 'danger')
    return render_template('month_form.html')

@app.route('/projects')
def projects():
    items = Project.query.order_by(Project.id.desc()).all()
    return render_template('projects.html', projects=items)

@app.route('/project/add', methods=['GET','POST'])
def add_project():
    form = ProjectForm()
    months = Month.query.order_by(Month.created_at.desc()).all()
    advertisers = Advertiser.query.order_by(Advertiser.name).all()
    
    # Получаем month_id из параметра URL (если создаем из месяца)
    month_id_from_url = request.args.get('month_id')
    
    if request.method == 'POST':
        # Если month_id передан в форме - используем его, иначе из URL
        month_id = request.form.get('month_id') or month_id_from_url
        advertiser_id = request.form.get('advertiser_id')
        
        # ✅ ДОБАВЛЕНО: Обработка нового рекламодателя
        if advertiser_id == '0':  # Если выбран "Новый рекламодатель"
            new_advertiser_name = request.form.get('new_advertiser_name', '').strip()
            if new_advertiser_name:
                new_advertiser = Advertiser(
                    name=new_advertiser_name,
                    telegram=request.form.get('new_advertiser_telegram', '')
                )
                db.session.add(new_advertiser)
                db.session.flush()  # Получаем ID нового рекламодателя
                advertiser_id = new_advertiser.id
            else:
                flash('Введите название рекламодателя', 'danger')
                return render_template('project_form.html', form=form, months=months, 
                                     advertisers=advertisers, show_month_select=show_month_select, 
                                     preselected_month_id=month_id_from_url)
        
        if not month_id:
            flash('Выберите месяц', 'danger')
            return render_template('project_form.html', form=form, months=months, 
                                 advertisers=advertisers, show_month_select=True)
        
        p = Project(
            name=form.name.data.strip(), 
            month_id=month_id,
            advertiser_id=advertiser_id,
            description=form.description.data, 
            status=form.status.data
        )
        db.session.add(p)
        db.session.commit()
        flash('Проект добавлен', 'success')
        
        # Перенаправляем в месяц, если создавали из месяца
        if month_id_from_url:
            return redirect(url_for('view_month', id=month_id_from_url))
        return redirect(url_for('projects'))
    
    # Определяем показывать ли выбор месяца
    show_month_select = not bool(month_id_from_url)
    
    return render_template('project_form.html', form=form, months=months, 
                         advertisers=advertisers,
                         show_month_select=show_month_select, 
                         preselected_month_id=month_id_from_url)

@app.route('/project/<int:id>/edit', methods=['GET','POST'])
def edit_project(id):
    project = Project.query.get_or_404(id)
    form = ProjectForm(obj=project)
    months = Month.query.order_by(Month.created_at.desc()).all()
    advertisers = Advertiser.query.order_by(Advertiser.name).all()
    
    if request.method == 'POST':
        project.name = form.name.data.strip()
        project.month_id = request.form.get('month_id')
        project.advertiser_id = request.form.get('advertiser_id')
        project.description = form.description.data
        project.status = form.status.data
        
        db.session.commit()
        flash('Проект обновлен', 'success')
        return redirect(url_for('view_project', id=project.id))
    
    # ✅ ДОБАВЛЕНО: Передаем preselected_month_id для правильной работы шаблона
    return render_template('project_form.html', form=form, months=months,
                         advertisers=advertisers, project=project,
                         preselected_month_id=project.month_id)  # ✅ ДОБАВЛЕНО

@app.route('/project/<int:id>')
def view_project(id):
    project = Project.query.get_or_404(id)
    orders = Order.query.filter_by(project_id=id).order_by(Order.date.desc()).all()
    return render_template('project_view.html', project=project, orders=orders)

@app.route('/project/<int:id>/delete', methods=['POST'])
def delete_project(id):
    p = Project.query.get_or_404(id)
    
    db.session.delete(p)
    db.session.commit()
    flash('Проект и связанные сделки удалены', 'info')
    return redirect(url_for('projects'))

@app.route('/orders')
def orders():
    items = Order.query.order_by(Order.date.desc()).all()
    return render_template('orders.html', orders=items)

@app.route('/order/add', methods=['GET','POST'])
def add_order():
    form = OrderForm()
    
    month_id_from_url = request.args.get('month_id')
    project_id_from_url = request.args.get('project_id')
    
    # ✅ ДОБАВЛЕНО: Получаем проект если передан project_id
    project = None
    if project_id_from_url:
        project = Project.query.get(project_id_from_url)
    
    # Заполняем выборы из существующих
    form.blogger.choices = [(0, '-- Новый блогер --')] + [(b.id, b.name) for b in Blogger.query.order_by(Blogger.name).all()]
    
    # ✅ ИСПРАВЛЕНО: Показываем выбор рекламодателя только если нет проекта
    if project:
        # Если создаем сделку в проекте - скрываем выбор рекламодателя
        form.advertiser.choices = []  # Пустой список
    else:
        # Если создаем сделку без проекта - показываем выбор рекламодателя
        form.advertiser.choices = [(0, '-- Новый рекламодатель --')] + [(a.id, a.name) for a in Advertiser.query.order_by(Advertiser.name).all()]
    
    form.project.choices = [('', '-- Без проекта --')] + [(p.id, p.name) for p in Project.query.order_by(Project.name).all()]
    
    if project_id_from_url:
        form.project.data = project_id_from_url
    
    if form.validate_on_submit():
        date_obj = None
        if form.date.data:
            try:
                date_obj = datetime.strptime(form.date.data, '%d.%m.%Y').date()
            except ValueError:
                flash('Неверный формат даты. Используйте дд.мм.гггг (например: 15.01.2024)', 'danger')
                return render_template('order_form.html', form=form, month_id=month_id_from_url, project_id=project_id_from_url, project=project)

        # Обработка нового блогера
        if form.blogger.data == 0:
            new_blogger = Blogger(
                name=request.form.get('new_blogger_name', '').strip(),
                platform=request.form.get('new_blogger_platform', 'tg'),
                link=request.form.get('new_blogger_link', '')
            )
            if new_blogger.name:
                db.session.add(new_blogger)
                db.session.flush()
                blogger_id = new_blogger.id
            else:
                blogger_id = None
        else:
            blogger_id = form.blogger.data

        # ✅ ИСПРАВЛЕНО: Обработка рекламодателя
        if project:
            # Если создаем сделку в проекте - берем рекламодателя из проекта
            advertiser_id = project.advertiser_id
        else:
            # Если создаем сделку без проекта - обрабатываем выбор рекламодателя
            if form.advertiser.data == 0:
                new_advertiser = Advertiser(
                    name=request.form.get('new_advertiser_name', '').strip(),
                    telegram=request.form.get('new_advertiser_telegram', '')
                )
                if new_advertiser.name:
                    db.session.add(new_advertiser)
                    db.session.flush()
                    advertiser_id = new_advertiser.id
                else:
                    advertiser_id = None
            else:
                advertiser_id = form.advertiser.data

        # Обработка проекта
        project_id = form.project.data if form.project.data else None

        o = Order(
            date=date_obj,
            blogger_id=blogger_id,
            advertiser_id=advertiser_id,
            product=form.product.data,
            cost=form.cost.data or 0,
            blogger_fee=form.blogger_fee.data or 0,
            status=form.status.data,
            link=form.link.data,
            project_id=project_id,
            month_id=month_id_from_url
        )
        db.session.add(o)
        db.session.commit()
        flash('Сделка добавлена', 'success')
        
        if project_id_from_url:
            return redirect(url_for('view_project', id=project_id_from_url))
        if month_id_from_url:
            return redirect(url_for('view_month', id=month_id_from_url))
        return redirect(url_for('orders'))
    
    # ✅ ДОБАВЛЕНО: Передаем project в шаблон
    return render_template('order_form.html', form=form, month_id=month_id_from_url, project_id=project_id_from_url, project=project)

@app.route('/order/<int:id>/edit', methods=['GET','POST'])
def edit_order(id):
    o = Order.query.get_or_404(id)
    form = OrderForm(obj=o)
    
    # Заполняем выборы
    form.blogger.choices = [(b.id, b.name) for b in Blogger.query.order_by(Blogger.name).all()]
    form.advertiser.choices = [(a.id, a.name) for a in Advertiser.query.order_by(Advertiser.name).all()]
    form.project.choices = [(p.id, p.name) for p in Project.query.order_by(Project.name).all()]
    
    if form.validate_on_submit():
        # ПРЕОБРАЗОВАНИЕ ДАТЫ ИЗ ФОРМАТА дд.мм.гггг
        date_obj = None
        if form.date.data:
            try:
                # Преобразуем из дд.мм.гггг в datetime объект
                date_obj = datetime.strptime(form.date.data, '%d.%m.%Y').date()
            except ValueError:
                flash('Неверный формат даты. Используйте дд.мм.гггг (например: 15.01.2024)', 'danger')
                return render_template('order_form.html', form=form)
        
        o.date = date_obj  # ИСПОЛЬЗУЕМ ПРЕОБРАЗОВАННУЮ ДАТУ
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
    
    # Преобразуем дату обратно в строку для отображения в форме
    if o.date:
        form.date.data = o.date.strftime('%d.%m.%Y')  # ИЗМЕНИЛИ НА %Y
    
    return render_template('order_form.html', form=form)
    
    # Преобразуем дату обратно в строку для отображения в форме
    if o.date:
        form.date.data = o.date.strftime('%d.%m.%Y') 
    
    return render_template('order_form.html', form=form)

@app.route('/order/<int:id>/delete', methods=['POST'])
def delete_order(id):
    o = Order.query.get_or_404(id)
    db.session.delete(o)
    db.session.commit()
    flash('Удалено', 'info')
    return redirect(url_for('orders'))

from werkzeug.utils import secure_filename
from flask import send_from_directory

@app.route('/documents')
def documents():
    items = Document.query.order_by(Document.created_at.desc()).all()
    return render_template('documents.html', documents=items)

@app.route('/document/upload', methods=['GET', 'POST'])
def upload_document():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Файл не выбран', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('Файл не выбран', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            doc = Document(
                name=request.form.get('name', filename),
                filename=filename,
                file_type=request.form.get('file_type', 'other'),
                project_id=request.form.get('project_id') or None,
                order_id=request.form.get('order_id') or None,
                description=request.form.get('description', '')
            )
            db.session.add(doc)
            db.session.commit()
            flash('Документ загружен', 'success')
            return redirect(url_for('documents'))
        else:
            flash('Недопустимый тип файла', 'danger')
    
    projects = Project.query.all()
    orders = Order.query.all()
    return render_template('upload_document.html', projects=projects, orders=orders)

@app.route('/document/<int:id>/delete', methods=['POST'])
def delete_document(id):
    doc = Document.query.get_or_404(id)
    
    if doc.filename:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], doc.filename)
        if os.path.exists(file_path):
            os.remove(file_path)
    
    db.session.delete(doc)
    db.session.commit()
    flash('Документ удален', 'info')
    return redirect(url_for('documents'))

@app.route('/document/<int:id>/download')
def download_document(id):
    doc = Document.query.get_or_404(id)
    return send_from_directory(app.config['UPLOAD_FOLDER'], doc.filename)

@app.route('/order/<int:id>/notes', methods=['POST'])
def update_order_notes(id):
    o = Order.query.get_or_404(id)
    data = request.get_json()
    
    if data and 'notes' in data:
        o.notes = data['notes'].strip()
        db.session.commit()
        return jsonify({'success': True})  # ← теперь работает
    
    return jsonify({'success': False}), 400

port = int(os.environ.get("PORT", 5000))
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("База данных создана!")
    
    app.run(host='0.0.0.0', port=port, debug=True)