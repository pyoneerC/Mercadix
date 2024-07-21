document.getElementById('price-form').addEventListener('submit', function (event) {
   document.getElementById('spinner').style.display = 'block';
   event.preventDefault();
   setTimeout(function () {
      document.getElementById('price-form').submit();
   }, 100);
});