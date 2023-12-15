const csrfToken = document.querySelector('#admin-wrapper input[type=hidden][name=csrfmiddlewaretoken]').value
const defaultHeaders = {
    'X-CSRFToken': csrfToken,
    'Content-Type': 'application/json',
}

function deleteUser() {
    const userId = document.querySelector('#admin-wrapper div.table-wrapper.users input[type=number][name=user-id]').value
    if (userId < 1) {
        alert("Идентификатор не может быть меньше единицы")
        return
    }
    fetch('admin', {
        method: "DELETE",
        headers: defaultHeaders,
        body: JSON.stringify({
            userId
        })
    })
    .then(r => {
        if (r.ok) {
            location.reload()
        } else if (r.status === 401) {
            alert("Вы не можете удалить самого себя")
        } else {
            alert(r.status)
        }
    })
}

function deleteDebtor() {
    const debtorId = document.querySelector('#admin-wrapper div.table-wrapper.debtors input[type=number][name=debtor-id]').value
    if (debtorId < 1) {
        alert("Идентификатор не может быть меньше единицы")
        return
    }
    fetch('admin', {
        method: "DELETE",
        headers: defaultHeaders,
        body: JSON.stringify({
            debtorId
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

function createDebtor() {
    const debtorName = document.querySelector('#admin-wrapper div.table-wrapper.debtors input[type=text][name=debtor-name]').value
    const userId = document.querySelector('#admin-wrapper div.table-wrapper.debtors input[type=number][name=user-id]').value
    if (!debtorName) {
        alert('Неправильное имя должника')
    }
    fetch('admin', {
        method: "PUT",
        headers: defaultHeaders,
        body: JSON.stringify({
            debtorName,
            userId
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

function calculateAllDebts() {
    fetch('admin', {
        method: "POST",
        headers: defaultHeaders,
        body: JSON.stringify({
            'calculateAllDebts': true
        })
    })
    .then(r => {
        if (r.ok) {
            alert('Расчёт выполнен')
        } else {
            alert(r.status)
        }
    })
}