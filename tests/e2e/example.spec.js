const { test, expect } = require('@playwright/test');

test.describe('Mercadix Application End-to-End Tests', () => {
  // Test home page rendering
  test('home page loads correctly', async ({ page }) => {
    await page.goto('/');
    
    // Check page title
    await expect(page).toHaveTitle(/Mercado Libre Price Chart/);
    
    // Check form elements exist
    await expect(page.locator('#price-form')).toBeVisible();
    await expect(page.locator('#item')).toBeVisible();
    await expect(page.locator('#number_of_pages')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  // Test form submission with valid input
  test('form submits with valid inputs and shows results', async ({ page }) => {
    // Mock exchange rate API response
    await page.route('https://fastapiproject-1-eziw.onrender.com/blue', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ venta: '400.0 ARS' }),
      });
    });

    // Mock MercadoLibre response
    await page.route('https://listado.mercadolibre.com.ar/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'text/html',
        body: `
          <html>
            <body>
              <span class="andes-money-amount__fraction">100000</span>
              <span class="andes-money-amount__fraction">150000</span>
              <span class="andes-money-amount__fraction">200000</span>
            </body>
          </html>
        `,
      });
    });

    // Navigate to home page
    await page.goto('/');
    
    // Fill form inputs
    await page.locator('#item').fill('iphone');
    await page.locator('#number_of_pages').fill('1');
    
    // Submit form
    await page.locator('button[type="submit"]').click();
    
    // Wait for results page to load with plot
    await expect(page.locator('.plot-container')).toBeVisible({ timeout: 10000 });
    
    // Check that the plot and statistics are displayed
    await expect(page.locator('img.plot')).toBeVisible();
    await expect(page.locator('.statistics')).toBeVisible();
  });

  // Test form validation
  test('form validation prevents invalid input submission', async ({ page }) => {
    await page.goto('/');
    
    // Test invalid item (with special characters)
    await page.locator('#item').fill('invalid@item');
    await page.locator('#number_of_pages').fill('1');
    await page.locator('button[type="submit"]').click();
    
    // Should show error page
    await expect(page.locator('body')).toContainText('Invalid item parameter');
    
    // Go back to home page and test invalid page number
    await page.goto('/');
    await page.locator('#item').fill('iphone');
    await page.locator('#number_of_pages').fill('5'); // Above max limit
    await page.locator('button[type="submit"]').click();
    
    // Should show error page
    await expect(page.locator('body')).toContainText('Number of pages must be between 1 and 3');
  });

  // Test download functionality
  test('plot image can be downloaded', async ({ page }) => {
    // Mock necessary API responses
    await page.route('https://fastapiproject-1-eziw.onrender.com/blue', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ venta: '400.0 ARS' }),
      });
    });

    await page.route('https://listado.mercadolibre.com.ar/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'text/html',
        body: `<html><body><span class="andes-money-amount__fraction">100000</span></body></html>`,
      });
    });

    // Navigate directly to results page with query parameters
    await page.goto('/show_plot?item=iphone&number_of_pages=1');
    
    // Check if the download button exists
    const downloadButton = page.locator('#download-button');
    await expect(downloadButton).toBeVisible();
    
    // Click would trigger download in a real browser, we just verify the button has an href attribute
    const hrefValue = await downloadButton.getAttribute('href');
    expect(hrefValue).toBeTruthy();
    expect(hrefValue).toContain('data:image/png;base64');
  });

  // Test responsive design
  test('application is responsive on mobile devices', async ({ page }) => {
    // Set viewport to mobile size
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Navigate to home page
    await page.goto('/');
    
    // Check that elements are still visible and properly sized
    const form = page.locator('#price-form');
    await expect(form).toBeVisible();
    
    // Form should take up most of the width on mobile
    const formBoundingBox = await form.boundingBox();
    expect(formBoundingBox.width).toBeGreaterThan(300);
    expect(formBoundingBox.width).toBeLessThan(375);
  });

  // Test error handling
  test('application handles API errors gracefully', async ({ page }) => {
    // Mock exchange rate API to return an error
    await page.route('https://fastapiproject-1-eziw.onrender.com/blue', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal server error' }),
      });
    });

    // Navigate directly to results page
    await page.goto('/show_plot?item=iphone&number_of_pages=1');
    
    // Should show error page
    await expect(page.locator('body')).toContainText('Failed to');
  });
});
