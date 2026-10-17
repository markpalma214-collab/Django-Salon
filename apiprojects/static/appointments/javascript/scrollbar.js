function smoothScrollTo(targetY, duration = 800) {
    const startY = window.scrollY;
    const distance = targetY - startY;
    const startTime = performance.now();

    function easeInOut(t) {
        return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
    }

    function step(now) {
        const progress = Math.min((now - startTime) / duration, 1);
        window.scrollTo({
            top: startY + distance * easeInOut(progress),
            behavior: "instant"
        });
        if (progress < 1) requestAnimationFrame(step);
    }

    requestAnimationFrame(step);
}

document.querySelectorAll('nav a[href^="#"]').forEach(function (link) {
    link.addEventListener("click", function (event) {
        const id = link.getAttribute("href");
        const target = id === "#" ? null : document.querySelector(id);

        if (id !== "#" && !target) return; // section doesn't exist yet

        event.preventDefault();
        const y = target ? target.getBoundingClientRect().top + window.scrollY : 0;
        smoothScrollTo(y);
    });
});