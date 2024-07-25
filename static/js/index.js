document.getElementById('price-form').addEventListener('submit', function (event) {
   document.getElementById('spinner').style.display = 'block';
   event.preventDefault();
   setTimeout(function () {
      document.getElementById('price-form').submit();
   }, 100);
});

window.addEventListener('load', function() {
   document.getElementById('spinner').style.display = 'none';
});

window.addEventListener('pageshow', function() {
   document.getElementById('spinner').style.display = 'none';
});