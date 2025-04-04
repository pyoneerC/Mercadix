import base64
import datetime
import io
import os
import re

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from flask import Flask, request, redirect, url_for, render_template, send_file

load_dotenv()

os.environ['MPLCONFIGDIR'] = '/tmp/matplotlib'

app = Flask(__name__)
API_URL = "https://fastapiproject-1-eziw.onrender.com/blue"
prices_cache = {}


@app.template_filter("format_number")
def format_number(value):
    try:
        return "{:,}".format(int(value))
    except (ValueError, TypeError):
        return value


exchange_rate = None


def get_exchange_rate():
    """Fetch the current exchange rate from the API."""
    global exchange_rate
    if exchange_rate is not None:
        return exchange_rate
    try:
        response = requests.get(API_URL)
        response.raise_for_status()
        exchange_rate = response.json().get("venta", None)
        return exchange_rate
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error fetching exchange rate: {e}")
        return None


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        item = request.form["item"]
        number_of_pages = int(request.form["number_of_pages"])
        return redirect(url_for("show_plot", item=item, number_of_pages=number_of_pages))
    return render_template("index.html")


@app.route('/manifest.json')
def serve_manifest():
    return send_file('manifest.json', mimetype='application/json')


@app.route('/sw.js')
def serve_sw():
    return send_file('sw.js', mimetype='application/javascript')


@app.route('/.well-known/assetlinks.json')
def serve_assetlinks():
    return send_file('assetlinks.json', mimetype='application/json')


def get_prices(item, number_of_pages):
    """Fetch the prices of the given item from MercadoLibre."""
    cache_key = (item, number_of_pages)
    if cache_key in prices_cache:
        return prices_cache[cache_key]

    prices_list = []
    for i in range(number_of_pages):
        start_item = i * 50 + 1
        url = f"https://listado.mercadolibre.com.ar/{item}_Desde_{start_item}_NoIndex_True"
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            prices = soup.find_all("span", class_="andes-money-amount__fraction")
            prices_list.extend([int(re.sub(r"\D", "", price.text)) for price in prices])
        except requests.exceptions.RequestException as e:
            app.logger.error(f"Error fetching prices: {e}")
            return None, None

    prices_cache[cache_key] = (prices_list, url)
    return prices_list, url


def format_x(value, tick_number):
    """Format the x-axis values."""
    return f"{int(value):,}"


def plot_prices(prices_list, item, url, filter_outliers=True, threshold=3):
    venta_dolar = get_exchange_rate()
    if not venta_dolar:
        app.logger.error("Failed to get exchange rate.")
        return None
    venta_dolar = float(venta_dolar.replace(" ARS", ""))

    # Compute statistics on the full dataset
    std_dev = np.std(prices_list)
    avg_price = np.mean(prices_list)
    median_price = np.median(prices_list)
    max_price = max(prices_list)
    min_price = min(prices_list)

    # Filter out outliers if the option is enabled
    if filter_outliers:
        lower_bound = avg_price - threshold * std_dev
        upper_bound = avg_price + threshold * std_dev
        non_outliers = [p for p in prices_list if lower_bound <= p <= upper_bound]
        outliers = [p for p in prices_list if p < lower_bound or p > upper_bound]
    else:
        non_outliers = prices_list
        outliers = []

    plt.figure(figsize=(10, 5))
    plt.hist(non_outliers, bins=20, color="lightblue", edgecolor="black")
    plt.ticklabel_format(style="plain", axis="x")
    formatter = ticker.FuncFormatter(format_x)
    plt.gca().xaxis.set_major_formatter(formatter)

    y_position = plt.gca().get_ylim()[1] * 0.05
    # Adjust offset for label text depending on median value
    x_pos_offset = (
        500 if median_price <= 10000
        else 1000 if median_price <= 20000
        else 2000 if median_price <= 50000
        else 3500 if median_price <= 70000
        else 10000
    )

    plt.xlabel("Price in ARS")
    plt.ylabel("Frequency")
    current_date = datetime.date.today().strftime("%d/%m/%Y")
    plt.title(
        f'Histogram of {item.replace("-", " ").upper()} prices in MercadoLibre Argentina ({current_date})\n'
        f"Number of items indexed: {len(prices_list)} ({request.args.get('number_of_pages')} pages)\n"
        f"URL: {url}"
    )

    def plot_stat_line(stat_value, color, label, linestyle="solid", linewidth=1):
        plt.axvline(stat_value, color=color, linestyle=linestyle, linewidth=linewidth)
        plt.text(
            stat_value + x_pos_offset,
            y_position,
            f"{label}: {int(stat_value):,} ARS ({int(stat_value / venta_dolar):,} USD)",
            rotation=90,
            color=color,
        )

    plot_stat_line(median_price, "red", "Median")
    plot_stat_line(avg_price, "purple", "Avg")
    plot_stat_line(max_price, "blue", "Max", linestyle="dashed")
    plot_stat_line(min_price, "blue", "Min", linestyle="dashed")
    plot_stat_line(avg_price + std_dev, "black", "Std Dev", linestyle="dotted", linewidth=3)
    plot_stat_line(np.percentile(prices_list, 25), "green", "25th percentile", linestyle="dashed", linewidth=2)

    plt.legend(["Median", "Avg", "Max", "Min", "Std Dev", "25th percentile"], loc="upper right")
    plt.grid(True)

    # If outliers were detected, annotate the chart with their values.
    if outliers:
        outlier_text = "Outliers: " + ", ".join([f"{p:,}" for p in sorted(outliers)])
        plt.figtext(0.99, 0.01, outlier_text, horizontalalignment='right', fontsize=8, color='red')

    plt.tight_layout()
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    plt.close()
    buffer.seek(0)
    plot_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return plot_base64


@app.route("/show_plot")
def show_plot():
    item = request.args.get("item")
    number_of_pages = int(request.args.get("number_of_pages"))
    prices_list, url = get_prices(item, number_of_pages)
    if prices_list is None or url is None:
        error_message = "Failed to fetch prices. Please try searching fewer pages or check the item name."
        return render_template("error.html", error_message=error_message), 500

    median_price = float(np.median(prices_list))
    avg_price = float(np.mean(prices_list))
    max_price = float(max(prices_list))
    min_price = float(min(prices_list))
    current_date = datetime.date.today().strftime("%d/%m/%Y")

    plot_base64 = plot_prices(prices_list, item, url)
    if plot_base64 is None:
        error_message = "Failed to generate plot. Please try again later."
        return render_template("error.html", error_message=error_message), 500

    return render_template(
        "show_plot.html",
        plot_base64=plot_base64,
        url=url,
        median_price=median_price,
        avg_price=avg_price,
        max_price=max_price,
        min_price=min_price,
        item=item,
        number_of_pages=number_of_pages,
        current_date=current_date,
        avg_price_usd=int(avg_price / float(get_exchange_rate().replace(" ARS", ""))),
        median_price_usd=int(median_price / float(get_exchange_rate().replace(" ARS", ""))),
        max_price_usd=int(max_price / float(get_exchange_rate().replace(" ARS", ""))),
        min_price_usd=int(min_price / float(get_exchange_rate().replace(" ARS", "")),
                          ))


@app.errorhandler(500)
def internal_server_error():
    return (
        render_template(
            "error.html",
            error_message="An unexpected error occurred. Please try again later.",
        ),
        500,
    )


if __name__ == "__main__":
    app.run(debug=True)
