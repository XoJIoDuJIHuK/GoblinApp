import oracledb
from django.utils.datetime_safe import datetime

no_such_identifier_text = 'PLS-00201'


class Role:
    def __init__(self, role_id: int, name: str):
        self.id: int = role_id
        self.name: str = name

    def __str__(self):
        return f"Role id:{self.id} name:{self.name}"


class User:
    def __init__(self, uid: int, name: str, roles: [Role]):
        self.id: int = uid
        self.name: str = name
        self.roles: [Role] = roles

    def __str__(self):
        return f'User id:{self.id} name:{self.name} roles:{self.roles}'


class Debtor:
    def __init__(self, debtor_id: int, name: str, user_id: int):
        self.id: int = debtor_id
        self.name: str = name
        self.user_id: int = user_id

    def __str__(self):
        return f"Debtor id:{self.id} name:{self.name} user id:{self.user_id}"


class DebtorEntry:
    def __init__(self, debtor: Debtor, multiplier: float, fulfilled: str):
        self.debtor: Debtor = debtor
        self.multiplier: float = multiplier
        self.fulfilled: bool = fulfilled == 'Y'

    def __str__(self):
        return f"D: {self.debtor} M: {self.multiplier} F: {self.fulfilled}"


class DebtTransaction:
    def __init__(self, transaction_id: int, name: str, amount: int, lender: Debtor, date: str,
                 description: str, debtors_entries: [DebtorEntry], restrictions: [Role]):
        self.id: int = transaction_id
        self.name: str = name
        self.amount: float = round(float(amount) / 100, 2)
        self.lender: Debtor = lender
        self.date: str = date
        self.description: str = description
        self.debtors_entries: [DebtorEntry] = debtors_entries
        self.restrictions: [Role] = restrictions

    def __setitem__(self, key, value):
        self.key = value

    def get_debtors_entries(self):
        return self.debtors_entries


class DisbalanceTransaction:
    def __init__(self, transaction_id: int, name: str, amount: int, reason: str, date: str,
                 user: User):
        self.id: int = transaction_id
        self.name: str = name
        self.amount: float = round(float(amount) / 100, 2)
        self.reason: str = reason
        self.date: date = date
        self.user: User = user

    def __str__(self):
        return (f"Disbalance transaction id:{self.id} name:{self.name} amount:{self.amount} " +
                f"reason id:{self.reason} date:{self.date} user_id:{self.user.id}")


class DbController:
    def __init__(self):
        self.admin_connection = oracledb.connect(
            user="GOBLIN_ADMIN",
            password="Qwerty12345",
            dsn="oracledb:1521/GOBLIN_APP_PDB.mshome.net")
        self.guest_connection = oracledb.connect(
            user="GUEST",
            password="guest_password",
            dsn="oracledb:1521/GOBLIN_APP_PDB.mshome.net")
        self.user_connection = oracledb.connect(
            user="COMMON_USER",
            password="user_password",
            dsn="oracledb:1521/GOBLIN_APP_PDB.mshome.net")
        self.cursor = self.guest_connection.cursor()
        self.cursor.execute('alter session set current_schema = GOBLIN_ADMIN')

    def use_guest(self):
        self.cursor = self.guest_connection.cursor()
        self.cursor.execute('alter session set current_schema=GOBLIN_ADMIN')

    def use_user(self):
        self.cursor = self.user_connection.cursor()
        self.cursor.execute('alter session set current_schema=GOBLIN_ADMIN')

    def use_admin(self):
        self.cursor = self.admin_connection.cursor()
        self.cursor.execute('alter session set current_schema=GOBLIN_ADMIN')

    def get_roles(self):
        # print('get roles')
        return [Role(*role) for role in (self.cursor.callproc('GET_ROLES',
                                                              [self.cursor.var(oracledb.CURSOR)])[0].fetchall())]

    def add_role(self, name: str, p_id: int = -1):
        try:
            result = self.cursor.var(oracledb.NUMBER)
            self.cursor.callproc('ADD_ROLE', [p_id, name, result])
            return result.getvalue()
        except Exception as e:
            error, = e.args
            error_code = error.code
            error_message = error.message
            if no_such_identifier_text in error_message:
                print('[ERROR] You have to log in as admin to call ADD_ROLE')
            else:
                print(error_message)
            return -1

    def delete_role(self, role_id: int):
        try:
            self.cursor.callproc('DELETE_ROLE', [role_id])
        except Exception as e:
            error, = e.args
            error_code = error.code
            error_message = error.message
            if no_such_identifier_text in error_message:
                print('[ERROR] You have to log in as admin to call DELETE_ROLE')
            else:
                print(error_message)

    def is_login_correct(self, login: str, password: str):
        result = self.cursor.var(oracledb.NUMBER)
        result.setvalue(0, 1)
        try:
            self.cursor.callproc('IS_LOGIN_CORRECT', [login, password, result])
        except Exception as e:
            error, = e.args
            error_code = error.code
            error_message = error.message
            if no_such_identifier_text in error_message:
                print('How don\'t you have rights to call IS_LOGIN_CORRECT?')
            else:
                print(error_message)
            return False
        return result.getvalue() != -1

    def get_users(self, roles: [Role]) -> [User]:
        # print('get users')
        try:
            user_tuples = (self.cursor.callproc('GET_USERS', [self.cursor.var(oracledb.CURSOR)])[0].
                           fetchall())
            return [User(user[0], user[1], self.get_user_roles(user[0], roles)) for user in user_tuples]
        except Exception as e:
            error, = e.args
            error_code = error.code
            error_message = error.message
            if no_such_identifier_text in error_message:
                print('[ERROR] You have to log in to call GET_USERS')
            else:
                print(error_message)
            return []

    def get_users_for_export(self, roles: [Role]):
        try:
            user_tuples = (self.cursor.callproc('GET_USERS_FOR_EXPORT', [self.cursor.var(oracledb.CURSOR)])[0].
                           fetchall())
            return [{'id': user[0], 'name': user[1], 'password': user[2],
                     'roles': self.get_user_roles(user[0], roles)} for user in user_tuples]
        except Exception as e:
            error, = e.args
            error_code = error.code
            error_message = error.message
            if no_such_identifier_text in error_message:
                print('[ERROR] You have to log in as admin to call GET_USERS_FOR_EXPORT')
            else:
                print(error_message)
            return []

    def add_user(self, name: str, password: str, roles: [Role], p_id: int = -1):
        result = self.cursor.var(oracledb.NUMBER)
        result.setvalue(0, 1)
        self.cursor.callproc('ADD_USER', [p_id, name, password, result])
        for role in roles:
            self.cursor.callproc('ADD_USER_ROLE', [result.getvalue(), role.id])
        return result.getvalue() >= 0

    def delete_user(self, user_id: int):
        try:
            self.cursor.callproc('DELETE_USER', [user_id])
        except Exception as e:
            error, = e.args
            error_code = error.code
            error_message = error.message
            if no_such_identifier_text in error_message:
                print('[ERROR] You have to log in as admin to call DELETE_USER')
            else:
                print(error_message)

    def get_user_roles(self, user_id: int, roles: [Role]) -> [Role]:
        try:
            role_tuples = (self.cursor.callproc('GET_USER_ROLES',
                                                [self.cursor.var(oracledb.CURSOR), user_id])
                           [0].fetchall())
            return [list(filter(lambda x: x.id == role[0], roles))[0] for role in role_tuples]
        except Exception as e:
            error, = e.args
            error_code = error.code
            error_message = error.message
            if no_such_identifier_text in error_message:
                print('[ERROR] You have to log in to call GET_USER_ROLES')
            else:
                print(error_message)
            return []

    def add_user_role(self, user_id: int, role: Role):
        try:
            self.cursor.callproc('ADD_USER_ROLE', [user_id, role.id])
        except Exception as e:
            error, = e.args
            error_code = error.code
            error_message = error.message
            if no_such_identifier_text in error_message:
                print('[ERROR] You have to log in to call ADD_USER_ROLE')
            else:
                print(error_message)

    def delete_user_role(self, user_id: int, role: Role):
        try:
            self.cursor.callproc('DELETE_USER_ROLE', [user_id, role.id])
        except Exception as e:
            error, = e.args
            error_code = error.code
            error_message = error.message
            if no_such_identifier_text in error_message:
                print('[ERROR] You have to log in to call DELETE_USER_ROLE')
            else:
                print(error_message)

    def get_debtors(self):
        return [Debtor(*debtor) for debtor in (
            self.cursor.callproc('GET_DEBTORS', [self.cursor.var(oracledb.CURSOR)])
            [0].fetchall())]

    def add_debtor(self, name: str, user_id: int | None, p_id: int = -1):
        try:
            result = self.cursor.var(oracledb.NUMBER)
            self.cursor.callproc('ADD_DEBTOR', [p_id, name, user_id, result])
            return result.getvalue()
        except Exception as e:
            error, = e.args
            error_code = error.code
            error_message = error.message
            if no_such_identifier_text in error_message:
                print('[ERROR] You have to log in as admin to call ADD_DEBTOR')
            else:
                print(error_message)
            return -1

    def delete_debtor(self, debtor_id: int):
        try:
            self.cursor.callproc('DELETE_DEBTOR', [debtor_id])
        except Exception as e:
            error, = e.args
            error_code = error.code
            error_message = error.message
            if no_such_identifier_text in error_message:
                print('[ERROR] You have to log in as admin to call DELETE_DEBTOR')
            else:
                print(error_message)

    def get_debt_transactions(self, debtors: [Debtor], roles: [Role]):
        transactions = self.cursor.callproc('GET_DEBT_TRANSACTIONS',
                                            [self.cursor.var(oracledb.CURSOR)])[0].fetchall()
        return [DebtTransaction(transaction_id=transaction[0],
                                name=transaction[1],
                                amount=transaction[2],
                                lender=list(filter(lambda x: x.id == transaction[3], debtors))[0],
                                date=f"{str(transaction[4].date().year).rjust(4, '0')}-"
                                     f"{str(transaction[4].date().month).rjust(2, '0')}-"
                                     f"{str(transaction[4].date().day).rjust(2, '0')}",
                                description=transaction[5],
                                debtors_entries=[DebtorEntry(list(filter(lambda x: x.id == entry[0], debtors))[0],
                                                             entry[1], entry[2])
                                                 for entry in
                                                 self.get_debtors_entries_by_transaction_id(transaction[0])],
                                restrictions=[list(filter(lambda x: x.id == role_tuple[0], roles))[0]
                                              for role_tuple in self.get_transaction_restrictions(
                                        transaction[0])])
                for transaction in transactions]

    def add_debt_transaction(self, name: str, amount: float, lender: Debtor, date: str, description: str,
                             restrictions: [Role], p_id: int = -1) -> int:
        try:
            transaction_id = self.cursor.var(oracledb.NUMBER)
            self.cursor.callproc('ADD_DEBT_TRANSACTION',
                                 [p_id, name, int(amount * 100), lender.id,
                                  datetime.strptime(date, '%Y-%m-%d'),
                                  description if description else 'Нет описания', transaction_id])
            try:
                for role in restrictions:
                    self.cursor.callproc('ADD_TRANSACTION_RESTRICTION', [transaction_id, role.id])
            except Exception as e:
                if no_such_identifier_text in e.args[0].message:
                    print('[ERROR] You have to log in to call ADD_TRANSACTION_RESTRICTION')
                else:
                    print(e.args[0].message)
            return transaction_id.getvalue()
        except Exception as e:
            error, = e.args
            error_code = error.code
            error_message = error.message
            if no_such_identifier_text in error_message:
                print('[ERROR] You have to log in to call ADD_DEBT_TRANSACTION')
            else:
                print(error_message)
            return -1

    def update_debt_transaction(self, transaction: DebtTransaction, name: str, amount: float, lender: Debtor,
                                date: str, description: str):
        try:
            self.cursor.callproc('UPDATE_DEBT_TRANSACTION',
                                 [transaction.id, name, int(amount * 100), lender.id,
                                  datetime.strptime(date, '%Y-%m-%d'),
                                  description if description else 'Нет описания'])
        except Exception as e:
            error, = e.args
            error_code = error.code
            error_message = error.message
            if no_such_identifier_text in error_message:
                print('[ERROR] You have to log in to call UPDATE_DEBT_TRANSACTION')
            else:
                print(error_message)

    def delete_debt_transaction(self, transaction: DebtTransaction):
        try:
            self.cursor.callproc('DELETE_DEBT_TRANSACTION', [transaction.id])
        except Exception as e:
            error, = e.args
            error_code = error.code
            error_message = error.message
            if no_such_identifier_text in error_message:
                print('[ERROR] You have to log in to call DELETE_DEBT_TRANSACTION')
            else:
                print(error_message)

    def get_debtors_entries_by_transaction_id(self, transaction_id: int):
        cursor = self.cursor.callproc('GET_DEBTORS_ENTRIES',
                                      [self.cursor.var(oracledb.CURSOR), transaction_id])
        result = cursor[0].fetchall()
        return result

    def add_debtor_entry_by_transaction_id(self, transaction_id: int, debtor_id: int,
                                           multiplier: float, amount: float, fulfilled: bool):
        try:
            self.cursor.callproc('ADD_DEBTOR_ENTRY', [transaction_id, debtor_id, multiplier,
                                                      int(amount * 100), 'Y' if fulfilled else 'N'])
        except Exception as e:
            error, = e.args
            error_code = error.code
            error_message = error.message
            if no_such_identifier_text in error_message:
                print('[ERROR] You have to log in to call ADD_DEBTOR_ENTRY')
            else:
                print(error_message)

    def delete_debtor_entry(self, transaction: DebtTransaction, debtor: Debtor):
        try:
            self.cursor.callproc('DELETE_DEBTOR_ENTRY', [transaction.id, debtor.id])
        except Exception as e:
            error, = e.args
            error_code = error.code
            error_message = error.message
            if no_such_identifier_text in error_message:
                print('[ERROR] You have to log in to call DELETE_DEBTOR_ENTRY')
            else:
                print(error_message)

    def get_transaction_restrictions(self, transaction_id):
        return self.cursor.callproc('GET_TRANSACTION_RESTRICTIONS',
                                    [self.cursor.var(oracledb.CURSOR), transaction_id])[0].fetchall()

    def add_transaction_restrictions(self, transaction_id: int, roles: [Role]):
        try:
            for role in roles:
                self.cursor.callproc('ADD_TRANSACTION_RESTRICTION', [transaction_id, role.id])
        except Exception as e:
            error, = e.args
            error_code = error.code
            error_message = error.message
            if no_such_identifier_text in error_message:
                print('[ERROR] You have to log in to call ADD_TRANSACTION_RESTRICTION')
            else:
                print(error_message)

    def delete_transaction_restriction(self, transaction: DebtTransaction, role: Role):
        try:
            self.cursor.callproc('DELETE_TRANSACTION_RESTRICTION', [transaction.id, role.id])
        except Exception as e:
            error, = e.args
            error_code = error.code
            error_message = error.message
            if no_such_identifier_text in error_message:
                print('[ERROR] You have to log in to call DELETE_TRANSACTION_RESTRICTION')
            else:
                print(error_message)

    def get_disbalance_transactions(self, users: [User], user: User | None = None, date: str | None = None,
                                    mode: int = 0, reason: str | None = None) \
            -> [DisbalanceTransaction]:
        # print('disbalance transactions')
        try:
            transaction_tuples = self.cursor.callproc('GET_DISBALANCE_TRANSACTIONS',
                                                      [self.cursor.var(oracledb.CURSOR),
                                                       user.id if user is not None else None,
                                                       datetime.strptime(date, '%Y-%m-%d') if date else date,
                                                       mode,
                                                       reason])[0].fetchall()
            return [DisbalanceTransaction(transaction[0], transaction[1], transaction[2], transaction[3],
                                          str(transaction[4].date()),
                                          list(filter(lambda x: x.id == transaction[5], users))[0])
                    for transaction in transaction_tuples]
        except Exception as e:
            error, = e.args
            error_code = error.code
            error_message = error.message
            if no_such_identifier_text in error_message:
                print('[ERROR] You have to log in to call GET_DISBALANCE_TRANSACTIONS')
            else:
                print(error_message)
            return []

    def add_disbalance_transaction(self, name: str, amount: float, reason: str, date: str, user: User):
        try:
            self.cursor.callproc('ADD_DISBALANCE_TRANSACTION',
                                 [name, int(amount * 100), reason,
                                  datetime.strptime(date, '%Y-%m-%d'), user.id])
        except Exception as e:
            error, = e.args
            error_code = error.code
            error_message = error.message
            if no_such_identifier_text in error_message:
                print('[ERROR] You have to log in to call ADD_DISBALANCE_TRANSACTION')
            else:
                print(error_message)

    def update_disbalance_transaction(self, transaction_id: int, name: str, amount: float, date: str,
                                      reason: str):
        try:
            self.cursor.callproc('UPDATE_DISBALANCE_TRANSACTION',
                                 [transaction_id, name, int(amount * 100), reason,
                                  datetime.strptime(date, '%Y-%m-%d')])
        except Exception as e:
            error, = e.args
            error_code = error.code
            error_message = error.message
            if no_such_identifier_text in error_message:
                print('[ERROR] You have to log in to call UPDATE_DISBALANCE_TRANSACTION')
            else:
                print(error_message)

    def delete_disbalance_transaction(self, transaction: DisbalanceTransaction):
        try:
            self.cursor.callproc('DELETE_DISBALANCE_TRANSACTION', [transaction.id])
        except Exception as e:
            error, = e.args
            error_code = error.code
            error_message = error.message
            if no_such_identifier_text in error_message:
                print('[ERROR] You have to log in to call DELETE_DISBALANCE_TRANSACTION')
            else:
                print(error_message)

    def get_p2p_debts_by_person_id(self, is_debtor: bool, debtor: Debtor, debtors: [Debtor], start_date: str = '',
                                   end_date: str = ''):
        try:
            entry_tuples = (self.cursor.callproc('GET_P2P_DEBTS_BY_PERSON_ID',
                                                 [self.cursor.var(oracledb.CURSOR), debtor.id,
                                                  'Y' if is_debtor else 'N', start_date, end_date])[0].
                            fetchall())
            return [{'person_name': list(filter(lambda x: x.id == entry[0], debtors))[0].name,
                     'amount': float(entry[1]) / 100} for entry in entry_tuples]
        except Exception as e:
            error, = e.args
            error_code = error.code
            error_message = error.message
            if no_such_identifier_text in error_message:
                print('[ERROR] You have to log in to call GET_P2P_DEBTS_BY_PERSON_ID')
            else:
                print(error_message)
            return []

    def calculate_p2p_debts(self, lender: Debtor, debtor: Debtor):
        try:
            self.cursor.callproc('CALCULATE_P2P_DEBTS', [lender.id, debtor.id])
        except Exception as e:
            error, = e.args
            error_code = error.code
            error_message = error.message
            if no_such_identifier_text in error_message:
                print('[ERROR] You have to log in as admin to call CALCULATE_P2P_DEBTS')
            else:
                print(error_message)

    def get_total_debt(self, debtor: Debtor, start_date: str = '', end_date: str = '') -> float:
        result = self.cursor.var(oracledb.NUMBER)
        try:
            self.cursor.callproc('GET_TOTAL_DEBT', [debtor.id, start_date, end_date, result])
        except Exception as e:
            error, = e.args
            error_code = error.code
            error_message = error.message
            if no_such_identifier_text in error_message:
                print('[ERROR] You have to log in to call GET_TOTAL_DEBT')
            else:
                print(error_message)
            return 0
        return float(result.getvalue()) / 100

    def get_total_balance(self, debtor: Debtor, start_date: str = '', end_date: str = '') -> float:
        result = self.cursor.var(oracledb.NUMBER)
        try:
            self.cursor.callproc('GET_TOTAL_BALANCE', [debtor.id, start_date, end_date, result])
        except Exception as e:
            error, = e.args
            error_code = error.code
            error_message = error.message
            if no_such_identifier_text in error_message:
                print('[ERROR] You have to log in to call GET_TOTAL_BALANCE')
            else:
                print(error_message)
            return 0
        return float(result.getvalue()) / 100

    def wipe_database(self):
        try:
            self.cursor.callproc('WIPE_DATABASE', [1337])
        except Exception as e:
            error, = e.args
            error_code = error.code
            error_message = error.message
            if no_such_identifier_text in error_message:
                print('[ERROR] You have to log in as admin to call WIPE_DATABASE')
            else:
                print(error_message)
