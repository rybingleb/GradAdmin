from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, SubmitField, BooleanField, TextAreaField,
    SelectField, SelectMultipleField, RadioField, DecimalField, IntegerField, DateField)
from wtforms.validators import DataRequired, Length, NumberRange, Optional
from gradadmin import app, db_conn, db_cursor as cursor
from datetime import date

today = date.today()

#cursor = db_conn.cursor()

class SearchForm(FlaskForm):
    search = StringField('search', validators=[DataRequired()])


class LoginForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить', default=True)
    submit = SubmitField('Войти')

    
class EditParam(FlaskForm):
    param_value = StringField('Значение параметра', validators=[])

    
class AddParam(FlaskForm):
    param_id = SelectField('Именование параметра')
    param_value = StringField('Значение параметра', validators=[])

    def __init__(self, party_id, *args, **kwargs):
        FlaskForm.__init__(self, *args, **kwargs)
        
        cursor.execute('''select to_char(p.id), p.name from party_params p
        where not exists (
          select 1
          from party_param_vals v
            where v.party_id = :party_id
            and v.party_param_id = p.id
        )
        order by p.name
        ''', party_id=party_id)
        self.param_id.choices = cursor.fetchall()
        
        
class AddPayment(FlaskForm):
    payment_date = DateField('Дата', format='%d.%m.%Y', default=today)
    payment_type_id = SelectField('Тип платежа', validators=[DataRequired()], default=3)
    amount = DecimalField('Сумма', validators=[DataRequired(), NumberRange(0)])
    debit = BooleanField('В дебет', default=True)
    sc_id = SelectField('Сервис-контракт', default=None)
    #description = TextAreaField('Примечание', validators=[DataRequired(), Length(min=0, max=512)])
    description = StringField('Примечание', validators=[DataRequired(), Length(min=1, max=512)])
    create_access = BooleanField('Открыть СК при наличии денег на счету', default=True)

    def __init__(self, customer_id, *args, **kwargs):
        FlaskForm.__init__(self, *args, **kwargs)
        self.customer_id = customer_id
        
        cursor.execute('''select to_char(t.id), t.name from payment_types t
        where t.can_be_manual = 1
        order by t.name
        ''')
        self.payment_type_id.choices = cursor.fetchall()
        
        cursor.execute('''
        select
            to_char(sc.id) as id,
            sc.login||'/'||tc.name||'/'||to_char(sc.begin_time, 'dd.mm.yyyy')||'-'||to_char(sc.end_time, 'dd.mm.yyyy') as descr
        from service_contracts sc, tariff_cards tc
        where sc.customer_id = :customer_id
          and sc.tariff_card <> 9
          and tc.id = sc.tariff_card
        order by sc.end_time desc
        ''', customer_id=self.customer_id)
        self.sc_id.choices = [("", "-")] + cursor.fetchall()

        
class SetNextTc(FlaskForm):
    next_tc_id = SelectField('Тарифный план', validators=[DataRequired()])
    create_access = BooleanField('Открыть СК при наличии денег на счету', default=False)
    stop_block = BooleanField('Прервать блокировку сегодняшним днем', default=False)

    def __init__(self, customer_id, login, *args, **kwargs):
        FlaskForm.__init__(self, *args, **kwargs)
        self.customer_id = customer_id
        self.login = login
        
        cursor.execute('''select a.nm_, a.nm_ from available_tc a
        where a.login = :login
        order by a.nm_
        ''', login=self.login)
        
        self.next_tc_id.choices = cursor.fetchall()
        
        
class AddRent(FlaskForm):
    contract_number = StringField('Номер договора', validators=[DataRequired()])
    passport = StringField('Паспорт', validators=[DataRequired()])
    contract_date = DateField('Дата договора', format='%d.%m.%Y', default=today)
    start_date = DateField('Дата начала списания аренды', format='%d.%m.%Y', default=today)
    service = SelectField('Услуга', validators=[DataRequired()])
    login = SelectField('Основной логин', validators=[DataRequired()])
    service_cnt = IntegerField('Кол-во', validators=[DataRequired()], default=1)
    rent_cnt = IntegerField('Сколько раз списать', validators=[Optional()])
    period = IntegerField('Период списания', validators=[Optional()])
    
    def __init__(self, customer_id, *args, **kwargs):
        FlaskForm.__init__(self, *args, **kwargs)
        self.customer_id = customer_id
        
        cursor.execute('''select cl.login, cl.login from customer_logins cl
        where cl.customer_id = :customer_id
        and cl.login not like '%-on'
        ''', customer_id=self.customer_id)
        
        self.login.choices = cursor.fetchall()
        
        cursor.execute('''select f.class, f.class from tariff_amount_fee f
        where f.tariff_card = 9
        and f.class is not null
        order by f.id
        ''')
        
        self.service.choices = cursor.fetchall()
        
class WriteoffService(FlaskForm):
    login = SelectField('Основной логин', validators=[DataRequired()])
    service = SelectField('Название услуги', validators=[DataRequired()])
    quantity = IntegerField('Объем', validators=[DataRequired()], default=1)
    
    def __init__(self, customer_id, *args, **kwargs):
        FlaskForm.__init__(self, *args, **kwargs)
        self.customer_id = customer_id
        
        cursor.execute('''select cl.login, cl.login from customer_logins cl
        where cl.customer_id = :customer_id
        and cl.login not like '%-on'
        ''', customer_id=self.customer_id)
        
        self.login.choices = cursor.fetchall()
        
        cursor.execute('''select f.class, f.class||' - '||round(xxfnd_currency.rub_amount(r.rate), 2)||' руб.' as descr
        from tariff_amount_fee f, rates_amount_fee r
        where f.tariff_card = 9
        and f.deathday > sysdate
        and r.tariff_id = f.id
        order by f.id
        ''')
        
        self.service.choices = cursor.fetchall()
        
class AddSc(FlaskForm):
    login = SelectField('Идентификатор', validators=[DataRequired()])
    rests_transfer = BooleanField('Перенести остатки из предыдущих сервис-контрактов', default=True)
    tariff_id = SelectField('Тарифный план', validators=[DataRequired()])
    begin_time = DateField('Период с', format='%d.%m.%Y', default=today)
    #end_time = DateField('по', format='%d.%m.%Y', default=today)
    ip = StringField('IP-адрес', validators=[Optional()])
    ip4pool_location_id = SelectField('Адрес подключения', validators=[DataRequired()])
    
    def __init__(self, customer_id, *args, **kwargs):
        FlaskForm.__init__(self, *args, **kwargs)
        self.customer_id = customer_id
        
        cursor.execute('''select cl.login, cl.login from customer_logins cl
        where cl.customer_id = :customer_id
        and cl.login not like '%-on'
        ''', customer_id=self.customer_id)
        
        self.login.choices = cursor.fetchall()
        
        cursor.execute('''select to_char(tc.id), tc.name||' ('||s.name||')'
        from
          tariff_cards tc,
          services s,
          xxtc_tariff_params p
        where tc.service_id in (9, 49, 65)
        and s.id = tc.service_id
        and p.tariff_id = tc.id
        and p.actual_to_date > sysdate
        and p.grad_available_flag = 1
        order by tc.id desc
        ''')
        
        self.tariff_id.choices = cursor.fetchall()
        
        cursor.execute('''select to_char(l.id), l.name from ip4pool_locations l''')
        
        self.ip4pool_location_id.choices = cursor.fetchall()
        
class EditSc(FlaskForm):
    new_end_time = DateField('по', format='%d.%m.%Y')
    new_ip = StringField('IP-адрес', validators=[Optional()])
    new_ip4pool_location_id = SelectField('Адрес подключения', validators=[DataRequired()])
    new_control_mode = SelectField('Действия при нулевом балансе', validators=[DataRequired()])

    def __init__(self, customer_id, sc_id, *args, **kwargs):
        FlaskForm.__init__(self, *args, **kwargs)
        
        self.customer_id = customer_id
        self.sc_id = sc_id
        
        cursor.execute('''select
        sc.id,
        sc.login,
        to_char(sc.begin_time, 'dd.mm.yyyy') as begin_time,
        to_char(sc.end_time, 'dd.mm.yyyy') as begin_timesc,
        tc.name,
        sc.ip,
        to_char(sc.ip4pool_location_id) as ip4pool_location_id,
        to_char(sc.control_mode) as control_mode
        from service_contracts sc, tariff_cards tc
        where sc.id = :sc_id
        and tc.id = sc.tariff_card
        ''', sc_id=self.sc_id)
        
        row = cursor.fetchone()
        self.login = row[1]
        self.begin_time = row[2]
        self.end_time = row[3]
        self.tc_name = row[4]
        self.ip = row[5]
        self.ip4pool_location_id = row[6]
        self.control_mode = row[7]
        
        cursor.execute('''select to_char(l.id), l.name from ip4pool_locations l''')
        
        self.new_ip4pool_location_id.choices = cursor.fetchall()
        
        self.new_control_mode.choices = [('0', 'отключать'), ('1', 'игнорировать')]
        
class MovePayment(FlaskForm):
    payment_sources = SelectField('Платежная система', validators=[DataRequired()])
    payment_txn_id = StringField('Идентификатор платежа', validators=[DataRequired()])
    to_login = StringField('Логин', validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        FlaskForm.__init__(self, *args, **kwargs)
        
        cursor.execute('''select s.name, s.name from payment_sources s
        ''')
        
        self.payment_sources.choices = cursor.fetchall()