# MercadoLibre Price Chart

## Descripción

Este proyecto es una aplicación web desarrollada en Flask que permite a los usuarios consultar precios de productos en MercadoLibre y visualizar un histograma de precios. Utiliza la API de [DolarAPI](https://dolarapi.com/) para obtener el tipo de cambio actual y presenta los datos en gráficos generados con Matplotlib.

> [!NOTE]
> [Disponible en todos los navegadores web!](mercado-libre-price-chart.vercel.app)

![Imagen de la Aplicación](media/price_histogram.png)
![GIF de la Aplicación](media/demonstration.gif)

> [!TIP]
> Puedes poner cualquier artículo que desees en la barra de búsqueda!

## Funcionalidades

- **Consulta de Precios**: Permite al usuario ingresar el nombre de un producto y el número de páginas para consultar en MercadoLibre.
- **Generación de Gráfico**: Visualiza un histograma de los precios obtenidos, mostrando estadísticas relevantes como el promedio, la mediana, el máximo, el mínimo, y la desviación estándar.
- **Visualización de Imágenes**: Incluye una imagen representativa del primer resultado de la búsqueda en el gráfico.
- **Interfaz de Usuario**: Ofrece una interfaz simple para introducir los parámetros de búsqueda y mostrar los resultados.

> [!TIP]
> Puedes descargar la imagen del gráfico y guardarla haciendo click en el botón "Download Image".

## Instalación

Para ejecutar este proyecto en tu máquina local, sigue estos pasos:

1. **Clonar el Repositorio**:
   ```bash
   git clone https://github.com/tu_usuario/mercado-libre-price-chart.git
    ```
   
2. **Instalar Dependencias**:

Asegúrate de tener Python y pip instalados en tu sistema. Luego, instala las dependencias del proyecto con el siguiente comando:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configurar Variables de Entorno**:

Crea un archivo `.env` en el directorio raíz del proyecto y agrega las siguientes variables:
   ```env
   FLASK_APP=app.py
   FLASK_ENV=development
   FLASK_DEBUG=0
   ```

4. **Ejecutar la Aplicación**:

Finalmente, ejecuta la aplicación con el siguiente comando:
   ```bash
   flask run
   ```

La aplicación estará disponible en `http://127.0.0.1:5000`

> [!WARNING]
> Cuidado con ingresar un número muy alto de páginas, ya que puede llevar varios segundos e incluso que la aplicación falle si tu internet es lento.


> [!CAUTION]
> Intenta ser lo más específico posible en tu búsqueda para obtener resultados más precisos. Puedes ver de donde se obtienen los datos clickeando el boton que dice "View on MercadoLibre".


![Histograma de Precios](media/chocolate_histogram.png)

## Tecnologías Utilizadas

- **Flask**: Framework web para Python.
- **Matplotlib**: Librería para la creación de gráficos.
- **BeautifulSoup**: Biblioteca para el análisis de HTML y extracción de datos.
- **PIL (Pillow)**: Librería para el manejo de imágenes.
- **Requests**: Biblioteca para hacer solicitudes HTTP.
- **NumPy**: Biblioteca para el cálculo numérico en Python.

## Contribuciones

Este proyecto es de código abierto y las contribuciones son bienvenidas. 

## Licencia

Distribuido bajo la licencia MIT. Haz clic [aquí](LICENSE) para más información.