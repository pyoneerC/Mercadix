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
    },
    'us': {  # Amazon US
        'domain': 'amazon.com',
        'currency': 'USD',
        'country_name': 'United States',
        'exchange_rate_api': None,
        'needs_exchange_rate': False,
        'fixed_usd_rate': 1.0  # USD is the base currency
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
        condition = request.form.get("condition", "all")  # Get the condition parameter with "all" as default

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

        # Validate condition
        if condition not in ["all", "new", "used"]:
            return render_template("error.html", error_message="Invalid condition parameter."), 400

        return redirect(url_for("show_plot", item=item, number_of_pages=number_of_pages, country=country_code, condition=condition))
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


def get_prices(item, number_of_pages, country_code='ar', condition='all'):
    """Fetch the prices of the given item from MercadoLibre/MercadoLivre."""
    cache_key = (item, number_of_pages, country_code, condition)
    if cache_key in prices_cache:
        return prices_cache[cache_key]

    prices_list = []
    product_infos = []  # List to store product information (title, price, URL)
    failed_pages = 0
    domain = COUNTRY_CONFIG[country_code]['domain']
    
    # Construct URL with condition filter if specified
    condition_param = ""
    if condition == "new":
        condition_param = "_ITEM*CONDITION_2230284"  # MercadoLibre ID for New condition
    elif condition == "used":
        condition_param = "_ITEM*CONDITION_2230581"  # MercadoLibre ID for Used condition
    
    for i in range(number_of_pages):
        start_item = i * 50 + 1
        url = f"https://listado.{domain}/{item}{condition_param}_Desde_{start_item}_NoIndex_True"
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Find all product containers
            product_containers = soup.select(".ui-search-result__wrapper")
            
            # If no products are found, stop scraping further pages
            if not product_containers:
                app.logger.info(f"No more results found after {i} pages.")
                break
            
            # Extract product information for each container
            for container in product_containers:
                try:
                    # Get product title
                    title_elem = container.select_one(".ui-search-item__title")
                    title = title_elem.text.strip() if title_elem else "Unknown Product"
                    
                    # Get product price
                    price_elem = container.select_one(".andes-money-amount__fraction")
                    if price_elem:
                        price = int(re.sub(r"\D", "", price_elem.text))
                    else:
                        continue  # Skip products without a price
                    
                    # Get product URL
                    url_elem = container.select_one(".ui-search-link")
                    product_url = url_elem['href'] if url_elem else None
                    
                    # Add price to the list
                    prices_list.append(price)
                    
                    # Add product info to the list
                    product_infos.append({
                        'title': title,
                        'price': price,
                        'url': product_url
                    })
                except Exception as e:
                    app.logger.error(f"Error processing product: {e}")
                    continue
        except requests.exceptions.RequestException as e:
            app.logger.error(f"Error fetching prices: {e}")
            failed_pages += 1

    if not prices_list:
        app.logger.info("No results found for the given search.")
        return None, None, failed_pages, None

    # For Brazilian prices, convert from centavos to reais if needed
    if country_code == 'br' and any(p > 10000 for p in prices_list):
        # Check if the prices seem to be in centavos (very high numbers)
        prices_list = [p / 100 for p in prices_list]
        # Also update product_infos
        for product in product_infos:
            product['price'] = product['price'] / 100

    prices_cache[cache_key] = (prices_list, url, failed_pages, product_infos)
    return prices_list, url, failed_pages, product_infos


def get_amazon_prices(item, number_of_pages, country_code='us'):
    """Fetch the prices of the given item from Amazon."""
    cache_key = (item, number_of_pages, country_code)
    if cache_key in prices_cache:
        return prices_cache[cache_key]

    prices_list = []
    product_infos = []  # List to store product information (title, price, URL)
    failed_pages = 0
    domain = COUNTRY_CONFIG[country_code]['domain']
    
    # Add custom headers to avoid being blocked by Amazon
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }
    
    for i in range(number_of_pages):
        page = i + 1
        # Amazon uses a different URL format for pagination
        url = f"https://www.{domain}/s?k={item.replace(' ', '+')}"
        if page > 1:
            url += f"&page={page}"
            
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Find all product containers in Amazon search results
            product_containers = soup.select('.s-result-item:not(.AdHolder)')
            
            # If no products are found, stop scraping further pages
            if not product_containers:
                app.logger.info(f"No more results found after {i} pages.")
                break
                
            # Process each product container
            for container in product_containers:
                try:
                    # Get product title
                    title_elem = container.select_one('h2 .a-link-normal')
                    title = title_elem.text.strip() if title_elem else "Unknown Product"
                    
                    # Get product price
                    price_elem = container.select_one('.a-price .a-offscreen')
                    if not price_elem:
                        continue  # Skip products without a price
                        
                    price_text = price_elem.text.strip()
                    price_match = re.search(r'[\d,]+\.?\d*', price_text)
                    if not price_match:
                        continue
                        
                    price_str = price_match.group().replace(',', '')
                    try:
                        # Convert to float for decimal handling
                        price = float(price_str)
                        # Convert to cents/pennies for consistency
                        price_cents = int(price * 100)
                    except ValueError:
                        continue
                    
                    # Get product URL
                    url_elem = container.select_one('h2 .a-link-normal')
                    product_url = None
                    if url_elem and 'href' in url_elem.attrs:
                        product_url = 'https://www.amazon.com' + url_elem['href'] if url_elem['href'].startswith('/') else url_elem['href']
                    
                    # Add price to the list
                    prices_list.append(price_cents)
                    
                    # Add product info to the list
                    product_infos.append({
                        'title': title,
                        'price': price_cents,
                        'url': product_url
                    })
                except Exception as e:
                    app.logger.error(f"Error processing Amazon product: {e}")
                    continue
                        
        except requests.exceptions.RequestException as e:
            app.logger.error(f"Error fetching Amazon prices: {e}")
            failed_pages += 1

    if not prices_list:
        app.logger.info("No results found for the given Amazon search.")
        return None, None, failed_pages, None

    # Convert from cents back to dollars for display
    prices_list = [p / 100 for p in prices_list]
    
    # Also update product_infos
    for product in product_infos:
        product['price'] = product['price'] / 100
    
    prices_cache[cache_key] = (prices_list, url, failed_pages, product_infos)
    return prices_list, url, failed_pages, product_infos


def format_x(value, tick_number):
    """Format the x-axis values."""
    return f"{int(value):,}"


def plot_prices(prices_list, item, url, failed_pages, country_code='ar', filter_outliers=True, threshold=3, condition='all'):
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
        0.5 if median_price <= 10 and country_code == 'us'  # For Amazon USD prices
        else 500 if median_price <= 10000
        else 1000 if median_price <= 20000
        else 2000 if median_price <= 50000
        else 3500 if median_price <= 70000
        else 10000
    )

    plt.xlabel(f"Price in {currency}")
    plt.ylabel("Frequency")
    current_date = datetime.date.today().strftime("%d/%m/%Y")
    
    # Determine marketplace name based on country code
    if country_code == 'us':
        marketplace_name = "Amazon"
    else:
        marketplace_name = f"MercadoLi{'v' if country_code == 'br' else 'b'}re"
    
    # Add condition text for title
    condition_text = ""
    if condition == "new":
        condition_text = " - Nuevos"
    elif condition == "used":
        condition_text = " - Usados"
    
    plt.title(
        f'Histogram of {item.replace("-", " ").upper()} prices in {marketplace_name} {country_name}{condition_text} ({current_date})\n'
        f"Number of items indexed: {len(prices_list)} ({request.args.get('number_of_pages')} pages)\n"
        f"URL: {url}\n"
        f"Failed to parse {failed_pages} pages."
    )

    def plot_stat_line(stat_value, color, label, linestyle="solid", linewidth=1):
        plt.axvline(stat_value, color=color, linestyle=linestyle, linewidth=linewidth)
        # For Amazon (USD), don't show USD conversion since it's already in USD
        if country_code == 'us':
            plt.text(
                stat_value + x_pos_offset,
                y_position,
                f"{label}: ${stat_value:.2f} {currency}",
                rotation=90,
                color=color,
            )
        else:
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
    condition = request.args.get("condition", "all")  # Get the condition parameter with "all" as default

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

    # Choose the appropriate price fetching function based on country code
    if country_code == 'us':
        prices_list, url, failed_pages, product_infos = get_amazon_prices(item, number_of_pages, country_code)
    else:
        prices_list, url, failed_pages, product_infos = get_prices(item, number_of_pages, country_code, condition)
        
    if prices_list is None or url is None or product_infos is None:
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
    
    # Get exchange rate - use fixed rate for non-Argentina countries
    if country_config['needs_exchange_rate']:
        exchange_rate_str = get_exchange_rate(country_code)
        exchange_rate = float(exchange_rate_str.replace(f" {currency}", ""))
    else:
        exchange_rate = country_config['fixed_usd_rate']
    
    # Generate the plot for backward compatibility and image download
    plot_base64 = plot_prices(prices_list, item, url, failed_pages, country_code, condition=condition)
    if plot_base64 is None:
        error_message = "Failed to generate plot. Please try again later."
        return render_template("error.html", error_message=error_message), 500

    # Filter outliers for the interactive chart (same logic as in plot_prices)
    threshold = 3
    lower_bound = avg_price - threshold * std_dev
    upper_bound = avg_price + threshold * std_dev
    non_outliers = [p for p in prices_list if lower_bound <= p <= upper_bound]
    outliers = [p for p in prices_list if p < lower_bound or p > upper_bound]
    
    # Find products near the median (±5%)
    median_range_min = median_price * 0.95  # 5% below median
    median_range_max = median_price * 1.05  # 5% above median
    
    # Find products close to median, cheapest, and most expensive
    products_near_median = []
    cheapest_product = None
    most_expensive_product = None
    
    # First scan to find cheapest and most expensive products
    min_price_found = float('inf')
    max_price_found = float('-inf')
    
    for product in product_infos:
        price = product['price']
        
        # Check for cheapest product
        if price < min_price_found:
            min_price_found = price
            cheapest_product = product
            
        # Check for most expensive product
        if price > max_price_found:
            max_price_found = price
            most_expensive_product = product
            
        # Check if product is within ±5% of median
        if median_range_min <= price <= median_range_max:
            # Include price percentage difference from median
            product_copy = product.copy()
            percentage_diff = ((price - median_price) / median_price) * 100
            product_copy['percentage_diff'] = round(percentage_diff, 2)
            products_near_median.append(product_copy)

    # Limit to reasonable number of products to display (at most 10)
    if len(products_near_median) > 10:
        # Sort by how close they are to the median
        products_near_median.sort(key=lambda x: abs(x['percentage_diff']))
        products_near_median = products_near_median[:10]
    
    # Convert to JSON for the frontend
    products_near_median_json = json.dumps(products_near_median)
    cheapest_product_json = json.dumps(cheapest_product) if cheapest_product else None
    most_expensive_product_json = json.dumps(most_expensive_product) if most_expensive_product else None
    
    # Convert prices to JSON for the frontend
    prices_json = json.dumps(non_outliers)
    outliers_json = json.dumps(outliers)

    # Additional template variables for Amazon (US)
    marketplace_name = "Amazon" if country_code == 'us' else f"MercadoLi{'v' if country_code == 'br' else 'b'}re"
    
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
        marketplace_name=marketplace_name,
        condition=condition,
        products_near_median_json=products_near_median_json,
        cheapest_product_json=cheapest_product_json,
        most_expensive_product_json=most_expensive_product_json,
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
