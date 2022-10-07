import requests
from flask import Flask, request, render_template, redirect, url_for
import json
import pandas as pd
from wtforms import Form, validators, fields
from waitress import serve

app = Flask(__name__)  # запускем приложение как одиночный модуль
# Для реализации защиты от атак, основанных на подделке межсайтовых запросов
# (Cross-Site Request Forgery, CSRF), Flask-WTF требует от приложения
# настройки ключа шифрования. С помощью этого ключа Flask-WTF генерирует
# шифровальные блоки, которые используются для проверки аутентичности
# запросов, содержащие данные форм:
app.config['SECRET_KEY'] = 'Nbkm_Kbyltvfyy22'
server_url = 'http://172.17.0.3:8080' # адрес, по которому обращаемся к веб-серверу
# server_url = 'http://127.0.0.1:8080'

class FormGetDataForPredict(Form):
    # Форма для получения данных от пользователя:
    user_name_field = fields.StringField(label='Имя пользователя:', validators=[validators.DataRequired()])
    user_password_field = fields.PasswordField(label='Пароль:', validators=[validators.DataRequired()])
    submit_btn = fields.SubmitField(label='Войти')


class LabInfoForm(Form):
    # Форма для ввода данных о концентрации веществ

    months = [('январь', 'январь'), ('февраль', 'февраль'),
              ('март', 'март'), ('апрель', 'апрель'),
              ('май', 'май'), ('июнь', 'июнь'),
              ('июль', 'июль'), ('август', 'асгуст'),
              ('сентябрь', 'сентябрь'), ('октябрь', 'октябрь'),
              ('ноябрь', 'ноябрь'), ('декабрь', 'декабрь')]

    field_month = fields.SelectField(choices=months)  # выпадающий список с перечнем месяцев
    field_month.name = "month_title"

    btn_save = fields.SubmitField(label='Сохранить данные за месяц',
                                  name='btn_save')

    btn_show_statistic = fields.SubmitField(label='Показать статистику',
                                            name='btn_show_statistic')


# указываем декоратор маршрута, чтобы указать URL, который должен инициировать выполнение функции index
@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Вход в приложение
    :return:
    """
    # Получаем данные из формы:
    form_login = FormGetDataForPredict(request.form)
    user_name = form_login.user_name_field.data
    user_password = form_login.user_password_field.data
    args = {'login': user_name, 'password': user_password}  # аргументы для передачи на сервер

    if form_login.submit_btn.data:
        # Если была нажата кнопка Войти
        url_to_redirect = server_url + '/api/login'  # адрес, по которому отправляем запрос на сервер
        resp = requests.post(url=url_to_redirect,
                             json=args)  # отправляем запрос, результат записываем в resp
        result = json.loads(resp.text)  # транслируем результат

        if type(result) is not int:
            # произошла ошибка - не найден пользователь
            # выводим сообщение об ошибке не отдельной странице
            return render_template('res.html',
                                   user_id=result['error'])
        else:
            # Пользователь в БД найден,
            # переходим на страницу отображения всех данных из БД,
            # что были внесены текущим пользователем:
            return redirect(url_for('display_all_data')+'?user_name='+user_name)
    else:
        # отображаем страницу, используя шаблон
        return render_template('login_page.html',
                               form=form_login)


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    """
    Выйти из системы
    :return:
    """
    url_to_redirect = server_url + '/api/logout'  # адрес запроса к серверу
    requests.get(url=url_to_redirect)  # отправляем запрос на сервер
    return redirect(url_for('login'))


@app.route('/display_all_data', methods=['GET', 'POST'])
def display_all_data():
    """
    Отображение всех данных из таблицы lab_data,
    что были внесены активным пользователем в БД
    :return:
    """
    if 'user_name' in request.args or 'user_name' in request.get_json():
        if 'user_name' in request.args:
            user_name = request.args['user_name']  # получаем имя пользователя для отображения на странице
        elif 'user_name' in request.get_json():
            user_name = request.get_json()['user_name']

        url_to_redirect = server_url + '/api/display'   # адрес запроса к серверу
        # отправляем запрос на сервер
        # Результатом будет текстовая строка, в формате, пригодном для создания JSON:
        args_to_send = '{"user_name":' + chr(34) + user_name + chr(34) + '}'
        resp = requests.get(url=url_to_redirect,
                            json=args_to_send)
        json_resp = json.loads(resp.text)

        if 'error' not in json_resp:
            df = pd.read_json(resp.text)  # получаем DataFrame результат запроса
            if df.shape[0] != 0:
                df.set_index(['Концентрат', 'Месяц'])
            else:
                # если в БД ещё нет для авторизированного пользователя
                   # никаких записей о содержании веществ в железорудном концентрате,
                # то выводим пустой Dataframe:
                dt_for_df = {'Концентрат': '',
                             'Месяц': '',
                             'Железо': '',
                             'Кремний': '',
                             'Алюминий': '',
                             'Кальций': '',
                             'Сера': ''
                             }
                df = pd.DataFrame(dt_for_df, index=['0'])

            form_lab = LabInfoForm(request.form)  # новый экземпляр формы для отображения на странице

            if form_lab.btn_show_statistic.data:
                # Показываем статистическую информацию
                url_to_redirect = server_url + '/api/report'  # адрес для отправки запроса на сервер
                month = chr(34) + form_lab.field_month.data + chr(34)  # месяц сопровождается кавычками
                json_args = {'month': month}  # аргумент для запроса

                resp = requests.post(url=url_to_redirect,
                                     json=json_args)  # отправляем запрос на сервер

                result = json.loads(resp.text)

                if type(result) is dict:
                    # произошла ошибка - пользователь на авторизирован
                    return render_template('res.html',
                                           user_id=result['error'])
                else:
                    df = pd.read_json(json.loads(resp.text))  # получаем DataFrame результат запроса

                    if df.shape[0] == 0:
                        # если в БД ещё нет для авторизированного пользователя
                        # никаких записей о содержании веществ в железорудном концентрате,
                        # то выводим пустой Dataframe:
                        dt_for_df = {'Концентрат': '',
                                     'Месяц': '',
                                     'Железо': '',
                                     'Кремний': '',
                                     'Алюминий': '',
                                     'Кальций': '',
                                     'Сера': ''
                                     }
                        df = pd.DataFrame(dt_for_df, index=['0'])
                    """
                    Отображение страницы, построенной на основе шаблона, со статистической информацией.
                    На страницу передаются через динамические элементы:
                    back_page - ссылка для возврата
                    month - месяц, за который отображается статистика
                    tables - таблицы в виде страницы HTML, полученная из Dataframe:                     
                    """
                    headers = ['mean', 'min', 'max']*5
                    df_new = df.rename(
                        columns={
                        "('Железо', 'mean')": "mean",
                        "('Железо', 'amin')": "min",
                        "('Железо', 'amax')": "max",
                        "('Кремний', 'mean')": "mean",
                        "('Кремний', 'amin')": "min",
                        "('Кремний', 'amax')": "max",
                        "('Алюминий', 'mean')": "mean",
                        "('Алюминий', 'amin')": "min",
                        "('Алюминий', 'amax')": "max",
                        "('Кальций', 'mean')": "mean",
                        "('Кальций', 'amin')": "min",
                        "('Кальций', 'amax')": "max",
                        "('Сера', 'mean')": "mean",
                        "('Сера', 'amin')": "min",
                        "('Сера', 'amax')": "max",
                    })

                    return render_template('work_with_statistic.html',
                                           back_page=url_for('display_all_data') + '?user_name=' + user_name,
                                           month=month,
                                           tables=[df_new.to_html(classes='data',
                                                                  table_id='spreadsheet')])

            """
            Отображение страницы, построенной на основе шаблона, со всей информацией, введённой
            в БД в таблицу lab_info текущим авторизированным пользователем.
            Через динамические элементы передаются следующие данные на страницу:
            user_name - имя пользователя, для отображения приветствия на странице 
            form - форма для ввода концентрации веществ и названия железорудного концентрата
            login_page - ссылка на страницу авторизации
            tables - таблицы в виде страницы HTML, полученная из Dataframe:
            """
            url_for_post = server_url + '/api/insert_lab_data'  # адрес запроса к серверу

            return render_template('work_with_data.html',
                                   user_name=user_name,
                                   form=form_lab,
                                   login_page=url_for('logout'),
                                   tables=[df.to_html(classes='data',
                                                      table_id='spreadsheet',
                                                      index=False)],
                                   url_to_redirect=url_for_post,
                                   usr=user_name)
        else:
            # произошла ошибка - попытка не авторизованного доступа
            # выводим сообщение об ошибке не отдельной странице
            return render_template('res.html',
                                   user_id=resp.json()['error'])

def prepare_json_df_for_page_template(df):
    """
    Подготовка JSON для передачи в шаблон страницы
    для последующей обработки его скриптом
    :param json_string_from_df:
    :return:
    """
    return json.loads(df.to_json(orient="values"))

if __name__ == '__main__':
    #serve(app, listen='*:3002')
    app.run(debug=False, host='0.0.0.0')
