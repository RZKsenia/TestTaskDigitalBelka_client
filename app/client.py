import requests
from flask import Flask, request, render_template, redirect, url_for
import json
import pandas as pd
from wtforms import Form, validators, fields
from waitress import serve

app = Flask(__name__) # запускем приложение как одиночный модуль
# Для реализации защиты от атак, основанных на подделке межсайтовых запросов
# (Cross-Site Request Forgery, CSRF), Flask-WTF требует от приложения
# настройки ключа шифрования. С помощью этого ключа Flask-WTF генерирует
# шифровальные блоки, которые используются для проверки аутентичности
# запросов, содержащие данные форм:
app.config['SECRET_KEY'] = 'Nbkm_Kbyltvfyy22'
server_url = 'http://172.17.0.3:8080' # адрес, по которому обращаемся к веб-серверу

class FormGetDataForPredict(Form):
    # Форма для получения данных от пользователя:
    user_name_field = fields.StringField(label='Имя пользователя:', validators=[validators.DataRequired()])
    user_password_field = fields.PasswordField(label='Пароль:', validators=[validators.DataRequired()])
    submit_btn = fields.SubmitField(label='Войти')

class LabInfoForm(Form):
    # Форма для ввода данных о концентрации веществ
    field_concentrat_title = fields.StringField() # наименование концентрата
    field_ferum = fields.StringField() # железо
    field_cremnium = fields.StringField() # кремний
    field_aluminium = fields.StringField() # алюминий
    field_calcium = fields.StringField() # кальций
    field_sera = fields.StringField() # сера

    months = ('январь', 'февраль', 'март',
              'апрель', 'май', 'июнь', 'июль',
              'август', 'сентябрь', 'октябрь',
              'ноябрь', 'декабрь')

    field_month = fields.SelectField(choices=months) # выпадающий список с перечнем месяцев

    btn_clipboard = fields.SubmitField(label='Заполнить поля из буфера обмена',
                                       name='btn_clipboard')
    btn_save = fields.SubmitField(label='Сохранить данные за месяц',
                                  name='btn_save')

    btn_show_statistic = fields.SubmitField(label='Показать статистику',
                                            name='btn_show_statistic')

# указываем декоратор маршрута, чтобы указать URL, который должен инициировать выполнение функции index
@app.route('/login', methods=['GET','POST'])
def login():
    """
    Вход в приложение
    :return:
    """
    # Получаем данные из формы:
    form_login = FormGetDataForPredict(request.form)
    user_name = form_login.user_name_field.data
    user_password = form_login.user_password_field.data
    args = {'login': user_name, 'password': user_password} # аргументы для передачи на сервер

    if form_login.submit_btn.data:
        # Если была нажата кнопка Войти
        url_to_redirect = server_url + '/api/login' # адрес, по которому отправляем запрос на сервер
        resp = requests.post(url=url_to_redirect,
                             json=args) # отправляем запрос, результат записываем в resp
        result = json.loads(resp.text) # транслируем результат

        if type(result) is not int:
            # произошла ошибка - не найден пользователь
            # выводим сообщение об ошибке не отдельной странице
            return render_template('res.html',
                                    user_id=result['error'])
        else:
            # Пользователь в БД найден,
            # переходим на страницу отображения всех данных из БД,
            # что были внесены текущим пользователем:
            return redirect(url_for('display_all_data') + '?user_name=' + user_name)
    else:
        # отображаем страницу, используя шаблон
        return render_template('login_page.html',
                               form=form_login)


@app.route('/display_all_data', methods=['GET', 'POST'])
def display_all_data():
    """
    Отображение всех данных из таблицы lab_data,
    что были внесены активным пользователем в БД
    :return:
    """
    user_name = request.args['user_name'] # получаем имя пользователя для отображения на странице
    url_to_redirect = server_url + '/api/display' # адрес запроса к серверу
    resp = requests.get(url=url_to_redirect) # отправляем запрос на сервер
    df = pd.read_json(json.loads(resp.text))  # получаем DataFrame результат запроса
    df.set_index(['Концентрат', 'Месяц'])

    form = LabInfoForm(request.form) # новый экземпляр формы для отображения на странице

    if form.btn_clipboard.data:
        # вставка данных из буфера обмена
        try:
            df_clipboard = pd.read_clipboard(header=None)

            form.field_ferum.data = df_clipboard.at[0, 0] # железо
            form.field_cremnium.data = df_clipboard.at[1, 0] # кремний
            form.field_aluminium.data = df_clipboard.at[2, 0] # алюминий
            form.field_calcium.data = df_clipboard.at[3, 0] # кальций
            form.field_sera.data = df_clipboard.at[4, 0] # сера
        except pd.errors.ParserError:
            pass

    if form.btn_save.data:
        # сохранение введённых данных в БД
        url_to_redirect = server_url + '/api/insert_lab_data' # адрес для отправки запроса на сервер
        json_args = {
                  'concentrat_title': form.field_concentrat_title.data,
                  'month':form.field_month.data,
                  'fer':form.field_ferum.data.replace(',', '.'),
                  'crmn':form.field_cremnium.data.replace(',', '.'),
                  'allum':form.field_aluminium.data.replace(',', '.'),
                  'clm':form.field_calcium.data.replace(',', '.'),
                  'sr':form.field_sera.data.replace(',', '.')} # аргументы для запроса к серверу

        resp = requests.post(url=url_to_redirect,
                             json=json_args) # отправляем запрос с аргументами на сервер
        result = json.loads(resp.text)

        if type(result) is dict:
            # произошла ошибка - не удалось добавить данные в таблицу
            # выводим сообщение об ошибке не отдельной странице
            return render_template('res.html',
                                   user_id=result['error'])

    if form.btn_show_statistic.data:
        # Показываем статистическую информацию
        url_to_redirect = server_url + '/api/report' # адрес для отправки запроса на сервер
        month = chr(34) + form.field_month.data + chr(34) # месяц сопровождается кавычками
        json_args = {'month': month} # аргумент для запроса
        resp = requests.post(url=url_to_redirect,
                             json=json_args) # отправляем запрос на сервер
        result = json.loads(resp.text)

        if type(result) is dict:
            # произошла ошибка - пользователь на авторизирован
            return render_template('res.html',
                                   user_id=result['error'])
        else:
            df = pd.read_json(json.loads(resp.text))  # получаем DataFrame результат запроса

            """
            Отображение страницы, построенной на основе шаблона, со статистической информацией.
            На страницу передаются через динамические элементы:
            back_page - ссылка для возврата
            month - месяц, за который отображается статистика
            tables - таблицы в виде страницы HTML, полученная из Dataframe: 
            """
            return render_template('work_with_statistic.html',
                                   back_page=url_for('display_all_data'),
                                   month=month,
                                   tables=[df.to_html()])

    """
    Отображение страницы, построенной на основе шаблона, со всей информацией, введённой
    в БД в таблицу lab_info текущим авторизированным пользователем.
    Через динамические элементы передаются следующие данные на страницу:
    user_name - имя пользователя, для отображения приветствия на странице 
    form - форма для ввода концентрации веществ и названия железорудного концентрата
    login_page - ссылка на страницу авторизации
    tables - таблицы в виде страницы HTML, полученная из Dataframe:
    """
    return render_template('work_with_data.html',
                           user_name=user_name,
                           form=form,
                           login_page=url_for('login'),
                           tables=[df.to_html()])


if __name__ == '__main__':
    serve(app, listen='*:3002')
