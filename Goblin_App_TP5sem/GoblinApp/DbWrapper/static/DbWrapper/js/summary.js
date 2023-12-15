const startDateInput = document.querySelector('#summary-wrapper form input[type=date][name=start-date]')
const endDateInput = document.querySelector('#summary-wrapper form input[type=date][name=end-date]')

function applySummaryFilter() {
    console.log({
        'startDate': startDateInput.value,
        'endDate': endDateInput.value,
    })
    fetch('summary', {
        method: 'POST',
        headers: {
            'X-CSRFToken': document.querySelector('#summary-wrapper form.filter-form input[type="hidden"][name=csrfmiddlewaretoken').value,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            'startDate': startDateInput.value,
            'endDate': endDateInput.value,
        })
    })
    .then(r => {
        if (!r.ok) {
            alert(r.status)
        }
    })
}

function summarizeDisbalanceData() {
    const dataWrapper = document.querySelector('div.disbalance-transactions > div.data-wrapper')
    const graphWrapper = document.querySelector('div.disbalance-transactions > div.graph-wrapper')
    const budgetElement = document.querySelector('#budget-message')
    const budgetElementWrapper = document.querySelector('.total-budget')
    const rawData = Array.from(dataWrapper.querySelectorAll('div.transaction-data')).map(x => {
        return {
            date: new Date(x.querySelector('input[name=date]').value),
            amount: +x.querySelector('input[name=amount]').value
        }
    })
    rawData.sort(sortingFunction)
    const incomeTransactions = []
    const outcomeTransactions = []
    for (let data of rawData) {
        if (data.amount > 0) {
            const length = incomeTransactions.length
            if (length !== 0) {
                console.log(incomeTransactions[length - 1].date, data.date, incomeTransactions[length - 1].date - data.date)
            }
            if (length === 0 || (incomeTransactions[length - 1].date - data.date) !== 0) {
                incomeTransactions.push(data)
            } else {
                incomeTransactions[length - 1].amount += data.amount
            }
        } else {
            const length = outcomeTransactions.length
            if (length !== 0) {
                console.log(outcomeTransactions[length - 1].date, data.date, outcomeTransactions[length - 1].date - data.date)
            }
            if (length === 0 || (outcomeTransactions[length - 1].date - data.date) !== 0) {
                outcomeTransactions.push({date: data.date, amount: data.amount * -1})
            } else {
                outcomeTransactions[length - 1].amount -= data.amount
            }
        }
    }
    function sortingFunction(a, b) {
        return a.date - b.date
    }
    const plot = Plot.plot({
        grid: true,
        marks: [
            Plot.ruleY([0]),
            Plot.lineY(incomeTransactions, {x: "date", y: "amount", stroke: "green"}),
            Plot.lineY(outcomeTransactions, {x: "date", y: "amount", stroke: "red"})
        ]
    })
    graphWrapper.append(plot)
    const sumBudget = rawData.map(x => x.amount).reduce((partialSum, e) => partialSum + e, 0)
    if (sumBudget > 0) {
        budgetElement.innerText = `Профицит бюджета ${sumBudget}`
        budgetElementWrapper.classList.add("good")
    } else {
        budgetElement.innerText = `Дефицит бюджета ${sumBudget}`
        budgetElementWrapper.classList.add("not-good")
    }
}
summarizeDisbalanceData()