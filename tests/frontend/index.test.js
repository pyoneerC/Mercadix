/**
 * @jest-environment jsdom
 */

// Mock DOM elements for testing
document.body.innerHTML = `
  <form id="price-form">
    <input type="text" id="item" name="item" value="iphone">
    <input type="number" id="number_of_pages" name="number_of_pages" value="1">
    <button type="submit">Search</button>
  </form>
  <div id="spinner" style="display: none;"></div>
`;

// Import the script to test
require('../../static/js/index.js');

describe('Form submission functionality', () => {
  // Save original submit function
  const originalSubmit = HTMLFormElement.prototype.submit;
  
  beforeEach(() => {
    // Mock the form's submit method
    HTMLFormElement.prototype.submit = jest.fn();
    // Reset spinner to hidden before each test
    document.getElementById('spinner').style.display = 'none';
  });
  
  afterEach(() => {
    // Restore original submit function
    HTMLFormElement.prototype.submit = originalSubmit;
    jest.clearAllMocks();
    jest.useRealTimers();
  });
  
  test('form submission displays spinner and submits the form', () => {
    // Mock setTimeout
    jest.useFakeTimers();
    
    // Trigger form submission
    const form = document.getElementById('price-form');
    form.dispatchEvent(new Event('submit'));
    
    // Check spinner is displayed immediately
    expect(document.getElementById('spinner').style.display).toBe('block');
    
    // Check form not submitted yet
    expect(HTMLFormElement.prototype.submit).not.toHaveBeenCalled();
    
    // Fast-forward timers
    jest.runAllTimers();
    
    // Check form submitted after timeout
    expect(HTMLFormElement.prototype.submit).toHaveBeenCalledTimes(1);
  });
});

describe('Page load events', () => {
  test('spinner is hidden on page load', () => {
    // Set spinner to visible
    document.getElementById('spinner').style.display = 'block';
    
    // Trigger load event
    window.dispatchEvent(new Event('load'));
    
    // Check spinner is hidden
    expect(document.getElementById('spinner').style.display).toBe('none');
  });
  
  test('spinner is hidden on pageshow event', () => {
    // Set spinner to visible
    document.getElementById('spinner').style.display = 'block';
    
    // Trigger pageshow event
    window.dispatchEvent(new Event('pageshow'));
    
    // Check spinner is hidden
    expect(document.getElementById('spinner').style.display).toBe('none');
  });
});

describe('Form validation', () => {
  test('form has required inputs', () => {
    const form = document.getElementById('price-form');
    const itemInput = document.getElementById('item');
    const pagesInput = document.getElementById('number_of_pages');
    
    expect(form).not.toBeNull();
    expect(itemInput).not.toBeNull();
    expect(pagesInput).not.toBeNull();
    
    // Verify default values
    expect(itemInput.value).toBe('iphone');
    expect(pagesInput.value).toBe('1');
  });
});