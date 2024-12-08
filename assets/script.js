window.addEventListener(
    'beforeunload', () => {
        document.querySelector("#button_clientClose").click()
    }
);

document.documentElement.setAttribute(
    'data-bs-theme', 'light'
)

