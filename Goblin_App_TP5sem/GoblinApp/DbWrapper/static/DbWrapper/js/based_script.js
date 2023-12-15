let currentUserRoles = []
let allRoles = []
let toReload = false
let initialUserRoles = [];
let submitClicksWithExistingDebtorName = 0;
if (isLoggedIn()) {
    (async () => {
        initialUserRoles = await getUserRoles()
    })();
}
const roleManagementWrapperWrapper = document.querySelector('#role-management-wrapper-wrapper')
    
const rolesWindow = {
    wrapper: roleManagementWrapperWrapper
}

function isLoggedIn() {
    return document.querySelector('.user-card > h3').innerText !== 'Гость'
}

if (roleManagementWrapperWrapper) {
    const roleManagementWrapper = document.querySelector('#role-management-wrapper')
    rolesWindow.self = roleManagementWrapper
    rolesWindow.userRolesSection = roleManagementWrapper.querySelector('.user-roles-management')
    rolesWindow.addRoleSection = roleManagementWrapper.querySelector('.add-role-section')
    rolesWindow.deleteRoleSection = roleManagementWrapper.querySelector('.delete-role-section')
    rolesWindow.allRolesWrapper = roleManagementWrapper.querySelector('.all-roles > .roles-wrapper')
    rolesWindow.userRolesWrapper = roleManagementWrapper.querySelector('.user-roles > .roles-wrapper')
    fetchAllRoles()
}

function fetchAllRoles() {
    fetch('get_all_roles', {
        mode: 'no-cors',
        method: 'GET'
    }).then(r => {
        if (r.ok) {
            return r.json()
        } else if (r.status != 401) {
            throw r.status
        }
    }).then(data => {
        allRoles = data
        updateDeleteRolesList()
    }).catch(e => {
        alert(e)
    })
}

const signForm = {
    self: document.querySelector('#sign-form'),
    wrapper: document.querySelector('#sign-form-wrapper'),
    'login-wrapper': document.querySelector('#login-wrapper'),
    'signup-wrapper': document.querySelector('#signup-wrapper'),
    'login-name': document.querySelector('#login-wrapper').querySelector('input[type="text"]'),
    'login-password': document.querySelector('#login-wrapper').querySelector('input[type="password"]'),
    'signup-name': document.querySelector('#signup-wrapper').querySelector('input[type="text"]'),
    'signup-password': document.querySelector('#signup-wrapper').querySelector('input[type="password"]'),
}

const hidden = 'hidden'
const active = 'active'
const deleteElement = 'delete-element'

const onHamburgerClick = () => {
    document.querySelector('#hamburger').classList.toggle(active)
    document.querySelector('aside').classList.toggle(active)
}

function toggleSignFormHidden() {
    signForm.wrapper.classList.toggle(hidden)
    submitClicksWithExistingDebtorName = 0
}

function showLoginForm() {
    if (signForm.wrapper.classList.contains(hidden)) toggleSignFormHidden()
    signForm["login-wrapper"].querySelector('input[type=text]').value = ''
    signForm["login-wrapper"].querySelector('input[type=password]').value = ''
    if (signForm["login-wrapper"].classList.contains(hidden)) signForm["login-wrapper"].classList.toggle(hidden)
    if (!signForm["signup-wrapper"].classList.contains(hidden)) signForm["signup-wrapper"].classList.toggle(hidden)
}

function showSignupForm() {
    if (signForm.wrapper.classList.contains(hidden)) toggleSignFormHidden()
    signForm["signup-name"].value = ''
    signForm["signup-password"].value = ''
    if (!signForm["login-wrapper"].classList.contains(hidden)) signForm["login-wrapper"].classList.toggle(hidden)
    if (signForm["signup-wrapper"].classList.contains(hidden)) signForm["signup-wrapper"].classList.toggle(hidden)
}

function sendSignRequest(isSignIn = true) {
    const name = isSignIn ? signForm['login-name'].value : signForm['signup-name'].value
    if (name.length > 50) {
        alert("Имя будет обрезано до 50 символов")
    }
    const password = isSignIn ? signForm['login-password'].value : signForm['signup-password'].value
    const debtors_names = Array.from(
        Array.from(document.querySelectorAll('#debtors-container > input[type=hidden]')
    ).map(x => x.value))
    if (name === 'Гость') {
        alert('Использование данного имени запрещено')
        return
    }
    if (!isSignIn && submitClicksWithExistingDebtorName == 0 && debtors_names.indexOf(name) !== -1) {
        submitClicksWithExistingDebtorName++
        alert("Вы пытаетесь зарегистрироваться под именем уже существующего должника. Выша учётная запись будет связана с этим должником. Для продолжения нажмите 'Зарегистрироваться' ещё раз")
        return
    }
    fetch('sign', {
        method: isSignIn ? 'POST' : 'PUT',
        headers: {
            'X-CSRFToken': signForm.self.querySelector('input[type="hidden"][name=csrfmiddlewaretoken').value,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            name,
            password,
        })
    })
    .then(r => {
        if (r.ok) {
            return new Promise(resolve => resolve("Вход успешен"))
        } else if (r.status === 400) {
            return new Promise(resolve => {
                resolve(isSignIn ? "Неверный логин или пароль" : "Пользователь с таким именем уже есть")
            })
        } else {
            return r.text()
        }
    })
    .then(message => {
        alert(message)
        location.reload()
    })
}

function signOut() {
    fetch('sign_out', {
        method: 'GET'
    })
    .then(() => location.assign('debt_transactions'))
}

function rjust(str, len, filler) {
    return str.length < len ? filler[0] * (str.length - len) + str : str
}

async function getUserRoles(username = undefined) {
    return fetch(!username ? `get_user_roles` : `get_user_roles?username=${username}`, {
        mode: 'no-cors',
        method: 'GET'
    })
    .then(r => {
        if (r.ok) {
            return r.json()
        } else if (r.status != 403) {
            throw new Error(r.status)
        }
    })
    .catch(e => {
        alert(e)
    })
}

function showAddNewRoleSection() {
    rolesWindow.addRoleSection.classList.remove('hidden')
    rolesWindow.deleteRoleSection.classList.add('hidden')
    rolesWindow.userRolesSection.classList.add('hidden')
}

function showDeleteNewRoleSection() {
    rolesWindow.addRoleSection.classList.add('hidden')
    rolesWindow.deleteRoleSection.classList.remove('hidden')
    rolesWindow.userRolesSection.classList.add('hidden')
}

function RoleComponent(text, onclick) {
    const roleElement = document.createElement('div')
    roleElement.classList.add('role')
    roleElement.innerText = text
    roleElement.onclick = onclick
    return roleElement
}

function assignRole(event) {
    const text = event.target.innerText
    rolesWindow.allRolesWrapper.removeChild(event.target)
    rolesWindow.userRolesWrapper.appendChild(RoleComponent(text, unassignRole))
}
function unassignRole(event) {
    const text = event.target.innerText
    rolesWindow.userRolesWrapper.removeChild(event.target)
    rolesWindow.allRolesWrapper.appendChild(RoleComponent(text, assignRole))
}

function updateDeleteRolesList() {
    const selectElement = rolesWindow.deleteRoleSection.querySelector('select')
    if (selectElement) {
        selectElement.innerHTML = allRoles.map(x => `<option>${x}</option>`).join()
    }
}

async function updateCurrentUserRoles(username = undefined) {
    currentUserRoles = await getUserRoles(username)
    console.log(currentUserRoles)
    rolesWindow.self.querySelector('.user-roles > h4.username').innerText = username ? username :
        document.querySelector('.top-bar .user-card h3').innerText
    const remainingRoles = allRoles.filter(x => currentUserRoles.indexOf(x) === -1)
    rolesWindow.allRolesWrapper.innerHTML = ''
    for (let role of remainingRoles) {
        rolesWindow.allRolesWrapper.appendChild(RoleComponent(role, assignRole))
    }
    rolesWindow.userRolesWrapper.innerHTML = ''
    for (let role of currentUserRoles) {
        rolesWindow.userRolesWrapper.appendChild(RoleComponent(role, unassignRole))
    }
}

async function showUserRoles(username = undefined) {
    updateCurrentUserRoles(username)
    rolesWindow.addRoleSection.classList.add('hidden')
    rolesWindow.deleteRoleSection.classList.add('hidden')
    rolesWindow.userRolesSection.classList.remove('hidden')
}

function saveCurrentUserRoles() {
    const username = rolesWindow.userRolesSection.querySelector('h4.username').innerText
    const originalUser = username === document.querySelector('.user-card h3').innerText
    const roles = Array.from(rolesWindow.userRolesWrapper.children).map(x => x.innerText)
    console.log(username)
    fetch('save_user_roles', {
        method: "POST",
        headers: {
            'X-CSRFToken': rolesWindow.userRolesSection.querySelector('.user-roles input[type="hidden"][name=csrfmiddlewaretoken').value,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            username,
            roles
        })
    }).then(r => {
        if (r.status == 200) {
            alert("Успешно")
            if (originalUser) {
                const sortedInitialRoles = initialUserRoles.toSorted()
                const sortedRolesToSave = roles.toSorted()
                let arraysAreEqual = true
                if (sortedInitialRoles.length === sortedRolesToSave.length) {
                    for (let i = 0; i < sortedInitialRoles.length; i++) {
                        arraysAreEqual = false
                        break
                    }
                } else {
                    arraysAreEqual = false
                }
                if (!arraysAreEqual) {
                    toReload = true
                }
            }
        } else {
            alert(r.status)
        }
    })
}

function showSelectedUserRoles() {
    const selectElement = rolesWindow.self.querySelector('select.other-usernames')
    const username = selectElement.value
    showUserRoles(username)
}

function createNewRole() {
    const roleName = rolesWindow.addRoleSection.querySelector('input[name=role-name]').value.trim()
    if (roleName) {
        if (!testName(roleName)) {
            alert("Название может состоять только из цифр, букв и пробелов")
            return
        }
        if (allRoles.indexOf(roleName) !== -1 || roleName === 'admin') {
            alert("Такая роль уже есть")
            return
        }
        fetch('create_new_role', {
            method: 'PUT',
            headers: {
                'X-CSRFToken': rolesWindow.addRoleSection.querySelector('input[type="hidden"][name=csrfmiddlewaretoken').value,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                'role-name': roleName
            })
        }).then(r => {
            if (r.ok) {
                alert("Успешно")
                allRoles.push(roleName)
                updateDeleteRolesList()
                toReload = true
            } else {
                alert(r.status)
            }
        })
    }
}

function deleteRole() {
    fetch('delete_role', {
        method: 'DELETE',
        headers: {
            'X-CSRFToken': rolesWindow.deleteRoleSection.querySelector('input[type="hidden"][name=csrfmiddlewaretoken').value,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            'role-name': rolesWindow.deleteRoleSection.querySelector('select').value
        })
    }).then(r => {
        if (r.ok) {
            alert('Успешно')
            updateDeleteRolesList()
            updateCurrentUserRoles()
            fetchAllRoles()
            toReload = true
        } else {
            alert(r.status)
        }
    })
}

async function onRoleManageClick() {
    await showUserRoles()
    rolesWindow.wrapper.classList.remove('hidden')
}
function closeRoleManagementWindow() {
    rolesWindow.wrapper.classList.add('hidden')
    if (toReload) {
        location.reload()
    }
}

async function importData() {
    fetch('import', {
        method: 'POST',
        headers: {
            'X-CSRFToken': importExportForm.querySelector('input[type="hidden"][name=csrfmiddlewaretoken').value,
            'Content-Type': 'application/json',
        },
        body: '{}'
    })
    .then(r => {
        if (r.ok) {
            alert("Импорт успешен")
        } else {
            alert(r.status)
        }
    })
}

async function exportData() {
    fetch('export', {
        method: 'POST',
        headers: {
            'X-CSRFToken': importExportForm.querySelector('input[type="hidden"][name=csrfmiddlewaretoken').value,
            'Content-Type': 'application/json',
        },
        body: '{}'
    })
    .then(r => {
        if (r.ok) {
            alert("Экспорт успешен")
        } else {
            alert(r.status)
        }
    })
}

function testName(str) {
    return /^[a-zA-Zа-яА-я0-9\s]+$/.test(str);
}