window.addEventListener(
    'beforeunload', () => {
        document.querySelector("#notifyClose").click()
    }
);

document.documentElement.setAttribute(
    'data-bs-theme', 'light'
)

