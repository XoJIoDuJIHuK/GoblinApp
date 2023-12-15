create user GUEST identified by guest_password;
create user COMMON_USER identified by user_password;
create user ADMIN identified by admin_password;

grant create session, restricted session to GUEST, COMMON_USER, ADMIN;
grant execute on GET_ROLES to GUEST, COMMON_USER, ADMIN;
grant execute on GET_DEBT_TRANSACTIONS to GUEST, COMMON_USER, ADMIN;
grant execute on GET_DEBTORS to GUEST, COMMON_USER, ADMIN;
grant execute on GET_DEBTORS_ENTRIES to GUEST, COMMON_USER, ADMIN;
grant execute on GET_TRANSACTION_RESTRICTIONS to GUEST, COMMON_USER, ADMIN;
grant execute on IS_LOGIN_CORRECT to GUEST, COMMON_USER, ADMIN;
grant execute on ADD_USER to GUEST, COMMON_USER, ADMIN;

grant execute on GET_TOTAL_BALANCE to COMMON_USER, ADMIN;
grant execute on GET_DISBALANCE_TRANSACTIONS to COMMON_USER, ADMIN;
grant execute on GET_TOTAL_DEBT to COMMON_USER, ADMIN;
grant execute on GET_P2P_DEBTS_BY_PERSON_ID to COMMON_USER, ADMIN;
grant execute on ADD_DEBT_TRANSACTION to COMMON_USER, ADMIN;
grant execute on ADD_DEBTOR_ENTRY to COMMON_USER, ADMIN;
grant execute on ADD_DISBALANCE_TRANSACTION to COMMON_USER, ADMIN;
grant execute on ADD_TRANSACTION_RESTRICTION to COMMON_USER, ADMIN;
grant execute on ADD_USER_ROLE to COMMON_USER, ADMIN;
grant execute on DELETE_DEBT_TRANSACTION to COMMON_USER, ADMIN;
grant execute on DELETE_DEBTOR_ENTRY to COMMON_USER, ADMIN;
grant execute on DELETE_DISBALANCE_TRANSACTION to COMMON_USER, ADMIN;
grant execute on DELETE_TRANSACTION_RESTRICTION to COMMON_USER, ADMIN;
grant execute on DELETE_USER_ROLE to COMMON_USER, ADMIN;
grant execute on GET_USERS to COMMON_USER, ADMIN;
grant execute on GET_USER_ROLES to COMMON_USER, ADMIN;
grant execute on UPDATE_DISBALANCE_TRANSACTION to COMMON_USER, ADMIN;
grant execute on UPDATE_DEBT_TRANSACTION to COMMON_USER, ADMIN;

grant execute on ADD_DEBTOR to ADMIN;
grant execute on ADD_ROLE to ADMIN;
grant execute on DELETE_DEBTOR to ADMIN;
grant execute on DELETE_ROLE to ADMIN;
grant execute on DELETE_USER to ADMIN;
grant execute on CALCULATE_P2P_DEBTS to ADMIN;
grant execute on WIPE_DATABASE to ADMIN;
grant execute on GET_USERS_FOR_EXPORT to ADMIN;

create tablespace GOBLIN_PERM_TBS datafile 'GOBLIN_PERM_TBS.dbf' size 10M autoextend on;

create sequence ROLES_ID_SEQ cycle;
drop sequence ROLES_ID_SEQ;
create table ROLES (
    id int default ROLES_ID_SEQ.nextval primary key,
    name nvarchar2(50) not null unique
);
drop table ROLES;
create or replace procedure GET_ROLES(p_cursor out SYS_REFCURSOR) as
    begin
        open p_cursor for select * from ROLES;
    end;
drop procedure GET_ROLES;
create or replace procedure ADD_ROLE(p_id int, role_name nvarchar2, result out int) as
    auxil_number int := 0;
    begin
        select count(*) into auxil_number from ROLES where name = role_name;
        if auxil_number = 1 then
            result := -1;
        else
            if p_id = -1 then
                insert into ROLES (name) values (role_name);
            else
                insert into ROLES (id, name) values (p_id, role_name);
            end if;
            commit;
            result := 0;
        end if;
    exception
        when others then
            result := -1;
    end;
drop procedure ADD_ROLE;
create or replace procedure DELETE_ROLE(p_id int) as
    begin
        delete ROLES where id = p_id;
        commit;
    end;
drop procedure DELETE_ROLE;

create sequence USERS_ID_SEQ cycle;
DROP sequence USERS_ID_SEQ;
create table USERS (
    id int default USERS_ID_SEQ.nextval primary key,
    name nvarchar2(50) not null unique,
    password nvarchar2(256) not null
);
drop table USERS;
create or replace procedure IS_LOGIN_CORRECT(login nvarchar2, password_hash nvarchar2, result out int) as
    found_users int;
    begin
        select count(*) into found_users from USERS where name = login and password = password_hash;
        if found_users = 1 then
            result := 1;
        else
            result := -1;
        end if;
    end;
drop procedure IS_LOGIN_CORRECT;
create or replace procedure GET_USERS(p_cursor out SYS_REFCURSOR) as
    begin
        open p_cursor for select id, name from USERS order by id;
    end;
drop procedure GET_USERS;
create or replace procedure GET_USERS_FOR_EXPORT(p_cursor out SYS_REFCURSOR) as
    begin
        open p_cursor for select id, name, password from USERS;
    end;
drop procedure GET_USERS_FOR_EXPORT;
create or replace procedure ADD_USER(p_id int, p_name nvarchar2, p_password nvarchar2, result out int) as
    similar_usernames int := 0;
    number_of_existing_debtors int := 0;
    begin
        select count(*) into similar_usernames from USERS where name = p_name and (p_id = -1 or p_id = id);
        if similar_usernames = 0 then
            if p_id = -1 then
                insert into USERS(name, password) values (p_name, p_password);--replace needed
            else
                insert into USERS(id, name, password) values (p_id, p_name, p_password);--replace needed
            end if;
            select id into result from USERS where name = p_name and password = p_password and ROWNUM = 1;
            select count(*) into number_of_existing_debtors from DEBTORS where name = p_name;
            if number_of_existing_debtors = 0 then
                ADD_DEBTOR(-1, p_name, result, result);
            else
                update DEBTORS set USER_ID = result where name = p_name;
            end if;
            commit;
        else
            result := -1;
        end if;
    end;
drop procedure ADD_USER;
create or replace procedure DELETE_USER(user_id int) as
    begin
        delete USERS where id = user_id;
        commit;
    end;
drop procedure DELETE_USER;

create sequence USERS_ROLES_ID_SEQ cycle;
create table USERS_ROLES (
    id int default USERS_ROLES_ID_SEQ.nextval primary key,
    user_id int not null constraint USERS_ROLES_USER_ID_FK references USERS(id) on delete cascade,
    role_id int not null constraint USERS_ROLES_ROLE_ID_FK references ROLES(id) on delete cascade
);
alter table USERS_ROLES INMEMORY;
drop table USERS_ROLES;
create or replace procedure GET_USER_ROLES (p_cursor out SYS_REFCURSOR, u_id int) as
begin
    open p_cursor for select role_id from USERS_ROLES where user_id = u_id;
end;
drop procedure GET_USER_ROLES;
create or replace procedure ADD_USER_ROLE (p_user_id int, p_role_id int) as
    role_exists int;
    user_exists int;
    selected_role nvarchar2(50);
    trying_to_assign_admin exception;
begin
    select name into selected_role from ROLES where id = p_role_id;
    if selected_role = 'admin' then raise trying_to_assign_admin; end if;
    select count(*) into user_exists from USERS where p_user_id = id;
    if user_exists = 0 then
        return;
    end if;
    select count(*) into role_exists from USERS_ROLES where user_id = p_user_id and role_id = p_role_id;
    if role_exists = 0 then
        insert into USERS_ROLES (user_id, role_id) VALUES (p_user_id, p_role_id);
        commit;
    end if;
    exception
        when trying_to_assign_admin then
            RAISE_APPLICATION_ERROR(-20002, 'Cannot assign admin role through this procedure');
        when others then
            RAISE_APPLICATION_ERROR(-20001, sqlerrm);
end;
drop procedure ADD_USER_ROLE;
create or replace procedure DELETE_USER_ROLE (p_user_id int, p_role_id int) as
begin
    delete USERS_ROLES where user_id = p_user_id and role_id = p_role_id;
    commit;
end;
drop procedure DELETE_USER_ROLE;

create sequence DEBTORS_ID_SEQ cycle;
DROP sequence DEBTORS_ID_SEQ;
create table DEBTORS (
    id int default DEBTORS_ID_SEQ.nextval primary key,
    name nvarchar2(50) unique not null,
    user_id int constraint ga_debtors_user_id_fk references USERS(id) on delete set null
);
drop table DEBTORS;
alter table DEBTORS INMEMORY;
create or replace procedure GET_DEBTORS(p_cursor out SYS_REFCURSOR) as
    begin
        open p_cursor for select * from DEBTORS order by name;
    end;
drop procedure GET_DEBTORS;
create or replace procedure ADD_DEBTOR(p_id int, p_name nvarchar2, p_user_id int, result out int) as
    auxil_number int := 0;
    existing_debtors int := 0;
    begin
        if p_id != -1 then
            select count(*) into existing_debtors from DEBTORS where id = p_id;
            if existing_debtors != 0 then
                result := -1;
                return;
            end if;
        end if;
        select count(*) into auxil_number from DEBTORS where name = p_name;
        if auxil_number = 0 then
            if p_id = -1 then
                insert into DEBTORS (name, user_id) values (p_name, p_user_id);
            else
                insert into DEBTORS (id, name, user_id) values (p_id, p_name, p_user_id);
            end if;
            select id into auxil_number from DEBTORS where name = p_name;

            for debtor_entry in (select id from DEBTORS where id != auxil_number) loop
                insert into P2P_DEBTS (lender, debtor) values (debtor_entry.id, auxil_number);
                insert into P2P_DEBTS (lender, debtor) values (auxil_number, debtor_entry.id);
            end loop;
            result := auxil_number;
        else
            result := -1;
        end if;
        commit;
    end;
drop procedure ADD_DEBTOR;
create or replace procedure DELETE_DEBTOR(debtor_id int) as
    begin
        delete DEBTORS where id = debtor_id;
        commit;
    end;
drop procedure DELETE_DEBTOR;

create sequence DEBT_TRANSACTIONS_ID_SEQ cycle;
drop sequence DEBT_TRANSACTIONS_ID_SEQ;
create table DEBT_TRANSACTIONS (
    id int default DEBT_TRANSACTIONS_ID_SEQ.nextval primary key,
    name nvarchar2(50) not null,
    amount int not null,
    lender int constraint ga_debt_transactions_lender_fk references DEBTORS(id) on delete cascade not null,
    transaction_date date,
    description nvarchar2(256)
);
drop table DEBT_TRANSACTIONS;
create or replace procedure GET_DEBT_TRANSACTIONS(p_cursor out SYS_REFCURSOR) as
    begin
        open p_cursor for select * from DEBT_TRANSACTIONS;
    end;
drop procedure GET_DEBT_TRANSACTIONS;
create or replace procedure ADD_DEBT_TRANSACTION(p_id int, p_name nvarchar2, p_amount int, p_lender int,
    p_transaction_date date, p_description nvarchar2, result out int) as
        existing_transactions int := 0;
    begin
        if p_id != -1 then
            select count(*) into existing_transactions from DEBT_TRANSACTIONS where id = p_id;
            if existing_transactions != 0 then
                result := -1;
                return;
            end if;
        end if;
        if p_id = -1 then
            insert into DEBT_TRANSACTIONS (name, amount, lender, transaction_date, description)
            values (p_name, p_amount, p_lender, p_transaction_date, p_description);
        else
            insert into DEBT_TRANSACTIONS (id, name, amount, lender, transaction_date, description)
            values (p_id, p_name, p_amount, p_lender, p_transaction_date, p_description);
        end if;
        select id into result from DEBT_TRANSACTIONS where ROWNUM = 1 order by id desc;
        commit;
    end;
drop procedure ADD_DEBT_TRANSACTION;
create or replace procedure UPDATE_DEBT_TRANSACTION(p_id int, p_name nvarchar2, p_amount int, p_lender int,
    p_transaction_date date, p_description nvarchar2) as
    begin
        update DEBT_TRANSACTIONS set name = p_name, amount = p_amount, lender = p_lender,
                                     transaction_date = p_transaction_date, description = p_description
        where id = p_id;
    end;
create or replace procedure DELETE_DEBT_TRANSACTION(p_id int) as
    debtors_cursor SYS_REFCURSOR;
    v_debtor_id int;
    v_lender_id int;
    begin
        select lender into v_lender_id from DEBT_TRANSACTIONS where id = p_id;
        open debtors_cursor for select e.debtor_id from DEBTORS_ENTRIES e join DEBT_TRANSACTIONS t
            on e.transaction_id = t.id where t.id = p_id and e.debtor_id != t.lender;
        loop
            fetch debtors_cursor into v_debtor_id;
            exit when debtors_cursor%NOTFOUND;
            delete from DEBTORS_ENTRIES where TRANSACTION_ID = p_id and DEBTORS_ENTRIES.DEBTOR_ID = v_debtor_id;
            CALCULATE_P2P_DEBTS(v_lender_id, v_debtor_id);
        end loop;
        delete DEBT_TRANSACTIONS where id = p_id;
        commit;
    end;
drop procedure DELETE_DEBT_TRANSACTION;

create sequence DEBTORS_ENTRIES_ID_SEQ cycle;
drop sequence DEBTORS_ENTRIES_ID_SEQ;
create table DEBTORS_ENTRIES (
    row_id int default DEBTORS_ENTRIES_ID_SEQ.nextval primary key,
    transaction_id int not null constraint GA_DEBTORS_ENTRIES_TRANSACTIONS_ID_FK
        references DEBT_TRANSACTIONS(id) on delete cascade,
    debtor_id int not null constraint GA_DEBTORS_ID_FK references DEBTORS(id) on delete cascade,
    multiplier float not null,
    amount int not null,
    fulfilled char(1) check ( fulfilled in ('Y', 'N') ) not null
);
alter table DEBTORS_ENTRIES inmemory no inmemory(row_id, multiplier, amount, fulfilled);
drop table DEBTORS_ENTRIES;
create or replace procedure GET_DEBTORS_ENTRIES(p_cursor out SYS_REFCURSOR, p_tran_id int) as
    begin
        open p_cursor for select debtor_id, multiplier, fulfilled from DEBTORS_ENTRIES
                                                                  where transaction_id = p_tran_id;
    end;
drop procedure GET_DEBTORS_ENTRIES;
create or replace procedure ADD_DEBTOR_ENTRY(p_tran_id int, p_debtor_id int, p_multiplier float, p_amount int,
p_fulfilled char) as
    auxil_number int;
    lender int;
    begin
        select count(*) into auxil_number from DEBT_TRANSACTIONS where id = p_tran_id;
        if auxil_number = 0 then
            RAISE_APPLICATION_ERROR(-20001, 'trying to add debtor entry for non-existing debt transaction');
        end if;
        select count(*) into auxil_number from DEBTORS_ENTRIES where transaction_id = p_tran_id
                                                                and debtor_id = p_debtor_id;
        if auxil_number = 0 then
            insert into DEBTORS_ENTRIES(transaction_id, debtor_id, multiplier, amount, fulfilled)
                values (p_tran_id, p_debtor_id, p_multiplier, p_amount, p_fulfilled);
        end if;
        select lender into lender from DEBT_TRANSACTIONS
            where id = p_tran_id and ROWNUM = 1;
        CALCULATE_P2P_DEBTS(p_debtor_id, lender);
        commit;
    end;
drop procedure ADD_DEBTOR_ENTRY;
create or replace procedure DELETE_DEBTOR_ENTRY(p_transaction_id int, p_debtor_id int) as
    lender int;
    debtor int;
    begin
        delete DEBTORS_ENTRIES where transaction_id = p_transaction_id and debtor_id = p_debtor_id;
        select lender into lender from DEBT_TRANSACTIONS
            where id = p_transaction_id and ROWNUM = 1;
        select id into debtor from DEBTORS where id = p_debtor_id;
        if debtor is null or lender is null then
            RAISE_APPLICATION_ERROR(-20001, 'Lender or debtor is null');
        end if;
        CALCULATE_P2P_DEBTS(p_debtor_id, lender);
        commit;
    end;
drop procedure DELETE_DEBTOR_ENTRY;

create sequence DEBT_TRANSACTIONS_RESTRICTIONS_ID_SEQ cycle;
create table DEBT_TRANSACTIONS_RESTRICTIONS (
    id int default DEBT_TRANSACTIONS_RESTRICTIONS_ID_SEQ.nextval primary key,
    transaction_id int not null
        constraint DEBT_TRANSACTIONS_RESTRICTIONS_T_ID_FK references DEBT_TRANSACTIONS(id) on delete cascade,
    role_id int not null constraint DEBT_TRANSACTIONS_RESTRICTIONS_R_ID_FK references ROLES(id) on delete cascade
);
drop table DEBT_TRANSACTIONS_RESTRICTIONS;
create or replace procedure GET_TRANSACTION_RESTRICTIONS (p_cursor out SYS_REFCURSOR, p_id int) as
begin
    open p_cursor for select role_id from DEBT_TRANSACTIONS_RESTRICTIONS where transaction_id = p_id;
end;
drop procedure GET_TRANSACTION_RESTRICTIONS;
create or replace procedure ADD_TRANSACTION_RESTRICTION (p_t_id int, p_r_id int) as
begin
    insert into DEBT_TRANSACTIONS_RESTRICTIONS (transaction_id, role_id) VALUES (p_t_id, p_r_id);
    commit;
    exception when others then
        RAISE_APPLICATION_ERROR(-20002, sqlerrm);
end;
drop procedure ADD_TRANSACTION_RESTRICTION;
create or replace procedure DELETE_TRANSACTION_RESTRICTION (p_t_id int, p_r_id int) as
begin
    delete from DEBT_TRANSACTIONS_RESTRICTIONS where transaction_id = p_t_id and role_id = p_r_id;
    commit;
end;
drop procedure DELETE_TRANSACTION_RESTRICTION;


create sequence DISBALANCE_TRANSACTIONS_ID_SEQ cycle;
drop sequence DISBALANCE_TRANSACTIONS_ID_SEQ;
create table DISBALANCE_TRANSACTIONS (
    id int default DISBALANCE_TRANSACTIONS_ID_SEQ.nextval primary key,
    name nvarchar2(50) not null, -- not unique
    amount int not null check ( amount != 0 ),
    reason nvarchar2(50) not null,
    transaction_date date not null,
    user_id int not null constraint DISBALANCE_TRANSACTIONS_USER_ID_FK references USERS(id)
        on delete cascade
);
drop table DISBALANCE_TRANSACTIONS;
create or replace procedure GET_DISBALANCE_TRANSACTIONS(p_cursor out SYS_REFCURSOR, p_user_id int, p_date date,
    p_mode int, p_reason nvarchar2) as
    begin
        commit;
        open p_cursor for select * from DISBALANCE_TRANSACTIONS
                                   where (p_user_id is null or user_id = p_user_id)
                                     and (p_date IS NULL OR transaction_date = p_date)
                                     and (p_mode = 0 OR (p_mode > 0 and amount > 0) or (p_mode < 0 and amount < 0))
                                     and (p_reason is null or reason = p_reason);
    end;
drop procedure GET_DISBALANCE_TRANSACTIONS;
create or replace procedure ADD_DISBALANCE_TRANSACTION(p_name nvarchar2, p_amount float, p_reason nvarchar2,
        p_transaction_date date, p_user_id int) as
    begin
        insert into DISBALANCE_TRANSACTIONS(name, amount, reason, transaction_date, user_id) VALUES
            (p_name, p_amount, p_reason, p_transaction_date, p_user_id);
        commit;
    end;
drop procedure ADD_DISBALANCE_TRANSACTION;
create or replace procedure UPDATE_DISBALANCE_TRANSACTION(p_id int, p_name nvarchar2, p_amount int,
    p_reason nvarchar2, p_date date) as
    begin
        update DISBALANCE_TRANSACTIONS set name=p_name, amount=p_amount, reason=p_reason,
                                           transaction_date=p_date where id=p_id;
        commit;
    end;
drop procedure UPDATE_DISBALANCE_TRANSACTION;
create or replace procedure DELETE_DISBALANCE_TRANSACTION(p_id int) as
    begin
        delete from DISBALANCE_TRANSACTIONS where id = p_id;
        commit;
    end;
drop procedure DELETE_DISBALANCE_TRANSACTION;

create sequence P2P_DEBTS_ID_SEQ cycle;
create table P2P_DEBTS (
    row_id int default P2P_DEBTS_ID_SEQ.nextval primary key,
    lender int not null constraint P2P_DEBTS_LENDER_FK references DEBTORS(id) on delete cascade,
    debtor int not null constraint P2P_DEBTS_DEBTOR_FK references DEBTORS(id) on delete cascade,
    amount int default 0 not null
);
drop table P2P_DEBTS;
create or replace procedure GET_P2P_DEBTS_BY_PERSON_ID(p_cursor out SYS_REFCURSOR, p_id int, is_debtor char,
start_date nvarchar2, end_date nvarchar2) as
    begin
        if length(start_date||'q') = 1 and length(end_date||'q') = 1 then
            if is_debtor = 'Y' then
                open p_cursor for select lender, amount from P2P_DEBTS where debtor = p_id and amount > 0;
            else
                open p_cursor for select debtor, amount from P2P_DEBTS where lender = P_id and amount > 0;
            end if;
        else
            if is_debtor = 'Y' then
                open p_cursor for select e.debtor_id, e.amount from DEBTORS_ENTRIES e join DEBT_TRANSACTIONS t on
                    e.transaction_id = t.id where t.lender != p_id and e.debtor_id = p_id and
                    (length(start_date||'q') = 1 or TO_DATE(start_date, 'YYYY-MM-DD') <= t.transaction_date)
                    and (length(end_date||'q') = 1 or TO_DATE(end_date, 'YYYY-MM-DD') >= t.transaction_date)
                    and e.fulfilled = 'N';
            else
                open p_cursor for select e.debtor_id, e.amount from DEBTORS_ENTRIES e join DEBT_TRANSACTIONS t on
                    e.transaction_id = t.id where t.lender = p_id and e.debtor_id != p_id and
                    (length(start_date||'q') = 1 or TO_DATE(start_date, 'YYYY-MM-DD') <= t.transaction_date)
                    and (length(end_date||'q') = 1 or TO_DATE(end_date, 'YYYY-MM-DD') >= t.transaction_date)
                    and e.fulfilled = 'N';
            end if;
        end if;
    end;
drop procedure GET_P2P_DEBTS_BY_PERSON_ID;
create or replace procedure CALCULATE_P2P_DEBTS (p_lender int, p_debtor int) as
    v_debtors_debt int := 0;
    v_lenders_debt int := 0;
    begin
        select sum(e.amount) into v_debtors_debt from DEBTORS_ENTRIES e join DEBT_TRANSACTIONS t on
            e.transaction_id = t.id where e.debtor_id = p_debtor and e.fulfilled = 'N' and t.lender = p_lender;
        if v_debtors_debt is null then
            v_debtors_debt := 0;
        end if;
        select sum(e.amount) into v_lenders_debt from DEBTORS_ENTRIES e join DEBT_TRANSACTIONS t on
            e.transaction_id = t.id where e.debtor_id = p_lender and e.fulfilled = 'N' and t.lender = p_debtor;
        if v_lenders_debt is null then
            v_lenders_debt := 0;
        end if;
        update P2P_DEBTS set amount = (v_debtors_debt - v_lenders_debt) where lender = p_lender and debtor = p_debtor;
        update P2P_DEBTS set amount = (v_lenders_debt - v_debtors_debt) where lender = p_debtor and debtor = p_lender;
        commit;
    end;
drop procedure CALCULATE_P2P_DEBTS;
create or replace procedure GET_TOTAL_BALANCE(p_id int, start_date nvarchar2, end_date nvarchar2,
result out int) as
    income int;
    outcome int;
begin
    if length(start_date||'q') = 1 and length(end_date||'q') = 1 then
        select sum(amount) into result from P2P_DEBTS where lender = p_id;
    else
        select sum(e.amount) into outcome from DEBTORS_ENTRIES e join DEBT_TRANSACTIONS t on
            e.transaction_id = t.id where e.debtor_id = p_id and t.lender != p_id and
            (length(start_date||'q') = 1 or TO_DATE(start_date, 'YYYY-MM-DD') <= t.transaction_date) and
            (length(end_date||'q') = 1 or TO_DATE(end_date, 'YYYY-MM-DD') >= t.transaction_date)
            and e.fulfilled = 'N';
        select sum(e.amount) into income from DEBTORS_ENTRIES e join DEBT_TRANSACTIONS t on
                e.transaction_id = t.id where e.debtor_id != p_id and t.lender = p_id and
                (length(start_date||'q') = 1 or TO_DATE(start_date, 'YYYY-MM-DD') <= t.transaction_date) and
                (length(end_date||'q') = 1 or TO_DATE(end_date, 'YYYY-MM-DD') >= t.transaction_date)
                and e.fulfilled = 'N';
        if income is null then
            income := 0;
        end if;
        if outcome is null then
            outcome := 0;
        end if;
        result := income - outcome;
    end if;
    if result is null then
        result := 0;
    end if;
end;
create or replace procedure GET_TOTAL_DEBT(p_id int, start_date nvarchar2, end_date nvarchar2,
result out int) as
begin
    if length(start_date||'q') = 1 and length(end_date||'q') = 1 then
        select sum(amount) into result from P2P_DEBTS where debtor = p_id and amount > 0;
    else
        select sum(e.amount) into result from DEBTORS_ENTRIES e join DEBT_TRANSACTIONS t on
            e.transaction_id = t.id where e.debtor_id = p_id and t.lender != p_id and e.fulfilled = 'N' and
            (length(start_date||'q') = 1 or TO_DATE(start_date, 'YYYY-MM-DD') <= t.transaction_date) and
            (length(end_date||'q') = 1 or TO_DATE(end_date, 'YYYY-MM-DD') >= t.transaction_date);
    end if;
    if result is null then
        result := 0;
    end if;
end;

create or replace procedure WIPE_DATABASE(redundant_parameter int) as
begin
    delete DEBT_TRANSACTIONS;
    delete DEBT_TRANSACTIONS_RESTRICTIONS;
    delete DEBTORS;
    delete DEBTORS_ENTRIES;
    delete DISBALANCE_TRANSACTIONS;
    delete P2P_DEBTS;
    delete ROLES;
    delete USERS;
    delete USERS_ROLES;
    commit;
    exception when others then
        rollback;
        RAISE_APPLICATION_ERROR(-20003, sqlerrm);
end;

create index USERS_ROLES_INDEX on USERS_ROLES(USER_ID);
create index DEBT_TRANSACTIONS_INDEX on DEBT_TRANSACTIONS(LENDER);
create index DISBALANCE_TRANSACTIONS_INDEX on DISBALANCE_TRANSACTIONS(USER_ID, TRANSACTION_DATE, AMOUNT, REASON);
create index DEBTORS_ENTRIES_INDEX on DEBTORS_ENTRIES(DEBTOR_ID);
create index P2P_DEBTS_INDEX on P2P_DEBTS(DEBTOR, LENDER);

alter index P2P_DEBTS_INDEX rebuild;

declare
    p_cursor sys_refcursor;
    cursor v_cursor is select lender, debtor from P2P_DEBTS;
    v_row v_cursor%rowtype;
begin
    GET_P2P_DEBTS_BY_PERSON_ID(p_cursor, 74, 'Y', '', '');
    fetch p_cursor into v_row;
    while p_cursor%found loop
        DBMS_OUTPUT.PUT_LINE(v_row.lender||' '||v_row.debtor);
        fetch p_cursor into v_row;
    end loop;
    close p_cursor;
end;

--date debts check
declare
    start_date nvarchar2(10) := '2023-10-12';
    end_date nvarchar2(10) := '';
    is_debtor char(1) := 'N';
    p_cursor sys_refcursor;
    cursor useless_cursor is select lender as person, amount as amount from P2P_DEBTS where debtor = 1 and amount > 0;
    xd useless_cursor%rowtype;
    p_id int := 1;
begin
        open p_cursor for select e.debtor_id, e.amount from DEBTORS_ENTRIES e join DEBT_TRANSACTIONS t on
                    e.transaction_id = t.id where t.lender = p_id and e.debtor_id != p_id and
                    (length(start_date||'q') = 1 or TO_DATE(start_date, 'YYYY-MM-DD') <= t.transaction_date)
                    and (length(end_date||'q') = 1 or TO_DATE(end_date, 'YYYY-MM-DD') >= t.transaction_date);
        loop
            fetch p_cursor into xd;
            exit when p_cursor%notfound;
            DBMS_OUTPUT.PUT_LINE(xd.person||' '||xd.amount);
        end loop;
        close p_cursor;
    end;