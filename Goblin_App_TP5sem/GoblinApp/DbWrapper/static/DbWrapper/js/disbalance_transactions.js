const todaysDate = new Date()
let currentEditingTransaction = 1

const filterFormSelf = document.querySelector('#disbalance-transactions-filter')
const filterForm = {
    self: filterFormSelf,
    mode: filterFormSelf.querySelector('#filter-mode'),
    reason: filterFormSelf.querySelector('#filter-reason'),
    date: filterFormSelf.querySelector('input[name=filter-date]'),
}

const addFormSelf = document.querySelector('#add-form')
const addForm = {
    self: addFormSelf,
}

if (addFormSelf) {
    addForm.wrapper = document.querySelector('#add-disbalance-transaction-form-wrapper')
    addForm.header = addFormSelf.querySelector('h2')
    addForm.name = addFormSelf.querySelector('input[name="transaction-name"')
    addForm.amount = addFormSelf.querySelector('input[name="transaction-amount"')
    addForm.date = addFormSelf.querySelector('input[name="transaction-date"')
    addForm.newReason = addFormSelf.querySelector('#new-transaction-reason')
    addForm.selectReason = addFormSelf.querySelector('#select-transaction-reason')
    addForm.submitButton = addFormSelf.querySelector('button.submit-button')
}

function showAddForm(event) {
    addForm.wrapper.classList.remove(hidden)
    if (currentEditingTransaction) {
        currentEditingTransaction = undefined
        switchAddFormToAddMode()
    }
}

function showEditForm(event) {
    if (!event.target.classList.contains(deleteElement)) {
        addForm.wrapper.classList.remove(hidden)
        clickedElement = event.target
        while (!clickedElement.classList.contains('disbalance-transaction')) {
            clickedElement = clickedElement.parentNode
        }
        currentEditingTransaction = 
            clickedElement.querySelector('input[type=hidden][name=transaction-id]').value
        switchAddFormToEditMode(clickedElement)
    }
}

function switchAddFormToAddMode() {
    addForm.header.innerText = 'Добавить транзакцию'
    addForm.name.value = 'Transaction'
    addForm.amount.value = 0
    addForm.date.value = `${rjust("" + todaysDate.getFullYear(), 4, '0')}-` +
        `${rjust(todaysDate.getMonth() + 1 + "", 2, '0')}-` +
        `${rjust("" + todaysDate.getDate(), 2, '0')}`
    addForm.self.querySelector('input[type="radio"][name="transaction-reason-mode"][value="new"]')
        .checked = true
    addForm.newReason.value = ''
    addForm.selectReason.selectedIndex = 0
    addForm.submitButton.innerText = 'Добавить'
}

function switchAddFormToEditMode(transactionCard) {
    addForm.header.innerText = 'Изменить транзакцию'
    addForm.name.value = transactionCard.querySelector('div.name').innerText
    addForm.amount.value = transactionCard.querySelector('div.amount').innerText
    addForm.date.value = transactionCard.querySelector('div.date').innerText
    addForm.self.querySelector('input[type="radio"][name="transaction-reason-mode"][value="select"]')
        .checked = true
    addForm.newReason.value = ''
    let i = 0
    const reason = transactionCard.querySelector('div.reason').innerText
    for (let option of addForm.selectReason.options) {
        if (option.value === reason) break
        i++
    }
    addForm.selectReason.selectedIndex = i
    console.log(addForm.submitButton)
    addForm.submitButton.innerText = 'Сохранить'
}

function hideAddForm() {
    addForm.wrapper.classList.add(hidden)
}

function addFormSubmit() {
    const name = addForm.name.value
    if (name.startsWith('[auto] ') && !testName(name.substring(7)) || 
        !name.startsWith('[auto] ') && !testName(name)) {
        alert("Использование специальных символов недопустимо")
        return
    }
    method = currentEditingTransaction ? 'POST' : 'PUT'
    const body = {
        'name': name,
        'amount': addForm.amount.value,
        'date': addForm.date.value,
        'reason': (addForm.self.querySelector('input[type=radio][name=transaction-reason-mode][value=new]').checked ?
            addForm.newReason.value || "Просто так" : addForm.selectReason.options[addForm.selectReason.selectedIndex].value) || 'Просто так',
    }
    if (body['amount'] == 0) {
        alert('Количество не может равняться нулю')
        return
    }
    if (currentEditingTransaction) body['id'] = currentEditingTransaction
    fetch('add_disbalance_transaction', {
        method: method,
        headers: {
            'X-CSRFToken': addForm.self.querySelector('input[type="hidden"][name=csrfmiddlewaretoken').value,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(body)
    })
    .then(r => {
        if (r.ok) {
            location.reload()
        } else {
            alert(r.status)
        }
    })
}

function deleteDisbalanceTransaction(event) {
    let deleteElement = event.target
    while (!deleteElement.classList.contains('disbalance-transaction')) 
        deleteElement = deleteElement.parentNode
    fetch('delete_disbalance_transaction', {
        method: 'DELETE',
        headers: {
            'X-CSRFToken': deleteElement.querySelector('input[type=hidden][name=csrfmiddlewaretoken]').value,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            'id': deleteElement.
                querySelector('input[type=hidden][name=transaction-id]').value
        })
    })
    .then(r => {
        if (r.ok) {
            deleteElement.parentNode.removeChild(deleteElement)
        } else {
            alert(r.status)
        }
    })
}