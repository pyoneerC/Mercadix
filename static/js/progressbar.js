   document.getElementById('price-form').onsubmit = function (event) {
    const progressBar = document.getElementById('progress-bar');
    progressBar.style.width = '0%';

    let currentProgress = 0;
    const interval = setInterval(() => {
    if (currentProgress >= 100) {
    clearInterval(interval);
} else {
    currentProgress += 2;
    progressBar.style.width = currentProgress + '%';
}
}, 100);
};