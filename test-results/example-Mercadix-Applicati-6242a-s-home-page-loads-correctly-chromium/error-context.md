# Test info

- Name: Mercadix Application End-to-End Tests >> home page loads correctly
- Location: /workspaces/Mercadix/tests/e2e/example.spec.js:5:3

# Error details

```
Error: Timed out 5000ms waiting for expect(locator).toHaveTitle(expected)

Locator: locator(':root')
Expected pattern: /Mercado Libre Price Chart/
Received string:  "Mercadix"
Call log:
  - expect.toHaveTitle with timeout 5000ms
  - waiting for locator(':root')
    6 × locator resolved to <html lang="en">…</html>
      - unexpected value "Mercadix"

    at /workspaces/Mercadix/tests/e2e/example.spec.js:9:24
```

# Page snapshot

```yaml
- heading "Mercadix" [level=1]
- text: "Artículo a buscar:"
- textbox "Artículo a buscar:"
- text: "Cantidad de páginas a escanear:"
- spinbutton "Cantidad de páginas a escanear:": "1"
- button "Generar Histograma"
- paragraph:
  - text: Escribí el nombre de un producto y
  - link "Mercadix te muestra en segundos":
    - /url: https://mercadix.maxcomperatore.com/show_plot?item=ps4&number_of_pages=1
  - text: cuánto se está pagando por eso en Mercado Libre. Vas a ver un gráfico con los precios más bajos, más altos y la media, para saber si vale la pena o no comprarlo.
- contentinfo:
  - paragraph: © 2024 PyoneerC — No afiliado a Mercado Libre.
  - link "GitHub":
    - /url: https://github.com/pyoneerC/Mercadix
  - link "Android App":
    - /url: https://pyoneerc1.itch.io/mercadix
  - link "Cafecito":
    - /url: https://cafecito.app/maxcomperatore
  - link "maxcomperatore.com":
    - /url: https://maxcomperatore.com
```

# Test source

```ts
   1 | const { test, expect } = require('@playwright/test');
   2 |
   3 | test.describe('Mercadix Application End-to-End Tests', () => {
   4 |   // Test home page rendering
   5 |   test('home page loads correctly', async ({ page }) => {
   6 |     await page.goto('/');
   7 |     
   8 |     // Check page title
>  9 |     await expect(page).toHaveTitle(/Mercado Libre Price Chart/);
     |                        ^ Error: Timed out 5000ms waiting for expect(locator).toHaveTitle(expected)
   10 |     
   11 |     // Check form elements exist
   12 |     await expect(page.locator('#price-form')).toBeVisible();
   13 |     await expect(page.locator('#item')).toBeVisible();
   14 |     await expect(page.locator('#number_of_pages')).toBeVisible();
   15 |     await expect(page.locator('button[type="submit"]')).toBeVisible();
   16 |   });
   17 |
   18 |   // Test form submission with valid input
   19 |   test('form submits with valid inputs and shows results', async ({ page }) => {
   20 |     // Mock exchange rate API response
   21 |     await page.route('https://fastapiproject-1-eziw.onrender.com/blue', async (route) => {
   22 |       await route.fulfill({
   23 |         status: 200,
   24 |         contentType: 'application/json',
   25 |         body: JSON.stringify({ venta: '400.0 ARS' }),
   26 |       });
   27 |     });
   28 |
   29 |     // Mock MercadoLibre response
   30 |     await page.route('https://listado.mercadolibre.com.ar/**', async (route) => {
   31 |       await route.fulfill({
   32 |         status: 200,
   33 |         contentType: 'text/html',
   34 |         body: `
   35 |           <html>
   36 |             <body>
   37 |               <span class="andes-money-amount__fraction">100000</span>
   38 |               <span class="andes-money-amount__fraction">150000</span>
   39 |               <span class="andes-money-amount__fraction">200000</span>
   40 |             </body>
   41 |           </html>
   42 |         `,
   43 |       });
   44 |     });
   45 |
   46 |     // Navigate to home page
   47 |     await page.goto('/');
   48 |     
   49 |     // Fill form inputs
   50 |     await page.locator('#item').fill('iphone');
   51 |     await page.locator('#number_of_pages').fill('1');
   52 |     
   53 |     // Submit form
   54 |     await page.locator('button[type="submit"]').click();
   55 |     
   56 |     // Wait for results page to load with plot
   57 |     await expect(page.locator('.plot-container')).toBeVisible({ timeout: 10000 });
   58 |     
   59 |     // Check that the plot and statistics are displayed
   60 |     await expect(page.locator('img.plot')).toBeVisible();
   61 |     await expect(page.locator('.statistics')).toBeVisible();
   62 |   });
   63 |
   64 |   // Test form validation
   65 |   test('form validation prevents invalid input submission', async ({ page }) => {
   66 |     await page.goto('/');
   67 |     
   68 |     // Test invalid item (with special characters)
   69 |     await page.locator('#item').fill('invalid@item');
   70 |     await page.locator('#number_of_pages').fill('1');
   71 |     await page.locator('button[type="submit"]').click();
   72 |     
   73 |     // Should show error page
   74 |     await expect(page.locator('body')).toContainText('Invalid item parameter');
   75 |     
   76 |     // Go back to home page and test invalid page number
   77 |     await page.goto('/');
   78 |     await page.locator('#item').fill('iphone');
   79 |     await page.locator('#number_of_pages').fill('5'); // Above max limit
   80 |     await page.locator('button[type="submit"]').click();
   81 |     
   82 |     // Should show error page
   83 |     await expect(page.locator('body')).toContainText('Number of pages must be between 1 and 3');
   84 |   });
   85 |
   86 |   // Test download functionality
   87 |   test('plot image can be downloaded', async ({ page }) => {
   88 |     // Mock necessary API responses
   89 |     await page.route('https://fastapiproject-1-eziw.onrender.com/blue', async (route) => {
   90 |       await route.fulfill({
   91 |         status: 200,
   92 |         contentType: 'application/json',
   93 |         body: JSON.stringify({ venta: '400.0 ARS' }),
   94 |       });
   95 |     });
   96 |
   97 |     await page.route('https://listado.mercadolibre.com.ar/**', async (route) => {
   98 |       await route.fulfill({
   99 |         status: 200,
  100 |         contentType: 'text/html',
  101 |         body: `<html><body><span class="andes-money-amount__fraction">100000</span></body></html>`,
  102 |       });
  103 |     });
  104 |
  105 |     // Navigate directly to results page with query parameters
  106 |     await page.goto('/show_plot?item=iphone&number_of_pages=1');
  107 |     
  108 |     // Check if the download button exists
  109 |     const downloadButton = page.locator('#download-button');
```