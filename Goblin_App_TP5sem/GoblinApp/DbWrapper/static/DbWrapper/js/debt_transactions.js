const todaysDate = new Date()

const fulfilled = 'fulfilled'

const getDebtorEntryInnerHTML = (debtor) => `<button type="button" onclick="switchFulfilled(this.parentNode)"></button>
    <input type="hidden" name="debtor_id" value="${debtor.id}"/>
    <span>${debtor.name}</span>
    <input type="number" value=1 min=0/>`

let all_debtors = []

const white = '#fff'
const black = '#000'
const colors = [['rgb(198, 16, 16)', white], ['rgb(214, 115, 29)', white], ['rgb(255, 225, 0)', black],
                ['rgb(62, 138, 0)', white], ['rgb(0, 138, 41)', white], ['rgb(92, 255, 244)', black],
                ['rgb(0, 44, 154)', white], ['rgb(128, 55, 255)', white], ['rgb(255, 55, 248)', white]]

const unused_debtors_element = document.querySelector('#unused_debtors')
const transaction_debtors_element = document.querySelector('#transaction_debtors')
const addForm = document.querySelector('.add_form')
const addFormWrapper = document.querySelector('#add-debt-transaction-form-wrapper')

let current_editing_transaction_id = undefined

const addFormTextValues = {
    add: {
        header: 'Добавить транзакцию',
        name: 'Название по умолчанию',
        amount: 1,
        lender: 0,
        date: `${rjust("" + todaysDate.getFullYear(), 4, '0')}-` +
              `${rjust(todaysDate.getMonth() + 1 + "", 2, '0')}-` +
              `${rjust("" + todaysDate.getDate(), 2, '0')}`,
        description: '',
        confirm: 'Создать'
    },
    edit: {
        header: 'Изменить транзакцию',
        confirm: 'Сохранить'
    }
}

if (isLoggedIn()) {
    fetch('get_debtors', {
        'method': 'GET',
    })
    .then(r => {
        if (r.ok) {
            return r.json()
        } else {
            alert(r.status)
        }
    })
    .then(data => {
        all_debtors = data
        for (let debtor of all_debtors) {
            createDebtorCard(debtor)
        }
    })
}

const createDebtorEntry = (debtor) => {
    let debtor_entry = document.createElement('div')
    debtor_entry.ondblclick = (event) => dontUseDebtor(event.target)
    debtor_entry.classList.add('debtor_entry')
    element_colors = colors[Math.floor(Math.random() * colors.length)]
    debtor_entry.style = `background-color: ${element_colors[0]}; color: ${element_colors[1]}`
    debtor_entry.innerHTML = getDebtorEntryInnerHTML(debtor)
    transaction_debtors_element.appendChild(debtor_entry)
}

const createDebtorCard = (debtor) => {
    let debtor_element = document.createElement('div')
    element_colors = colors[Math.floor(Math.random() * colors.length)]
    debtor_element.onclick = (event) => {
        useDebtor(event.target)
    }
    debtor_element.classList.add('debtor_card')
    debtor_element.style = `background-color: ${element_colors[0]}; color: ${element_colors[1]}`
    debtor_element.innerText = debtor.name
    unused_debtors_element.appendChild(debtor_element)
}

const useDebtor = (debtor_card) => {
    let debtor = all_debtors.find(e => e.name === debtor_card.innerText)
    unused_debtors_element.removeChild(debtor_card)
    createDebtorEntry(debtor)
}

const dontUseDebtor = (debtor_entry) => {
    if (debtor_entry.tagName === 'DIV') {
        let debtor = all_debtors.find(e => e.name === debtor_entry.innerText)
        transaction_debtors_element.removeChild(debtor_entry)
        createDebtorCard(debtor)
    }
}

const switchFulfilled = (debtor_entry) => {
    debtor_entry.classList.toggle(fulfilled)
}

const showAddForm = () => {
    addFormWrapper.classList.remove('hidden')
    current_editing_transaction_id = undefined
    setUpAddForm(true)
}

const cancelAddTransaction = () => {
    for (debtor_entry of addForm.querySelectorAll('.debtor_entry')) {
        dontUseDebtor(debtor_entry)
    }
    addFormWrapper.classList.add('hidden')
}

const onAddSubmit = (event) => {
    const name = addForm.querySelector('input[name=transaction_name]').value
    if (!testName(name)) {
        alert("Использование специальных символов недопустимо")
        return
    }
    entries = []
    roles = Array.from(addForm.querySelectorAll('#transaction-roles .role')).map(x => x.innerText)
    for (entry of addForm.querySelector('#transaction_debtors').children) {
        entries.push({
            id: entry.querySelector('input[type=hidden]').value,
            name: entry.innerText,
            multiplier: entry.querySelector('input[type=number]').value,
            fulfilled: entry.classList.contains('fulfilled')
        })
    }
    if (entries.length === 0) {
        alert("Выберите хотя бы одного должника")
        return
    }
    event.preventDefault()

    let selectLender = addForm.querySelector('select[name=transaction_lender]')
    fetch('add_debt_transaction', {
        method: current_editing_transaction_id ? 'POST' : 'PUT',
        headers: {
            'X-CSRFToken': addForm.querySelector('input[name=csrfmiddlewaretoken').value,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            transaction_id: current_editing_transaction_id || 0,
            transaction_name: name,
            transaction_amount: +addForm.querySelector('input[name=transaction_amount]').value,
            transaction_lender: all_debtors.find(x => x.name === 
                selectLender.options[selectLender.selectedIndex].innerText).id,
            transaction_date: addForm.querySelector('input[name=transaction_date]').value,
            transaction_description: addForm.querySelector('textarea[name=transaction_description]').value,
            transaction_debtors_entries: entries,
            transaction_restrictions: roles
        })
    })
    .then(r => {
        if (r.ok) {
            location.reload()
        } else {
            alert(r.status)
        }
    })
}

const deleteTransaction = button => {
    fetch('delete_debt_transaction', {
        method: 'DELETE',
        headers: {
            'X-CSRFToken': addForm.querySelector('input[type="hidden"][name=csrfmiddlewaretoken').value,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            transaction_id: button.querySelector('input[type="hidden"][name="transaction_id"]').value
        })
    })
    .then(r => {
        if (r.ok) {
            location.reload()
        } else {
            alert(r.status)
        }
    })
}

function onTransactionClick(transaction_card, event) {
    transactionIdInput = transaction_card.querySelector('input[type=hidden][name=transaction_id]')
    if (!transactionIdInput) {
        return
    }
    if (event.target.classList.contains('delete-element') || !addFormWrapper.classList.contains('hidden')) {
        return
    }
    current_editing_transaction_id = +transactionIdInput.value
    addFormWrapper.classList.remove('hidden')
    setUpAddForm(false, transaction_card)
}

function setUpAddForm(isAdd, transaction_card = undefined) {
    const selectLender = addForm.querySelector('select[name=transaction_lender]')
    const header = addForm.querySelector('h2')

    const name_input = addForm.querySelector('input[name=transaction_name')
    const amount_input = addForm.querySelector('input[name=transaction_amount')
    const date_input = addForm.querySelector('input[name=transaction_date')
    const description_input = addForm.querySelector('textarea[name=transaction_description')
    const unusedRolesWrapper = addForm.querySelector('#unused-roles')
    const transactionRolesWrapper = addForm.querySelector('#transaction-roles')
    const submit_button = addForm.querySelector('button[name=submit_button')
    if (isAdd) {
        header.innerText = addFormTextValues.add.header
        name_input.value = addFormTextValues.add.name
        amount_input.value = addFormTextValues.add.amount
        selectLender.selectedIndex = 0
        date_input.value = addFormTextValues.add.date
        description_input.value = addFormTextValues.add.description
        submit_button.innerText = addFormTextValues.add.confirm
        unusedRolesWrapper.innerHTML = ''
        transactionRolesWrapper.innerHTML = ''
        for (let role of allRoles) {
            unusedRolesWrapper.appendChild(RoleComponent(role, addRoleRestriction))
        }
    } else if (transaction_card) {
        const name = transaction_card.querySelector('.first-row > .name').innerText
        const amount = +transaction_card.querySelector('.first-row > .amount').innerText
        const lender_name = transaction_card.querySelector('.first-row > .lender').innerText
        const date = transaction_card.querySelector('.first-row > .date').innerText
        const description = transaction_card.querySelector('.second-row > .description').innerText
        name_input.value = name
        amount_input.value = amount
        let i = 0
        for (option of selectLender.options) {
            if (option.innerText === lender_name) {
                selectLender.selectedIndex = i
                break
            }
            i++
        }
        date_input.value = date
        description_input.value = description
        for (debtor_card of transaction_card.querySelectorAll('.debtor-entry')) {
            const debtor_id = debtor_card.querySelector('input[name=debtor_entry_debtor_id]').value
            const multiplier = debtor_card.querySelector('input[name=debtor_entry_multiplier]').value
            const fulfilled = debtor_card.querySelector('input[name=debtor_entry_fulfilled]').value
            for (let debtor_form_card of addForm.querySelectorAll('#unused_debtors .debtor_card')) {
                if (debtor_form_card.innerText.trim() === debtor_card.innerText.trim()) {
                    useDebtor(debtor_form_card)
                }
            }
            for (let debtor_entry of addForm.querySelectorAll('#transaction_debtors .debtor_entry')) {
                if (debtor_entry.querySelector('input[name="debtor_id"]').value === debtor_id) {
                    debtor_entry.querySelector('input[type=number]').value = +multiplier
                    if (fulfilled === 'True') {
                        switchFulfilled(debtor_entry)
                    }
                    break;
                }
            }
        }

        const transactionRoles = Array.from(transaction_card.
            querySelectorAll('input[type=hidden][name=transaction-restriction]')).map(x => x.value)
        const unusedRoles = allRoles.filter(x => transactionRoles.indexOf(x) === -1)
        unusedRolesWrapper.innerHTML = ''
        transactionRolesWrapper.innerHTML = ''
        for (let role of unusedRoles) {
            unusedRolesWrapper.appendChild(RoleComponent(role, addRoleRestriction))
        }
        for (let role of transactionRoles) {
            transactionRolesWrapper.appendChild(RoleComponent(role, removeRoleRestriction))
        }
        header.innerText = addFormTextValues.edit.header
        submit_button.innerText = addFormTextValues.edit.confirm
    }    
}

function addRoleRestriction(event) {
    addForm.querySelector('#transaction-roles').appendChild(RoleComponent(event.target.innerText, removeRoleRestriction))
    addForm.querySelector('#unused-roles').removeChild(event.target)
}
function removeRoleRestriction(event) {
    addForm.querySelector('#unused-roles').appendChild(RoleComponent(event.target.innerText, addRoleRestriction))
    addForm.querySelector('#transaction-roles').removeChild(event.target)
}