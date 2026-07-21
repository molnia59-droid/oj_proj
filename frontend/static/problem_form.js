const form = document.querySelector("[data-problem-form]")

if (form) {
    const list = document.querySelector("#test-case-list")
    const template = document.querySelector("#test-case-template")
    const addButton = document.querySelector("#add-test-button")
    const scoreSummary = document.querySelector("#score-summary")

    // return every current testcase block
    function testCards() {
        return [...list.querySelectorAll(".test-case-card")]
    }

    // return the selected automatic or manual score mode
    function scoreMode() {
        return form.querySelector(
            "input[name='score_mode']:checked"
        ).value
    }

    // distribute one hundred points without losing the remainder
    function automaticScores(count) {
        const base = Math.floor(100 / count)
        const remainder = 100 % count

        return Array.from(
            { length: count },
            (_, index) => base + (index < remainder ? 1 : 0),
        )
    }

    // update numbering and generate missing case ids
    function updateNumbers() {
        testCards().forEach((card, index) => {
            card.querySelector("[data-test-number]").textContent = index + 1

            const caseInput = card.querySelector("input[name='test_case_id']")

            if (!caseInput.value.trim()) {
                caseInput.value = `case_${String(index + 1).padStart(2, "0")}`
            }
        })
    }

    // apply automatic scores or show the current manual total
    function updateScores() {
        const cards = testCards()
        const inputs = cards.map(
            card => card.querySelector(".test-score-input"),
        )

        if (scoreMode() === "auto") {
            const scores = automaticScores(cards.length)

            inputs.forEach((input, index) => {
                input.value = scores[index]
                input.readOnly = true
            })
        } else {
            inputs.forEach(input => {
                input.readOnly = false
            })
        }

        const total = inputs.reduce(
            (sum, input) => sum + Number(input.value || 0),
            0,
        )
        scoreSummary.textContent = `Total: ${total}`
    }

    // connect remove buttons to testcase cards
    function connectRemoveButtons() {
        testCards().forEach(card => {
            const button = card.querySelector("[data-remove-test]")

            button.onclick = () => {
                if (testCards().length === 1) {
                    return
                }

                card.remove()
                updateNumbers()
                updateScores()
            }
        })
    }

    // add one new testcase from the html template
    addButton.addEventListener("click", () => {
        list.append(template.content.cloneNode(true))
        updateNumbers()
        connectRemoveButtons()
        updateScores()
    })

    // changing score mode immediately updates all score fields
    form.querySelectorAll("input[name='score_mode']").forEach(input => {
        input.addEventListener("change", updateScores)
    })

    // manual score edits update the visible total
    list.addEventListener("input", event => {
        if (event.target.matches(".test-score-input")) {
            updateScores()
        }
    })

    // prevent manual submission unless the score total equals one hundred
    form.addEventListener("submit", event => {
        if (scoreMode() !== "manual") {
            return
        }

        const total = testCards().reduce(
            (sum, card) => sum + Number(
                card.querySelector(".test-score-input").value || 0,
            ),
            0,
        )

        if (total !== 100) {
            event.preventDefault()
            alert("Test scores must total 100")
        }
    })

    updateNumbers()
    connectRemoveButtons()
    updateScores()
}
