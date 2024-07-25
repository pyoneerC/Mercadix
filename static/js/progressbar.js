  document.getElementById('price-form').onsubmit = function(event) {
    const numberOfPages = parseInt(document.getElementById('number_of_pages').value);
    const totalSeconds = numberOfPages * 2;
    const progressBar = document.getElementById('progress-bar');


    progressBar.style.width = '0%';
    progressBar.textContent = totalSeconds + 's';

    let currentProgress = 0;
    let secondsRemaining = totalSeconds;
    const increment = 100 / totalSeconds;

    const interval = setInterval(() => {
      if (currentProgress >= 100) {
        clearInterval(interval);
        progressBar.textContent = '0s';
      } else {
        currentProgress += increment;
        progressBar.style.width = currentProgress + '%';
        secondsRemaining -= 1;
        progressBar.textContent = secondsRemaining + 's';
      }
    }, 1000);
  }