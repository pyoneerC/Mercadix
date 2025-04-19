import base64
import datetime
import io
import os
import re
import json

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from flask import Flask, request, redirect, url_for, render_template, send_file, abort

load_dotenv()

os.environ['MPLCONFIGDIR'] = '/tmp/matplotlib'

app = Flask(__name__)
API_URL = "https://fastapiproject-1-eziw.onrender.com/blue"
prices_cache = {}

# Domain configurations
COUNTRY_CONFIG = {
    'ar': {
        'domain': 'mercadolibre.com.ar',
        'currency': 'ARS',
        'country_name': 'Argentina',
        'exchange_rate_api': API_URL,
        'needs_exchange_rate': True
    },
    'br': {
        'domain': 'mercadolivre.com.br',
        'currency': 'BRL',
        'country_name': 'Brasil',
        'exchange_rate_api': None,
        'needs_exchange_rate': False,
        'fixed_usd_rate': 5.0  # Fixed approximate exchange rate for Brazil (1 USD = ~5 BRL)
    }
}

# Default exchange rates (will be updated by API calls)
exchange_rates = {
    'ar': None,
    'br': None
}


@app.template_filter("format_number")
def format_number(value):
    try:
        return "{:,}".format(int(value))
    except (ValueError, TypeError):
        return value


def get_exchange_rate(country_code='ar'):
    """Fetch the current exchange rate from the API."""
    global exchange_rates
    
    country_config = COUNTRY_CONFIG[country_code]
    
    # If we don't need an exchange rate for this country, use the fixed rate
    if not country_config['needs_exchange_rate']:
        return f"{country_config['fixed_usd_rate']} {country_config['currency']}"
    
    # If we already have a cached rate, return it
    if exchange_rates[country_code] is not None:
        return exchange_rates[country_code]
    
    # Otherwise fetch from API (for Argentina)
    try:
        response = requests.get(country_config['exchange_rate_api'])
        response.raise_for_status()
        exchange_rates[country_code] = response.json().get("venta", None)
        return exchange_rates[country_code]
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error fetching exchange rate for {country_code}: {e}")
        # Return a fallback value if the API fails
        return f"1000 {country_config['currency']}"


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        item = request.form["item"].strip()
        number_of_pages = request.form["number_of_pages"].strip()
        country_code = request.form.get("country", "ar")  # Default to Argentina if not specified

        # Validate country code
        if country_code not in COUNTRY_CONFIG:
            return render_template("error.html", error_message="Invalid country code."), 400

        # Validate item
        if not item or not re.match(r"^[a-zA-Z0-9\-\s]+$", item):
            return render_template("error.html", error_message="Invalid item parameter."), 400

        # Validate number_of_pages
        try:
            number_of_pages = int(number_of_pages)
            if number_of_pages < 1 or number_of_pages > 3:
                return render_template("error.html", error_message="Number of pages must be between 1 and 3."), 400
        except ValueError:
            return render_template("error.html", error_message="Number of pages must be a valid integer."), 400

        return redirect(url_for("show_plot", item=item, number_of_pages=number_of_pages, country=country_code))
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


def get_prices(item, number_of_pages, country_code='ar'):
    """Fetch the prices of the given item from MercadoLibre/MercadoLivre."""
    cache_key = (item, number_of_pages, country_code)
    if cache_key in prices_cache:
        return prices_cache[cache_key]

    prices_list = []
    failed_pages = 0
    domain = COUNTRY_CONFIG[country_code]['domain']
    
    for i in range(number_of_pages):
        start_item = i * 50 + 1
        url = f"https://listado.{domain}/{item}_Desde_{start_item}_NoIndex_True"
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            prices = soup.find_all("span", class_="andes-money-amount__fraction")

            # If no prices are found, stop scraping further pages
            if not prices:
                app.logger.info(f"No more results found after {i} pages.")
                break

            prices_list.extend([int(re.sub(r"\D", "", price.text)) for price in prices])
        except requests.exceptions.RequestException as e:
            app.logger.error(f"Error fetching prices: {e}")
            failed_pages += 1

    if not prices_list:
        app.logger.info("No results found for the given search.")
        return None, None, failed_pages

    # For Brazilian prices, convert from centavos to reais if needed
    if country_code == 'br' and any(p > 10000 for p in prices_list):
        # Check if the prices seem to be in centavos (very high numbers)
        prices_list = [p / 100 for p in prices_list]

    prices_cache[cache_key] = (prices_list, url, failed_pages)
    return prices_list, url, failed_pages


def format_x(value, tick_number):
    """Format the x-axis values."""
    return f"{int(value):,}"


def plot_prices(prices_list, item, url, failed_pages, country_code='ar', filter_outliers=True, threshold=3):
    country_config = COUNTRY_CONFIG[country_code]
    currency = country_config['currency']
    country_name = country_config['country_name']
    
    venta_dolar_str = get_exchange_rate(country_code)
    if not venta_dolar_str:
        app.logger.error(f"Failed to get exchange rate for {country_code}.")
        return None
    
    try:
        venta_dolar = float(venta_dolar_str.replace(f" {currency}", ""))
    except (ValueError, TypeError):
        app.logger.error(f"Failed to parse exchange rate: {venta_dolar_str}")
        venta_dolar = country_config.get('fixed_usd_rate', 1000)  # Fallback

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

    plt.xlabel(f"Price in {currency}")
    plt.ylabel("Frequency")
    current_date = datetime.date.today().strftime("%d/%m/%Y")
    plt.title(
        f'Histogram of {item.replace("-", " ").upper()} prices in MercadoLi{"v" if country_code == "br" else "b"}re {country_name} ({current_date})\n'
        f"Number of items indexed: {len(prices_list)} ({request.args.get('number_of_pages')} pages)\n"
        f"URL: {url}\n"
        f"Failed to parse {failed_pages} pages."
    )

    def plot_stat_line(stat_value, color, label, linestyle="solid", linewidth=1):
        plt.axvline(stat_value, color=color, linestyle=linestyle, linewidth=linewidth)
        plt.text(
            stat_value + x_pos_offset,
            y_position,
            f"{label}: {int(stat_value):,} {currency} ({int(stat_value / venta_dolar):,} USD)",
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
    item = request.args.get("item", "").strip()
    number_of_pages = request.args.get("number_of_pages", "").strip()
    country_code = request.args.get("country", "ar")  # Default to Argentina if not specified

    # Validate country code
    if country_code not in COUNTRY_CONFIG:
        return render_template("error.html", error_message="Invalid country code."), 400

    # Validate item
    if not item or not re.match(r"^[a-zA-Z0-9\-\s]+$", item):
        return render_template("error.html", error_message="Invalid item parameter."), 400

    # Validate number_of_pages
    try:
        number_of_pages = int(number_of_pages)
        if number_of_pages < 1 or number_of_pages > 3:
            return render_template("error.html", error_message="Number of pages must be between 1 and 3."), 400
    except ValueError:
        return render_template("error.html", error_message="Number of pages must be a valid integer."), 400

    prices_list, url, failed_pages = get_prices(item, number_of_pages, country_code)
    if prices_list is None or url is None:
        error_message = "Failed to fetch prices. Please try searching fewer pages or check the item name."
        return render_template("error.html", error_message=error_message), 500

    median_price = float(np.median(prices_list))
    avg_price = float(np.mean(prices_list))
    max_price = float(max(prices_list))
    min_price = float(min(prices_list))
    std_dev = float(np.std(prices_list))
    percentile_25 = float(np.percentile(prices_list, 25))
    current_date = datetime.date.today().strftime("%d/%m/%Y")
    
    country_config = COUNTRY_CONFIG[country_code]
    currency = country_config['currency']
    
    # Get exchange rate - use fixed rate for Brazil
    if country_config['needs_exchange_rate']:
        exchange_rate_str = get_exchange_rate(country_code)
        exchange_rate = float(exchange_rate_str.replace(f" {currency}", ""))
    else:
        exchange_rate = country_config['fixed_usd_rate']
    
    # Generate the plot for backward compatibility and image download
    plot_base64 = plot_prices(prices_list, item, url, failed_pages, country_code)
    if plot_base64 is None:
        error_message = "Failed to generate plot. Please try again later."
        return render_template("error.html", error_message=error_message), 500

    # Filter outliers for the interactive chart (same logic as in plot_prices)
    threshold = 3
    lower_bound = avg_price - threshold * std_dev
    upper_bound = avg_price + threshold * std_dev
    non_outliers = [p for p in prices_list if lower_bound <= p <= upper_bound]
    outliers = [p for p in prices_list if p < lower_bound or p > upper_bound]
    
    # Convert prices to JSON for the frontend
    prices_json = json.dumps(non_outliers)
    outliers_json = json.dumps(outliers)

    return render_template(
        "show_plot.html",
        plot_base64=plot_base64,
        prices_json=prices_json,
        outliers_json=outliers_json,
        url=url,
        median_price=median_price,
        avg_price=avg_price,
        max_price=max_price,
        min_price=min_price,
        std_dev=std_dev,
        percentile_25=percentile_25,
        item=item,
        number_of_pages=number_of_pages,
        current_date=current_date,
        exchange_rate=exchange_rate,
        avg_price_usd=int(avg_price / exchange_rate),
        median_price_usd=int(median_price / exchange_rate),
        max_price_usd=int(max_price / exchange_rate),
        min_price_usd=int(min_price / exchange_rate),
        failed_pages=failed_pages,
        country_code=country_code,
        currency=country_config['currency'],
        country_name=country_config['country_name'],
    )


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
