from flask_login import UserMixin
from gradadmin import login
from werkzeug.security import generate_password_hash, check_password_hash
from gradadmin import db_conn, db_cursor as cursor
from flask_login import current_user

class MenuItem:
    def __init__(self, text, href):
        self.text = text
        self.href = href
        
class User(UserMixin):
    def __init__(self, login):
        self.login = login
        cursor.execute('''select cl.password, cl.customer_id, pd.party_type
        from customer_logins cl, party_departments pd
        where cl.login = :login
        --and pd.party_type <> 0
        and pd.party_id = cl.customer_id
        ''', login=self.login)
        row = cursor.fetchone()
        
        if row:
            self.password_hash = generate_password_hash(row[0])
            self.customer_id = row[1]
            self.party_type = row[2]

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    is_authenticated = True

    def is_active(self):
        #return True
        if self.party_type == 0:
            return False
        else:
            return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.login)
        #if self.party_type == 0:
        #    return None
        #else:
        #    return str(self.login)
        
@login.user_loader
def load_user(id):
    return User(id)
    
class Customer():
    def __init__(self, id):
        self.id = id
        #Действующие сервис-контракты
        cursor.execute('''select
          sc.id,
          sc.login,
          s.name,
          tc.name,
          to_char(sc.begin_time, 'dd.mm.yyyy'),
          to_char(sc.end_time, 'dd.mm.yyyy'),
          trunc(xxfnd_currency.rub_amount(sc.debet), 2),
          trunc(xxfnd_currency.rub_amount(sc.credit), 2),
          trunc(xxfnd_currency.rub_amount(sc.balance), 2),
          nvl(sc.ip, '-') as ip
        from
          service_contracts sc,
          services s,
          tariff_cards tc
        where sc.customer_id = :customer_id
          and sc.end_time > sysdate
          and tc.id = sc.tariff_card
          and s.id = tc.service_id
        order by sc.end_time desc, sc.begin_time
        ''', customer_id=self.id)    

        self.sc_list = cursor.fetchall()

        #Устаревшие сервис-контракты
        cursor.execute('''select
          sc.id,
          sc.login,
          s.name,
          tc.name,
          to_char(sc.begin_time, 'dd.mm.yyyy'),
          to_char(sc.end_time, 'dd.mm.yyyy'),
          trunc(xxfnd_currency.rub_amount(sc.debet), 2),
          trunc(xxfnd_currency.rub_amount(sc.credit), 2),
          trunc(xxfnd_currency.rub_amount(sc.balance), 2),
          nvl(sc.ip, '-') as ip
        from
          service_contracts sc,
          services s,
          tariff_cards tc
        where sc.customer_id = :customer_id
          and sc.end_time <= sysdate
          and tc.id = sc.tariff_card
          and s.id = tc.service_id
        order by sc.end_time desc, sc.begin_time
        ''', customer_id=self.id)    

        self.old_sc_list = cursor.fetchall()

        #контактные данные
        cursor.execute('''select
          p.name,
          p.short_name,
          p.cn_last_name,
          p.cn_first_name,
          p.cn_middle_name,
          p.phone,
          p.email,
          decode(p.legalentity, 0, 'Физическое', 1, 'Юридическое') as legalentity,
          p.primary_addr_domain,
          p.primary_addr_postal,
          p.primary_addr_city,
          p.primary_addr_street,
          p.tax_code,
          p.pdv_tax_code,
          a.domain as real_domain,
          a.city as real_city,
          a.street_addr as real_street_addr,
          a.postal_code as real_postal_code,
          p.bank_name,
          p.bank_location
        from parties p, party_add_addresses a
        where p.id = :customer_id
            and a.party_id(+) = p.id
            and a.addr_key(+) = 'real'
        ''', customer_id=self.id)

        row = cursor.fetchone()
        self.name = row[0]
        self.short_name = row[1]
        self.cn_last_name = row[2]
        self.cn_first_name = row[3]
        self.cn_middle_name = row[4]
        self.phone = row[5]
        self.email = row[6]
        self.legalentity = row[7]
        self.primary_addr_domain = row[8]
        self.primary_addr_postal = row[9]
        self.primary_addr_city = row[10]
        self.primary_addr_street = row[11]
        self.tax_code = row[12]
        self.pdv_tax_code = row[13]
        self.real_domain = row[14]
        self.real_city = row[15]
        self.real_street_addr = row[16]
        self.real_postal_code = row[17]
        self.bank_name = row[18]
        self.bank_location = row[19]

        #единый счет
        cursor.execute('''select trunc(xxfnd_currency.rub_amount(a.balance), 2) from xxbl_customer_accounts a
        where a.customer_id = :customer_id
        ''', customer_id=self.id)

        row = cursor.fetchone()
        if row:
            self.balance = row[0]
        else:
            self.balance = '-'
            
        #нераспределенные платежи
        cursor.execute('''select trunc(xxfnd_currency.rub_amount(r.balance), 2)
        from receipts_unallotted r
        where r.customer_id = :customer_id
        ''', customer_id=self.id)

        row = cursor.fetchone()
        if row:
            self.balance_unallotted = row[0]
            
        #остатки по закрытым сервис-контрактам
        cursor.execute('''select trunc(xxfnd_currency.rub_amount(sum(sc.balance)), 2) as balance
        from service_contracts sc
        where sc.customer_id = :customer_id
        and sc.end_time < sysdate
        ''', customer_id=self.id)

        row = cursor.fetchone()
        if row:
            self.rests = row[0]

        cursor.execute('''select sc.login, tc.name, trunc(xxfnd_currency.rub_amount(nvl(f.rate, 0)), 2) as rate
        from sc, customer_logins cl, tariff_cards tc, tariff_license_fee f
        where cl.customer_id = :customer_id
        and sc.login = cl.login
        and tc.id = sc.tariff_card
        and f.tariff_card(+) = tc.id
        and f.deathday(+) > sysdate
        ''', customer_id=self.id)

        self.next_tc = cursor.fetchall()

        #платежи
        cursor.execute('''select
            p.id,
            to_char(p.payment_date, 'dd.mm.yyyy'),
            t.name,
            decode(p.sign, 1, '+', 0, '-'),
            trunc(xxfnd_currency.rub_amount(p.payment), 2),
            nvl(sc.login, '-'),
            p.description,
            prt.short_name,
            to_char(p.insert_time, 'dd.mm.yyyy hh24:mi:ss')
        from
          payments p,
          payment_types t,
          parties prt,
          service_contracts sc
        where p.customer_id = :customer_id
          and t.id = p.payment_type_id
          and prt.id(+) = p.operator_id
          and sc.id(+) = p.service_contract
        order by p.insert_time desc, p.id
        ''', customer_id=self.id)

        self.payments = cursor.fetchall()

        #параметры
        cursor.execute('''select v.id, p.name, v.value
        from party_param_vals v, party_params p
        where v.party_id = :customer_id
        and p.id = v.party_param_id
        ''', customer_id=self.id)

        self.params = cursor.fetchall()

        #аренды
        cursor.execute('''select
          c.contract_number,
          c.contract_date,
          r.start_date,
          r.service_name,
          trunc(xxfnd_currency.rub_amount(rf.rate), 2) as rate,
          r.service_quantity,
          cl.login,
          r.pay_max_num,
          nvl(to_char(r.period), 'месяц') as period
        from
          xxbl_customer_logins cl,
          xxrent_rents r,
          rent_contracts c,
          tariff_amount_fee f,
          rates_amount_fee rf
        where cl.customer_id = :customer_id
        and r.login_id = cl.login_id
        and c.id = r.rent_contract_id
        and f.class = r.service_name
        and f.deathday > sysdate
        and rf.tariff_id = f.id
        ''', customer_id=self.id)

        self.rents = cursor.fetchall()

        #разовые услуги
        cursor.execute('''select
          cl.customer_id,
          s.id,
          s.login,
          s.begin_time,
          s.q1 as service_name,
          s.ai1 as quantity,
          s.id
        from seances s, customer_logins cl
        where cl.customer_id = :customer_id
            and s.login = cl.login
          and s.hname = 'onetime_service'
        ''', customer_id=self.id)

        self.one_time_seances = cursor.fetchall()
    
class PartyParam():
    def __init__(self, id):
        self.id = id
        cursor.execute('''select v.party_id, v.party_param_id, v.value, p.name
        from party_param_vals v, party_params p
        where v.id = :id
        and p.id = v.party_param_id
        ''', id=id)
        
        row = cursor.fetchone()
        self.party_id = row[0]
        self.party_param_id = row[1]
        self.value = row[2]
        self.name = row[3]
        
    def update(self, value):
        cursor.execute('''update party_param_vals v
        set v.value = :value
        where v.party_id = :customer_id
        and v.party_param_id = :param_id
        ''', customer_id=self.party_id, param_id=self.party_param_id, value=value)
        
        db_conn.commit()
        
    @staticmethod
    def add(party_id, param_id, value):
        cursor.execute('''insert into party_param_vals(party_id, party_param_id, value)
        values(:party_id, :party_param_id, :value)
        ''', party_id=party_id, party_param_id=param_id, value=value)
        
        db_conn.commit()
        
    def delete(self):
        cursor.execute('''delete party_param_vals v
        where v.id = :id
        ''', id=self.id)
        
        db_conn.commit()
        
class Payment():
    @staticmethod
    def add(customer_id, service_contract, payment_date, payment_type_id, payment_amount, description, sign, create_access):
        cursor.callproc('infonext.grad_admin.add_payment',
        keywordParameters={'i_customer_id': customer_id,
        'i_service_contract': service_contract,
        'i_payment_date': payment_date,
        'i_payment_type_id': payment_type_id,
        'i_payment_amount': payment_amount,
        'i_operator_id': current_user.customer_id,
        'i_description': description,
        'i_sign': sign,
        'i_create_access': create_access})
        
        db_conn.commit()