from gradadmin import app, db_conn, db_cursor as cursor
from flask import render_template, g, url_for, redirect, flash
from .models import *
from .forms import *
from flask_login import login_user, logout_user, current_user, login_required

@app.before_request
def before_request():
    g.tnsentry = db_conn.tnsentry
    g.menu = [MenuItem(text='Перенос платежей', href=url_for('move_payment'))]
    g.search_form = SearchForm()
    
    
@app.route('/login', methods=['GET', 'POST'])
def login():
    print(dir(current_user))
    for r in dir(current_user):
        print(r, getattr(current_user, r))
    
    
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User(login=form.username.data)
        if user is not None:
            if user.check_password(form.password.data):
                if user.party_type == 0:
                    flash('Недостаточно прав')
                    return redirect(url_for('login'))
                else:
                    login_user(user, remember=form.remember_me.data)
                    return redirect(url_for('index'))
            else:
                flash('Неверный логин или пароль')
                return redirect(url_for('login'))
        
    return render_template('login.html', title='Sign In', form=form)

    
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

    
@app.route("/")
@login_required
def index():
    return render_template('index.html')


@app.route("/tariffs")
@login_required
def tariffs():
    return render_template("tariffs.html")

    
@app.route("/cust_info/<customer_id>")
@login_required
def cust_info(customer_id):
    customer = Customer(id=customer_id)
    
    return render_template("cust_info.html", customer=customer)

    
@app.route('/search', methods=['POST'])
def search():
    if not g.search_form.validate_on_submit():
        return redirect(url_for('index'))
    return redirect(url_for('search_results', query=g.search_form.search.data))


@app.route('/search_results/<query>')
@login_required
def search_results(query):
    cursor.execute('''select cl.login, cl.customer_id
    from customer_logins cl
    where upper(cl.login) like upper(:query)||'%'
    order by cl.login
    ''', query=query)
    
    results = cursor.fetchall()
    
    return render_template('search_results.html',
                           query=query,
                           results=results)


@app.route("/edit_param/<param_val_id>", methods=['GET', 'POST'])
@login_required
def edit_param(param_val_id):
    form = EditParam()
    pp = PartyParam(param_val_id)
    if form.validate_on_submit():
        pp.update(value=form.param_value.data)
    
        flash('Ваши изменения сохранены.')
        return redirect(url_for('cust_info', customer_id=pp.party_id))
    else:
        form.param_value.data = pp.value
        
    return render_template('edit_param.html', form=form, pp=pp)
    
    
@app.route("/add_param/<customer_id>", methods=['GET', 'POST'])
@login_required
def add_param(customer_id):
    form = AddParam(customer_id)
    if form.validate_on_submit():
        PartyParam.add(party_id=customer_id, param_id=form.param_id.data, value=form.param_value.data)
    
        flash('Ваши изменения сохранены.')
        return redirect(url_for('cust_info', customer_id=customer_id))
        
    return render_template('add_param.html', form=form)
    
    
@app.route("/delete_param/<param_val_id>", methods=['GET'])
@login_required
def delete_param(param_val_id):
    pp = PartyParam(param_val_id)
    pp.delete()
    
    flash('Ваши изменения сохранены.')
    return redirect(url_for('cust_info', customer_id=pp.party_id))
    
    
@app.route("/add_payment/<customer_id>", methods=['GET', 'POST'])
@login_required
def add_payment(customer_id):
    form = AddPayment(customer_id)
    if form.validate_on_submit():
        if app.debug:
            print('add_payment validate_on_submit')
            for f in form:
                print(f.name, f.data)
            
        Payment.add(customer_id=form.customer_id, service_contract=form.sc_id.data,
            payment_date=form.payment_date.data, payment_type_id=form.payment_type_id.data,
            payment_amount=form.amount.data, description=form.description.data,
            sign=int(form.debit.data), create_access=int(form.create_access.data))
            
        flash('Платеж добавлен.')
        return redirect(url_for('cust_info', customer_id=customer_id))
        
    return render_template('add_payment.html', form=form)
    
    
@app.route("/set_next_tc/<customer_id>/<login>", methods=['GET', 'POST'])
@login_required
def set_next_tc(customer_id, login):
    form = SetNextTc(customer_id, login)
    if form.validate_on_submit():
        print('set_next_tc validate_on_submit')
        for f in form:
            print(f.name, f.data)
        
        flash('Ваши изменения сохранены.')
        return redirect(url_for('cust_info', customer_id=customer_id))
        
    return render_template('set_next_tc.html', form=form)
    
@app.route("/add_rent/<customer_id>", methods=['GET', 'POST'])
@login_required
def add_rent(customer_id):
    form = AddRent(customer_id)
    #for field in form:
    #    print(field)
    if form.validate_on_submit():
        print('add_rent validate_on_submit')
        for f in form:
            print(f.name, f.data)
        
        flash('Ваши изменения сохранены.')
        return redirect(url_for('cust_info', customer_id=customer_id))
        
    return render_template('add_rent.html', form=form)

    
@app.route("/writeoff_service/<customer_id>", methods=['GET', 'POST'])
@login_required
def writeoff_service(customer_id):
    form = WriteoffService(customer_id)
    if form.validate_on_submit():
        print('writeoff_ot_service validate_on_submit')
        for f in form:
            print(f.name, f.data)
        
        flash('Ваши изменения сохранены.')
        return redirect(url_for('cust_info', customer_id=customer_id))
        
    return render_template('writeoff_service.html', form=form)
    
@app.route("/delete_writeoff/<customer_id>/<seance_id>", methods=['GET'])
@login_required
def delete_writeoff(customer_id, seance_id):
    print('delete_writeoff', seance_id)
    
    flash('Ваши изменения сохранены.')
    return redirect(url_for('cust_info', customer_id=customer_id))
    
    
@app.route("/edit_sc/<customer_id>/<sc_id>", methods=['GET', 'POST'])
@login_required
def edit_sc(customer_id, sc_id):
    form = EditSc(customer_id, sc_id)
    if form.validate_on_submit():
        print('edit_sc validate_on_submit')
        for f in form:
            print(f.name, f.data)
        
        flash('Ваши изменения сохранены.')
        #return redirect(url_for('cust_info', customer_id=customer_id))
    else:
        form.new_control_mode.data = form.control_mode
        form.new_ip4pool_location_id.data = form.ip4pool_location_id
        
    return render_template('edit_sc.html', form=form)
    
    
@app.route("/add_sc/<customer_id>", methods=['GET', 'POST'])
@login_required
def add_sc(customer_id):
    form = AddSc(customer_id)
    if form.validate_on_submit():
        print('add_sc validate_on_submit')
        for f in form:
            print(f.name, f.data)
        
        flash('Ваши изменения сохранены.')
        return redirect(url_for('cust_info', customer_id=customer_id))
        
    return render_template('add_sc.html', form=form)
    
@app.route("/move_payment", methods=['GET', 'POST'])
@login_required
def move_payment():
    form = MovePayment()
    if form.validate_on_submit():
        print('add_sc validate_on_submit')
        for f in form:
            print(f.name, f.data)
        
        flash('Ваши изменения сохранены.')
        return redirect(url_for('index'))
        
    return render_template('move_payment.html', form=form)
    
    
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

    
@app.errorhandler(500)
def internal_error(error):
    db_conn.rollback()
    return render_template('500.html'), 500