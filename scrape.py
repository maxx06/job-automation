import os
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def setup_driver():
    """Set up and return a configured Chrome webdriver."""
    chrome_options = Options()
    # Uncomment the line below to run headless (no browser window)
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1920,1080")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def search_sei(driver, first_name=None, last_name=None, entity_type=None, position=None):
    """Search for SEI filings with the given parameters."""
    # Navigate to the search page
    driver.get("https://www.ethics.webapps.ms.gov/SearchSEIForm.aspx")
    
    # Add a longer wait time and print a message to debug
    print("Waiting for page to load...")
    try:
        # Wait for the page to load - try a different element that's definitely on the page
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text']"))
        )
        print("Page loaded successfully")
    except Exception as e:
        print(f"Error waiting for page to load: {str(e)}")
        # Take a screenshot to see what's happening
        driver.save_screenshot("debug_screenshot.png")
        print("Saved debug screenshot")
        raise
    
    # Try to find elements with more generic selectors
    print("Filling out search form...")
    try:
        # Find the first name field
        if first_name:
            first_name_field = driver.find_element(By.ID, "ctl00_MainContentPlaceHolder_txtFirstName")
            if not first_name_field:
                # Try alternative selector
                first_name_field = driver.find_element(By.CSS_SELECTOR, "input[id*='FirstName']")
            first_name_field.send_keys(first_name)
            print(f"Entered first name: {first_name}")
        
        # Find the last name field
        if last_name:
            last_name_field = driver.find_element(By.ID, "ctl00_MainContentPlaceHolder_txtLastName")
            if not last_name_field:
                # Try alternative selector
                last_name_field = driver.find_element(By.CSS_SELECTOR, "input[id*='LastName']")
            last_name_field.send_keys(last_name)
            print(f"Entered last name: {last_name}")
        
        # Find and click the search button
        search_button = driver.find_element(By.ID, "ctl00_MainContentPlaceHolder_btnSearchSEI")
        if not search_button:
            # Try alternative selector
            search_button = driver.find_element(By.CSS_SELECTOR, "input[value='Search SEI']")
        search_button.click()
        print("Clicked search button")
    except Exception as e:
        print(f"Error filling out form: {str(e)}")
        driver.save_screenshot("form_error_screenshot.png")
        print("Saved form error screenshot")
        raise
    
    # Wait for results to load with a longer timeout
    print("Waiting for results...")
    time.sleep(5)
    
    # Check if results are present
    results_table = driver.find_elements(By.CSS_SELECTOR, "table.GridView")
    
    if not results_table:
        print("No results found.")
        return []
    
    # Parse results
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    results = []
    
    # Find all rows in the results table
    rows = soup.select("table.GridView tr")
    
    # Skip header row
    for row in rows[1:]:
        cells = row.find_all('td')
        if len(cells) >= 2:
            name = cells[1].text.strip()
            position = cells[2].text.strip() if len(cells) > 2 else ""
            
            # Get the link to view the SEI
            view_link = cells[0].find('a')
            if view_link and 'href' in view_link.attrs:
                link = view_link['href']
                results.append({
                    'name': name,
                    'position': position,
                    'link': link
                })
    
    return results

def download_sei_pdfs(driver, results, output_dir="sei_pdfs"):
    """Download SEI PDFs for each result."""
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    for result in results:
        try:
            # Click on the "View SEI" link
            link_script = result['link']
            if link_script.startswith("javascript:"):
                # Extract the function call and arguments
                script = link_script.replace("javascript:", "")
                driver.execute_script(script)
                
                # Wait for the PDF to load in a new window/tab
                time.sleep(3)
                
                # Switch to the new window/tab
                windows = driver.window_handles
                if len(windows) > 1:
                    driver.switch_to.window(windows[1])
                    
                    # Get the PDF URL
                    pdf_url = driver.current_url
                    
                    # Download the PDF
                    response = requests.get(pdf_url)
                    if response.status_code == 200:
                        # Create a filename based on the person's name
                        filename = f"{result['name'].replace(' ', '_')}_{result['position'].replace(' ', '_')}.pdf"
                        filename = os.path.join(output_dir, filename)
                        
                        with open(filename, 'wb') as f:
                            f.write(response.content)
                        print(f"Downloaded: {filename}")
                    
                    # Close the PDF tab and switch back to the main window
                    driver.close()
                    driver.switch_to.window(windows[0])
        except Exception as e:
            print(f"Error downloading SEI for {result['name']}: {str(e)}")

def main():
    """Main function to run the scraper."""
    driver = setup_driver()
    
    try:
        # Example search - modify parameters as needed
        first_name = "John"
        last_name = "Smith"
        
        print(f"Searching for SEI filings for {first_name} {last_name}...")
        results = search_sei(driver, first_name=first_name, last_name=last_name)
        
        if results:
            print(f"Found {len(results)} results.")
            download_sei_pdfs(driver, results)
        else:
            print("No results found.")
    
    finally:
        # Clean up
        driver.quit()

if __name__ == "__main__":
    main()
