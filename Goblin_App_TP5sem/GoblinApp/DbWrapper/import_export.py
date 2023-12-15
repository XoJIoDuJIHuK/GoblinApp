import json

from .db_controller import Role, User, DebtTransaction, Debtor, DebtorEntry, DisbalanceTransaction, \
    DbController


class Exporter:
    @staticmethod
    def export_roles(roles: [Role]):
        filename = 'roles.json'
        with open(filename, 'w') as f:
            json.dump([{'id': role.id, 'name': role.name} for role in roles], f)
        return filename

    @staticmethod
    def export_users(users):
        filename = 'users.json'
        with open(filename, 'w') as f:
            json.dump([{'id': user['id'], 'name': user['name'], 'password': user['password'],
                        'roles': json.dumps([role.id for role in user['roles']])} for user in users], f)
        return filename

    @staticmethod
    def export_debtors(debtors: [Debtor]):
        filename = 'debtors.json'
        with open(filename, 'w') as f:
            json.dump([{'id': debtor.id, 'name': debtor.name,
                        'user_id': debtor.user_id} for debtor in debtors], f)
        return filename

    @staticmethod
    def export_debt_transactions(transactions: [DebtTransaction]):
        filename = 'debt_transactions.json'
        with open(filename, 'w') as f:
            json.dump([{'id': t.id, 'name': t.name, 'amount': t.amount, 'lender': t.lender.id,
                        'date': t.date, 'description': t.description, 'debtors_entries': json.dumps(
                    [{'debtor_id': entry.debtor.id, 'multiplier': entry.multiplier,
                      'fulfilled': entry.fulfilled} for entry in t.debtors_entries]
                ), 'restrictions': json.dumps([role.id for role in t.restrictions])} for t in transactions], f)
        return filename

    @staticmethod
    def export_disbalance_transactions(transactions: [DisbalanceTransaction]):
        filename = 'disbalance_transactions.json'
        with open(filename, 'w') as f:
            json.dump([{'id': t.id, 'name': t.name, 'amount': t.amount, 'reason': t.reason,
                        'date': t.date, 'user_id': t.user.id} for t in transactions], f)
        return filename


class Importer:
    @staticmethod
    def import_roles(db_controller: DbController):
        filename = 'roles.json'
        with open(filename, 'r') as f:
            new_roles = json.loads(f.read())
            for role in new_roles:
                db_controller.add_role(p_id=role['id'], name=role['name'])
        return filename

    @staticmethod
    def import_debtors(db_controller: DbController):
        filename = 'debtors.json'
        with open(filename, 'r') as f:
            new_debtors = json.loads(f.read())
            for debtor in new_debtors:
                db_controller.add_debtor(p_id=debtor['id'], user_id=None, name=debtor['name'])
        return filename

    @staticmethod
    def import_users(db_controller: DbController, db_storage):
        filename = 'users.json'
        with open(filename, 'r') as f:
            new_users = json.loads(f.read())
            for user in new_users:
                user_roles = list(map(lambda x: list(filter(lambda y: y.id == int(x), db_storage['roles']))[0],
                                      json.loads(user['roles'])))
                db_controller.add_user(p_id=user['id'],
                                       name=user['name'],
                                       password=user['password'],
                                       roles=user_roles)
        return filename

    @staticmethod
    def import_debt_transactions(db_controller: DbController, db_storage):
        filename = 'debt_transactions.json'
        with open(filename, 'r') as f:
            new_transactions = json.loads(f.read())
            for t in new_transactions:
                print(json.loads(t['restrictions']))
                db_controller.add_debt_transaction(p_id=int(t['id']),
                                                   name=t['name'],
                                                   amount=float(t['amount']),
                                                   lender=list(filter(lambda x: x.id == int(t['lender']),
                                                                      db_storage['debtors']))[0],
                                                   date=t['date'],
                                                   description=t['description'],
                                                   restrictions=list(map(lambda x: Role(role_id=int(x),
                                                                                        name=''),
                                                                         json.loads(t['restrictions']))))
                debtors_entries = json.loads(t['debtors_entries'])
                sum_multiplier = sum(map(lambda x: float(x['multiplier']), debtors_entries))
                for entry in debtors_entries:
                    db_controller.add_debtor_entry_by_transaction_id(transaction_id=int(t['id']),
                                                                     debtor_id=int(entry['debtor_id']),
                                                                     multiplier=float(entry['multiplier']),
                                                                     amount=float(t['amount']) *
                                                                            float(entry['multiplier']) /
                                                                            sum_multiplier,
                                                                     fulfilled=entry['fulfilled'])
        return filename

    @staticmethod
    def import_disbalance_transactions(db_controller: DbController, db_storage):
        filename = 'disbalance_transactions.json'
        with open(filename, 'r') as f:
            new_transactions = json.loads(f.read())
            for t in new_transactions:
                db_controller.add_disbalance_transaction(name=t['name'],
                                                         amount=float(t['amount']),
                                                         reason=t['reason'],
                                                         date=t['date'],
                                                         user=list(filter(lambda x: x.id == int(t['user_id']),
                                                                          db_storage['users']))[0])
        return filename
