from flask import Flask, request, redirect, url_for, render_template
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib.ticker as ticker
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup
from PIL import Image
import numpy as np
import requests
import datetime
import re
import io
import base64

app = Flask(__name__)
API_URL = "https://dolarapi.com/v1/dolares/blue"


def get_exchange_rate():
    """Fetch the current exchange rate from the API."""
    try:
        response = requests.get(API_URL)
        response.raise_for_status()
        return response.json().get('venta', None)
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error fetching exchange rate: {e}")
        return None


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        item = request.form['item']
        number_of_pages = int(request.form['number_of_pages'])
        return redirect(url_for('show_plot', item=item, number_of_pages=number_of_pages))
    return render_template('index.html')


def get_prices(item, number_of_pages):
    """Fetch the prices of the given item from MercadoLibre."""
    prices_list = []
    image_urls = []

    for i in range(number_of_pages):
        start_item = i * 50 + 1
        url = f'https://listado.mercadolibre.com.ar/{item}_Desde_{start_item}_NoIndex_True'
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            prices = soup.find_all('span', class_='andes-money-amount__fraction')
            prices_list.extend([int(re.sub(r'\D', '', price.text)) for price in prices])

            images = soup.find_all('img', class_='poly-component__picture poly-component__picture--square')
            image_urls.extend([image['src'] for image in images])
        except requests.exceptions.RequestException as e:
            app.logger.error(f"Error fetching prices: {e}")
            return None, None, None

    return prices_list, url, image_urls


def format_x(value, tick_number):
    """Format the x-axis values."""
    return f"{int(value):,}"


def plot_prices(prices_list, item, url, image_urls):
    """Plot a histogram of the prices."""
    venta_dolar = get_exchange_rate()
    if not venta_dolar:
        app.logger.error("Failed to get exchange rate.")
        return None

    plt.figure(figsize=(10, 5))
    plt.hist(prices_list, bins=20, color='lightblue', edgecolor='black')

    plt.ticklabel_format(style='plain', axis='x')
    formatter = ticker.FuncFormatter(format_x)
    plt.gca().xaxis.set_major_formatter(formatter)

    y_position = plt.gca().get_ylim()[1] * 0.05
    median = np.median(prices_list)
    x_pos_offset = 500 if median <= 10000 else 1000 if median <= 20000 \
        else 2000 if median <= 50000 else 3500 if median <= 70000 else 10000

    plt.xlabel('Price in ARS')
    plt.ylabel('Frequency')
    current_date = datetime.date.today().strftime('%d/%m/%Y')
    plt.title(f'Histogram of {item.replace("-", " ").upper()} prices in MercadoLibre Argentina ({current_date})\n'
              f'Number of items indexed: {len(prices_list)} '
              f'({request.args.get("number_of_pages")} pages)\nURL: {url}\n')

    std_dev = np.std(prices_list)
    avg_price = np.mean(prices_list)
    median_price = np.median(prices_list)
    max_price = max(prices_list)
    min_price = min(prices_list)

    def plot_stat_line(stat_value, color, label, linestyle='solid', linewidth=1):
        plt.axvline(stat_value, color=color, linestyle=linestyle, linewidth=linewidth)
        plt.text(stat_value + x_pos_offset, y_position,
                 f'{label}: {int(stat_value):,} ARS ({int(stat_value / venta_dolar):,} USD)', rotation=90, color=color)

    plot_stat_line(median_price, 'red', 'Median')
    plot_stat_line(avg_price, 'purple', 'Avg')
    plot_stat_line(max_price, 'blue', 'Max', linestyle='dashed')
    plot_stat_line(min_price, 'blue', 'Min', linestyle='dashed')
    plot_stat_line(avg_price + std_dev, 'black', 'Std Dev', linestyle='dotted', linewidth=3)
    plot_stat_line(np.percentile(prices_list, 25), 'green', '25th percentile', linestyle='dashed', linewidth=2)

    plt.legend(['Median', 'Avg', 'Max', 'Min', 'Std Dev', '25th percentile'], loc='upper right')

    if image_urls:
        img = Image.open(io.BytesIO(requests.get(image_urls[0]).content))
        ylim = plt.gca().get_ylim()
        ytop = ylim[1] - 0.1 * (ylim[1] - ylim[0])
        imagebox = OffsetImage(img, zoom=0.2)
        ab = AnnotationBbox(imagebox, (max_price, ytop), frameon=False)
        plt.gca().add_artist(ab)

    plt.grid(True)
    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    plt.close()
    buffer.seek(0)

    plot_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    return plot_base64


@app.route('/show_plot')
def show_plot():
    item = request.args.get('item')
    number_of_pages = int(request.args.get('number_of_pages'))
    prices_list, url, image_urls = get_prices(item, number_of_pages)
    if prices_list is None or url is None:
        error_message = "Failed to fetch prices. Please try searching fewer pages or check the item name."
        return render_template('error.html', error_message=error_message), 500

    plot_base64 = plot_prices(prices_list, item, url, image_urls)
    if plot_base64 is None:
        error_message = "Failed to generate plot. Please try again later."
        return render_template('error.html', error_message=error_message), 500

    return render_template('show_plot.html', plot_base64=plot_base64, url=url)


@app.errorhandler(500)
def internal_server_error(error):
    return render_template('error.html', error_message="An unexpected error occurred. Please try again later."), 500


if __name__ == '__main__':
    app.run(debug=True)
