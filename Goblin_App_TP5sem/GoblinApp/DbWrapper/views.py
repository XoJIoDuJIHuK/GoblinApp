import json
import hashlib
import os
import zipfile

from .import_export import Exporter, Importer
from django.shortcuts import render, redirect
from django.http import HttpResponse
from . import db_controller as dbc
import datetime
from .db_controller import User, DebtTransaction, DisbalanceTransaction, DebtorEntry

password_salt = 'Qwerty12345'
db_controller = dbc.DbController()
exporter = Exporter()
importer = Importer()

current_user = {
    'status': 'guest',
    'user': None
}


def is_authorized():
    return current_user['status'] != 'guest'


def is_admin(user: User = None):
    return is_authorized() and 'admin' in list(map(lambda x: x.name, current_user['user'].roles
        if not user else user.roles))


debtors = db_controller.get_debtors()
roles = db_controller.get_roles()
users = db_controller.get_users(roles) if is_authorized() else []

db_storage = {
    'users': users,
    'debtors': debtors,
    'roles': roles,
    'debt_transactions': db_controller.get_debt_transactions(debtors, roles),
    'disbalance_transactions': db_controller.get_disbalance_transactions(users=users,
                                                                         user=current_user['user'])
    if is_authorized() else []
}


def get_admin_information():
    if is_admin():
        return {
            'all_other_usernames': [x.name for x in list(filter(
                lambda x: x.id != current_user['user'].id, db_storage['users']))],
        }
    else:
        return None


def get_debtors(request):
    return HttpResponse(json.dumps(list(map(lambda x: {'id': x.id, 'name': x.name}, db_storage['debtors']))))


def get_debt_transactions(request):
    def has_neccessary_role(transaction: DebtTransaction):
        if is_admin():
            return True
        if is_authorized():
            for role in current_user['user'].roles:
                if role in transaction.restrictions:
                    return True
        return len(transaction.restrictions) == 0

    prefiltered_transactions = list(filter(has_neccessary_role, db_storage['debt_transactions']))

    def transactions_filter(transaction: DebtTransaction):

        debtor = request.POST.get('filter_debtor')
        lender = request.POST.get('filter_lender')
        return (debtor == '--' or debtor in list(map(lambda x: x.debtor.name, transaction.debtors_entries))) \
            and (lender == '--' or lender == transaction.lender.name)

    data = {
        'debt_transactions': prefiltered_transactions,
        'debtors': db_storage['debtors'],
        'initial_lender': '--',
        'initial_debtor': '--',
        'pagename': 'Долги',
    }
    if request.method == 'POST':
        data['initial_debtor'] = request.POST.get('filter_debtor')
        data['initial_lender'] = request.POST.get('filter_lender')
        data['debt_transactions'] = list(filter(transactions_filter, prefiltered_transactions))
    return render(request, 'DbWrapper/base.html', context={
        'data': data,
        'current_user': current_user,
        'required_template': 'debt transactions',
        'admin_information': get_admin_information()
    })


def change_debt_transactions(request):
    if request.method in ['PUT', 'POST'] and is_authorized():
        body = json.loads(request.body)
        lender_id = int(body['transaction_lender'])
        filtered_debtors = list(filter(lambda x: x.id == lender_id, db_storage['debtors']))
        if len(filtered_debtors) != 1:
            return HttpResponse(status=404)
        if filtered_debtors[0].user_id != current_user['user'].id and current_user['status'] != 'admin':
            return HttpResponse(status=401)
        entries = [DebtorEntry(list(filter(lambda x: int(entry['id']) == x.id,
                                           db_storage['debtors']))[0],
                               float(entry['multiplier']),
                               'Y' if bool(entry['fulfilled']) else 'N')
                   for entry in body['transaction_debtors_entries']]
        transaction_id = body['transaction_id']
        transaction_name = body['transaction_name'][:49]
        transaction_amount = float(body['transaction_amount'])
        transaction_lender = filtered_debtors[0]
        transaction_description = body['transaction_description'][:255]
        transaction_date = body['transaction_date']
        if not date_is_valid(transaction_date):
            return HttpResponse(status=400)
        try:
            transaction_restrictions = list(set(map(lambda x: list(filter(lambda y: y.name == x,
                                                                          db_storage['roles']))[0],
                                                    body['transaction_restrictions'])))
        except:
            return HttpResponse(400)
        if request.method == 'PUT':
            transaction_id = (db_controller.add_debt_transaction(
                name=transaction_name,
                amount=transaction_amount,
                lender=transaction_lender,
                date=transaction_date,
                description=transaction_description,
                restrictions=transaction_restrictions))
            db_controller.add_disbalance_transaction(name='[auto] ' + transaction_name,
                                                     amount=transaction_amount * -1,
                                                     reason='Одолжение',
                                                     date=transaction_date,
                                                     user=current_user['user'])
            db_storage['disbalance_transactions'] = db_controller.get_disbalance_transactions(db_storage['users'])
        if request.method == 'POST':
            filtered_transactions = list(filter(lambda x: x.id == int(transaction_id),
                                                db_storage['debt_transactions']))
            if len(filtered_transactions) != 1:
                return HttpResponse(status=400)
            transaction = filtered_transactions[0]
            db_controller.update_debt_transaction(transaction=transaction,
                                                  name=transaction_name,
                                                  amount=transaction_amount,
                                                  lender=transaction_lender,
                                                  date=transaction_date,
                                                  description=transaction_description)
            transaction_id = transaction.id
            for entry in transaction.debtors_entries:
                db_controller.delete_debtor_entry(transaction=transaction,
                                                  debtor=entry.debtor)
            for role in transaction.restrictions:
                db_controller.delete_transaction_restriction(transaction=transaction,
                                                             role=role)
            db_controller.add_transaction_restrictions(transaction_id=transaction_id,
                                                       roles=transaction_restrictions)
        sum_multiplier = sum(map(lambda x: x.multiplier, entries))
        for entry in entries:
            db_controller.add_debtor_entry_by_transaction_id(transaction_id=transaction_id,
                                                             debtor_id=entry.debtor.id,
                                                             multiplier=entry.multiplier,
                                                             amount=transaction_amount * entry.multiplier /
                                                                    sum_multiplier,
                                                             fulfilled=entry.fulfilled)
        db_storage['debt_transactions'] = db_controller.get_debt_transactions(db_storage['debtors'],
                                                                              db_storage['roles'])
        return HttpResponse(status=200)
    return redirect('get_debt_transactions')


def delete_debt_transaction(request):
    if request.method == 'DELETE' and is_authorized():
        body = json.loads(request.body)
        transaction_id = int(body['transaction_id'])
        filtered_transactions = list(filter(lambda x: x.id == transaction_id, db_storage['debt_transactions']))
        if len(filtered_transactions) != 1:
            return HttpResponse(status=404)
        if is_admin() or filtered_transactions[0].lender.user_id == current_user['user'].id:
            for entry in filtered_transactions[0].debtors_entries:
                db_controller.delete_debtor_entry(filtered_transactions[0], entry.debtor)
            db_controller.delete_debt_transaction(filtered_transactions[0])
        else:
            return HttpResponse(status=401)
        db_storage['debt_transactions'] = db_controller.get_debt_transactions(db_storage['debtors'],
                                                                              db_storage['roles'])
        return redirect('get_debt_transactions')
    else:
        return HttpResponse(status=400)


def get_disbalance_transactions(request):
    if not is_authorized():
        return redirect('get_debt_transactions')
    transaction_filter = {
        'mode': 'Доходы и расходы',
        'reason': '--',
        'date': '',
    }

    def filter_transaction(x):
        ownership_check = current_user['user'].id == x.user.id
        mode_check = True if transaction_filter['mode'] == 'Доходы и расходы' \
            else x.amount > 0 if transaction_filter['mode'] == 'Доходы' else x.amount < 0
        reason_check = True if transaction_filter['reason'] == '--' else x.reason == transaction_filter['reason']
        date_check = True if transaction_filter['date'] == '' else x.date == transaction_filter['date']
        return ownership_check and mode_check and reason_check and date_check

    if request.method == 'POST':
        str_date = request.POST.get('filter-date')
        if len(str_date) != 0 and not date_is_valid(str_date):
            return HttpResponse(status=400)
        mode = request.POST.get('filter-mode')
        reason = request.POST.get('filter-reason')
        transaction_filter['mode'] = mode
        transaction_filter['reason'] = reason
        transaction_filter['date'] = str_date
    filtered_transactions = list(filter(filter_transaction, db_storage['disbalance_transactions']))
    transaction_filter['reasons'] = list(set(map(lambda x: x.reason, db_storage['disbalance_transactions'])))
    return render(request, 'DbWrapper/base.html', context={
        'data': {
            'disbalance_transactions': filtered_transactions,
            'pagename': transaction_filter['mode'],
        },
        'required_template': 'disbalance transactions',
        'current_user': current_user,
        'filter': transaction_filter,
        'admin_information': get_admin_information()
    })


def change_disbalance_transaction(request):
    if not is_authorized():
        return HttpResponse(status=403)
    if request.method in ['PUT', 'POST']:
        body = json.loads(request.body)
        if not date_is_valid(body['date']):
            return HttpResponse(status=400)
        name = body['name'][:49]
        amount = float(body['amount'])
        if amount == 0:
            return HttpResponse("Количество не может равняться нулю", status=400)
        reason = body['reason'][:49]
        date = body['date']
    else:
        return HttpResponse(status=400)
    if request.method == 'PUT':
        transaction_id = db_controller.add_disbalance_transaction(name=name,
                                                                  amount=amount,
                                                                  reason=reason,
                                                                  date=date,
                                                                  user=current_user['user'])
    if request.method == 'POST':
        transaction_id = int(body['id'])
        filtered_transactions = list(filter(lambda x: x.id == transaction_id, db_storage['disbalance_transactions']))
        if len(filtered_transactions) != 1:
            return HttpResponse(status=404)
        if is_admin() or filtered_transactions[0].user.id == current_user['user'].id:
            db_controller.update_disbalance_transaction(transaction_id=transaction_id,
                                                        name=name,
                                                        amount=amount,
                                                        reason=reason,
                                                        date=date)
        else:
            return HttpResponse(status=401)
    db_storage['disbalance_transactions'] = (db_controller.
                                             get_disbalance_transactions(users=db_storage['users'],
                                                                         user=current_user['user']))
    return HttpResponse(status=200)


def delete_disbalance_transaction(request):
    if not is_authorized():
        return HttpResponse(status=403)
    body = json.loads(request.body)
    filtered_transactions = list(filter(lambda x: x.id == int(body['id']), db_storage['disbalance_transactions']))
    if len(filtered_transactions) != 1:
        return HttpResponse(status=404)
    if not is_admin() and filtered_transactions[0].user.id != current_user['user'].id:
        return HttpResponse(status=401)
    db_controller.delete_disbalance_transaction(filtered_transactions[0])
    db_storage['disbalance_transactions'] = db_controller.get_disbalance_transactions(db_storage['users'])
    return redirect('disbalance_transactions')


def serialize_role_array(array):
    return json.dumps([x.name for x in list(filter(lambda x: x.name != 'admin', array))])


def get_user_roles(request):
    if not is_authorized():
        return HttpResponse(status=403)
    if request.method == 'GET':
        if 'username' in request.GET:
            if not is_admin():
                return HttpResponse("You are not admin to request others' roles", status=403)
            found_users = list(filter(lambda x: x.name == request.GET['username'], db_storage['users']))
            if len(found_users) != 1:
                return HttpResponse("User with specified name is not found", status=400)
            return HttpResponse(serialize_role_array(found_users[0].roles))
        else:
            return HttpResponse(serialize_role_array(current_user['user'].roles))
    else:
        return HttpResponse(status=400)


def get_all_roles(request):
    if not is_authorized():
        return HttpResponse(status=401)
    if request.method == 'GET':
        return HttpResponse(json.dumps([x.name for x in list(filter(
            lambda x: x.name != 'admin', db_storage['roles']))]))
    else:
        return HttpResponse(status=400)


def save_user_roles(request):
    def get_role_by_name(name):
        filtered_roles = list(filter(lambda x: x.name == name, db_storage['roles']))
        if len(filtered_roles) == 1:
            return filtered_roles[0]
        return None

    def get_user_by_name(name):
        filtered_users = list(filter(lambda x: x.name == name, db_storage['users']))
        if len(filtered_users) == 1:
            return filtered_users[0]
        else:
            raise NameError('user not found')

    if request.method == 'POST' and is_authorized():
        body = json.loads(request.body)
        try:
            user_to_save = get_user_by_name(body['username'])
            if user_to_save.name != current_user['user'].name and not is_admin():
                return HttpResponse(status=403)
        except NameError as e:
            return HttpResponse(e, status=404)
        roles_to_save = list(map(get_role_by_name, body['roles']))
        for role in user_to_save.roles:
            if role not in roles_to_save and role.name != 'admin':
                db_controller.delete_user_role(user_to_save.id, role)
        for role in roles_to_save:
            if role not in user_to_save.roles:
                db_controller.add_user_role(user_to_save.id, role)
        current_user['user'].roles = db_controller.get_user_roles(current_user['user'].id, db_storage['roles'])
        return HttpResponse(status=200)
    else:
        return HttpResponse(status=403)


def create_new_role(request):
    if not is_admin():
        return HttpResponse(status=403)
    if request.method != 'PUT':
        return HttpResponse(status=400)
    body = json.loads(request.body)
    role_name = body['role-name']
    if role_name == 'admin':
        return HttpResponse(status=400)
    if role_name not in list(map(lambda x: x.name, db_storage['roles'])):
        db_controller.add_role(role_name)
        db_storage['roles'] = db_controller.get_roles()
        return HttpResponse(status=200)
    else:
        return HttpResponse(status=409)


def delete_role(request):
    if not is_admin():
        return HttpResponse(status=403)
    if request.method != 'DELETE':
        return HttpResponse(status=400)
    body = json.loads(request.body)
    role_name = body['role-name']
    if role_name == 'admin':
        return HttpResponse(status=418)
    filtered_roles = list(filter(lambda x: x.name == role_name, db_storage['roles']))
    if len(filtered_roles) == 1:
        db_controller.delete_role(filtered_roles[0].id)
        db_storage['roles'] = db_controller.get_roles()
        return HttpResponse(status=200)
    else:
        return HttpResponse(status=409)


def sign(request):
    if is_authorized() and request.method not in ['POST', 'PUT']:
        return HttpResponse(status=404)
    body = json.loads(request.body)
    name = body['name'][:49]
    if name == 'Гость':
        return HttpResponse(status=418)
    password = body['password'][:255]
    password_hash = hashlib.sha256(str(password + password_salt).encode()).hexdigest()
    success = (request.method == 'POST' and db_controller.is_login_correct(name, password_hash)) or \
              (request.method == 'PUT' and db_controller.add_user(name, password_hash, []))
    if success:
        db_controller.use_user()
        db_storage['users'] = db_controller.get_users(db_storage['roles'])
        db_storage['debtors'] = db_controller.get_debtors()
        current_user['status'] = 'user'
        current_user['user'] = list(filter(lambda x: x.name == name, db_storage['users']))[0]
        db_storage['disbalance_transactions'] = (
            db_controller.get_disbalance_transactions(users=db_storage['users'],
                                                      user=current_user['user']))
        if is_admin():
            current_user['status'] = 'admin'
            db_controller.use_admin()
        return HttpResponse(status=200)
    else:
        return HttpResponse(status=400)


def date_is_valid(string_date: str) -> bool:
    try:
        datetime.datetime.strptime(string_date, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def summary_debts(request):
    def filter_by_date(entity: DebtTransaction | DisbalanceTransaction):
        filter_start_date = debts_filter['start_date']
        filter_end_date = debts_filter['end_date']
        if filter_start_date == '' and filter_end_date == '':
            return True
        if filter_start_date == '':
            return filter_end_date > entity.date
        if filter_end_date == '':
            return filter_start_date < entity.date
        return filter_start_date < entity.date < filter_end_date

    if not is_authorized() or request.method not in ['GET', 'POST']:
        return redirect('get_debt_transactions')
    debts_filter = {
        'start_date': '',
        'end_date': '',
    }
    filtered_debtors = list(filter(lambda x: x.user_id == current_user['user'].id, db_storage['debtors']))
    if len(filtered_debtors) != 1:
        return HttpResponse(status=500)
    if request.method == 'POST' and request.POST.get('submit'):
        string_start_date = request.POST.get('start-date')
        string_end_date = request.POST.get('end-date')
        if string_start_date != '' and not date_is_valid(string_start_date) or \
                string_end_date != '' and not date_is_valid(string_end_date):
            return HttpResponse(status=400)
        debts_filter['start_date'] = string_start_date
        debts_filter['end_date'] = string_end_date
    debts_data = {
        'total_debt': db_controller.get_total_debt(filtered_debtors[0], start_date=debts_filter['start_date'],
                                                   end_date=debts_filter['end_date']),
        'total_balance': db_controller.get_total_balance(filtered_debtors[0], start_date=debts_filter['start_date'],
                                                         end_date=debts_filter['end_date']),
        'self_debts': db_controller.get_p2p_debts_by_person_id(True, filtered_debtors[0], db_storage['debtors'],
                                                               start_date=debts_filter['start_date'],
                                                               end_date=debts_filter['end_date']),
        'self_lends': db_controller.get_p2p_debts_by_person_id(False, filtered_debtors[0], db_storage['debtors'],
                                                               start_date=debts_filter['start_date'],
                                                               end_date=debts_filter['end_date']),
    }
    return render(request, 'DbWrapper/base.html', context={
        'data': {
            'pagename': 'Сводка',
        },
        'required_template': 'summary',
        'current_user': current_user,
        'filter': debts_filter,
        'debts_data': debts_data,
        'disbalance_transactions': list(filter(lambda x: filter_by_date(x) and
                                                         x.user.id == current_user['user'].id,
                                               db_storage['disbalance_transactions'])),
        'admin_information': get_admin_information()
    })


def admin_page(request):
    if not is_admin():
        return redirect('get_debt_transactions')
    if request.method == 'DELETE':
        body = json.loads(request.body)
        if 'userId' in body:
            user_id = int(body['userId'])
            if user_id == current_user['user'].id:
                return HttpResponse(status=401)
            filtered_users = list(filter(lambda x: x.id == user_id, db_storage['users']))
            if len(filtered_users) != 1:
                return HttpResponse(status=400)
            db_controller.delete_user(user_id)
        elif 'debtorId' in body:
            debtor_id = int(body['debtorId'])
            filtered_debtors = list(filter(lambda x: x.id == debtor_id, db_storage['debtors']))
            if len(filtered_debtors) != 1:
                return HttpResponse(status=400)
            user_id = filtered_debtors[0].user_id
            if user_id is not None:
                filtered_users = list(filter(lambda x: x.id == user_id, db_storage['users']))
                if len(filtered_users) != 1:
                    return HttpResponse("Не найден нужный пользователь", status=500)
                db_controller.delete_user(user_id)
                db_storage['users'] = db_controller.get_users(db_storage['roles'])
            db_controller.delete_debtor(debtor_id)
            db_storage['debtors'] = db_controller.get_debtors()
        else:
            return HttpResponse(status=400)

    elif request.method == 'PUT':
        body = json.loads(request.body)
        print(body)
        if 'debtorName' in body and 'userId' in body:
            debtor_name = body['debtorName'][:49]
            user_id = int(body['userId'])
            if user_id == 0:
                user_id = None
            filtered_debtors = list(filter(lambda x: user_id == x.user_id, db_storage['debtors']))
            if len(filtered_debtors) > 0:
                return HttpResponse("Пользователь уже занят", status=400)
            filtered_debtors = list(filter(lambda x: x.name == debtor_name, db_storage['debtors']))
            if len(filtered_debtors) > 0:
                return HttpResponse("Имя занято", status=400)
            db_controller.add_debtor(name=debtor_name, user_id=user_id)
            db_storage['debtors'] = db_controller.get_debtors()
        else:
            return HttpResponse(status=400)
    elif request.method == 'POST':
        body = json.loads(request.body)
        if 'calculateAllDebts' in body and body['calculateAllDebts']:
            for i in range(len(db_storage['debtors'])):
                lender = db_storage['debtors'][i]
                for j in range(i + 1, len(db_storage['debtors'])):
                    debtor = db_storage['debtors'][j]
                    db_controller.calculate_p2p_debts(lender, debtor)
        else:
            return HttpResponse(status=418)

    return render(request, 'DbWrapper/base.html', context={
        'data': {
            'pagename': 'Админка',
        },
        'required_template': 'admin',
        'current_user': current_user,
        'debtors': [{'id': x.id, 'name': x.name, 'user_id': x.user_id} for x in db_storage['debtors']],
        'users': [{'id': x.id, 'name': x.name} for x in db_storage['users']],
        'admin_information': get_admin_information()
    })


def export(request):
    if not is_admin() or request.method != 'POST':
        return HttpResponse(status=403)
    files = [exporter.export_roles(db_storage['roles']),
             exporter.export_users(db_controller.get_users_for_export(roles=db_storage['roles'])),
             exporter.export_debtors(db_storage['debtors']),
             exporter.export_debt_transactions(db_storage['debt_transactions']),
             exporter.export_disbalance_transactions(db_storage['disbalance_transactions'])]
    with zipfile.ZipFile('backup.zip', 'w') as archive:
        for file in files:
            archive.write(file)
    return HttpResponse(status=200)


def import_data(request):
    if not is_admin() or request.method != 'POST':
        return HttpResponse(status=403)
    if 'backup.zip' not in os.listdir():
        return HttpResponse(status=404)
    with zipfile.ZipFile('backup.zip', 'r') as archive:
        archive.extractall()
    db_controller.wipe_database()
    importer.import_roles(db_controller)
    db_storage['roles'] = db_controller.get_roles()
    importer.import_debtors(db_controller)
    importer.import_users(db_controller, db_storage)
    db_storage['debtors'] = db_controller.get_debtors()
    db_storage['users'] = db_controller.get_users(db_storage['roles'])
    importer.import_debt_transactions(db_controller, db_storage)
    db_storage['debt_transactions'] = db_controller.get_debt_transactions(db_storage['debtors'],
                                                                          db_storage['roles'])
    importer.import_disbalance_transactions(db_controller, db_storage)
    db_storage['disbalance_transactions'] = db_controller.get_disbalance_transactions(db_storage['users'])
    return HttpResponse(status=200)


def signout(request):
    current_user['status'] = 'guest'
    current_user['user'] = None
    db_storage['disbalance_transactions'] = []
    db_storage['users'] = []
    db_controller.use_guest()
    return redirect('get_debt_transactions')

# def insert_users(request):
#     def generate_unique_strings(length, count):
#         unique_strings = set()
#
#         while len(unique_strings) < count:
#             random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
#             unique_strings.add(random_string)
#
#         return unique_strings
#
#     unique_strings = generate_unique_strings(50, 10000)
#     password_hash = hashlib.sha256(str('1234' + password_salt).encode()).hexdigest()
#     for name in unique_strings:
#         if not db_controller.add_user(name, password_hash, []):
#             return HttpResponse(status=503)
#     return HttpResponse(status=200)
