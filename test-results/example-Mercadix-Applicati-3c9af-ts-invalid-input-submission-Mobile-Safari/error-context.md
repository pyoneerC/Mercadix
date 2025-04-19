# Test info

- Name: Mercadix Application End-to-End Tests >> form validation prevents invalid input submission
- Location: /workspaces/Mercadix/tests/e2e/example.spec.js:65:3

# Error details

```
Error: browserType.launch: 
╔══════════════════════════════════════════════════════╗
║ Host system is missing dependencies to run browsers. ║
║ Missing libraries:                                   ║
║     libwoff2dec.so.1.0.2                             ║
║     libopus.so.0                                     ║
║     libwebpdemux.so.2                                ║
║     libharfbuzz-icu.so.0                             ║
║     libwebpmux.so.3                                  ║
║     libenchant-2.so.2                                ║
║     libhyphen.so.0                                   ║
║     libEGL.so.1                                      ║
║     libGLX.so.0                                      ║
║     libgudev-1.0.so.0                                ║
║     libevdev.so.2                                    ║
║     libGLESv2.so.2                                   ║
║     libx264.so                                       ║
╚══════════════════════════════════════════════════════╝
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
   9 |     await expect(page).toHaveTitle(/Mercado Libre Price Chart/);
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
>  65 |   test('form validation prevents invalid input submission', async ({ page }) => {
      |   ^ Error: browserType.launch: 
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
  110 |     await expect(downloadButton).toBeVisible();
  111 |     
  112 |     // Click would trigger download in a real browser, we just verify the button has an href attribute
  113 |     const hrefValue = await downloadButton.getAttribute('href');
  114 |     expect(hrefValue).toBeTruthy();
  115 |     expect(hrefValue).toContain('data:image/png;base64');
  116 |   });
  117 |
  118 |   // Test responsive design
  119 |   test('application is responsive on mobile devices', async ({ page }) => {
  120 |     // Set viewport to mobile size
  121 |     await page.setViewportSize({ width: 375, height: 667 });
  122 |     
  123 |     // Navigate to home page
  124 |     await page.goto('/');
  125 |     
  126 |     // Check that elements are still visible and properly sized
  127 |     const form = page.locator('#price-form');
  128 |     await expect(form).toBeVisible();
  129 |     
  130 |     // Form should take up most of the width on mobile
  131 |     const formBoundingBox = await form.boundingBox();
  132 |     expect(formBoundingBox.width).toBeGreaterThan(300);
  133 |     expect(formBoundingBox.width).toBeLessThan(375);
  134 |   });
  135 |
  136 |   // Test error handling
  137 |   test('application handles API errors gracefully', async ({ page }) => {
  138 |     // Mock exchange rate API to return an error
  139 |     await page.route('https://fastapiproject-1-eziw.onrender.com/blue', async (route) => {
  140 |       await route.fulfill({
  141 |         status: 500,
  142 |         contentType: 'application/json',
  143 |         body: JSON.stringify({ error: 'Internal server error' }),
  144 |       });
  145 |     });
  146 |
  147 |     // Navigate directly to results page
  148 |     await page.goto('/show_plot?item=iphone&number_of_pages=1');
  149 |     
  150 |     // Should show error page
  151 |     await expect(page.locator('body')).toContainText('Failed to');
  152 |   });
  153 | });
  154 |
```