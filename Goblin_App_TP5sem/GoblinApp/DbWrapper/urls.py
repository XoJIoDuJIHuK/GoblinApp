from django.urls import path

from . import views

urlpatterns = [
    path("sign", views.sign, name="sign"),
    path("sign_out", views.signout, name="sign_out"),
    path("get_debtors", views.get_debtors, name="get_debtors"),
    path("debt_transactions", views.get_debt_transactions, name="get_debt_transactions"),
    path("add_debt_transaction", views.change_debt_transactions, name="add_debt_transaction"),
    path("delete_debt_transaction", views.delete_debt_transaction, name="delete_debt_transaction"),
    path("disbalance_transactions", views.get_disbalance_transactions, name="disbalance_transactions"),
    path("add_disbalance_transaction", views.change_disbalance_transaction, name="add_disbalance_transaction"),
    path("delete_disbalance_transaction", views.delete_disbalance_transaction, name="delete_disbalance_transaction"),
    path("get_user_roles", views.get_user_roles, name="get_user_roles"),
    path("get_all_roles", views.get_all_roles, name="get_all_roles"),
    path("save_user_roles", views.save_user_roles, name="save_user_roles"),
    path("create_new_role", views.create_new_role, name="create_new_role"),
    path("delete_role", views.delete_role, name="delete_role"),
    path("summary", views.summary_debts, name="summary"),
    path("admin", views.admin_page, name="admin"),
    path("export", views.export, name="export"),
    path("import", views.import_data, name="import"),
    # path("insert_users", views.insert_users, name="insert_users"),
]