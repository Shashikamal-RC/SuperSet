#!/usr/bin/env python3
"""
Superset Job Posting Automation

This module provides an automated process for posting job profiles on the Superset platform.
It uses Selenium WebDriver to interact with the web interface.
"""

import logging
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, Union, Any

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
    ElementClickInterceptedException
)
from webdriver_manager.chrome import ChromeDriverManager


# Configure logging
logger = logging.getLogger("superset_automator")
logger.setLevel(logging.INFO)

# Create file handler
file_handler = logging.FileHandler("automation.log")
file_handler.setLevel(logging.INFO)

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Create formatter and add it to the handlers
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)


@dataclass
class JobData:
    """Data class to hold job posting information."""
    company_name: str
    job_title: str
    location: str = "Pune"
    min_salary: int = 1000000
    max_salary: int = 1500000
    job_description: str = ""
    job_function: str = ''
    salary_breakup: str = ""
    posted_by: str = ""
    timestamp: str = ""
    is_ai_generated: bool = False


class ElementInteraction:
    """Helper class for interacting with web elements."""
    
    def __init__(self, driver: WebDriver, wait: WebDriverWait):
        self.driver = driver
        self.wait = wait

    def safe_click(self, element: WebElement) -> bool:
        """Safely click an element, handling various exceptions."""
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.5)
            element.click()
            return True
        except ElementClickInterceptedException:
            try:
                self.driver.execute_script("arguments[0].click();", element)
                return True
            except Exception as e:
                logger.error(f"Failed to click element with JS: {e}")
                return False
        except Exception as e:
            logger.error(f"Failed to click element: {e}")
            return False

    def safe_input(self, element: WebElement, value: str) -> bool:
        """Safely enter text into an input field."""
        try:
            element.clear()
            element.send_keys(value)
            return True
        except Exception as e:
            logger.error(f"Failed to input text: {e}")
            return False

    def js_input(self, element: WebElement, value: Union[str, int]) -> bool:
        """Use JavaScript to set an input value."""
        try:
            self.driver.execute_script(
                "arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input'));", 
                element, 
                value
            )
            return True
        except Exception as e:
            logger.error(f"Failed to set input value with JS: {e}")
            return False


class SupersetAutomator:
    """
    Automates job posting on the Superset platform.
    
    This class handles login, navigation, and form filling to automate
    the job posting process on the Superset platform.
    """

    def __init__(self, url: str, username: str, password: str, headless: bool = False):
        """
        Initialize the Superset automator.
        
        Args:
            url: The URL of the Superset platform
            username: The username for login
            password: The password for login
            headless: Whether to run the browser in headless mode
        """
        self.url = url
        self.username = username
        self.password = password
        self.headless = headless
        self.driver = None
        self.wait = None
        self.element_interaction = None

    def setup_driver(self) -> None:
        """Set up the WebDriver for browser automation."""
        try:
            logger.info("Setting up WebDriver...")
            options = webdriver.ChromeOptions()
            if self.headless:
                options.add_argument("--headless=new")  # Modern headless mode
            options.add_argument("--disable-gpu")
            
            self.driver = webdriver.Chrome(
                service=ChromeService(ChromeDriverManager().install()), 
                options=options
            )
            
            self.wait = WebDriverWait(self.driver, 15)
            self.element_interaction = ElementInteraction(self.driver, self.wait)
            logger.info("WebDriver setup completed successfully")
        except WebDriverException as e:
            logger.error(f"WebDriver setup failed: {e}")
            raise

    def login(self) -> bool:
        """
        Attempt to login to the Superset platform.
        
        Returns:
            bool: True if login successful, False otherwise
        """
        try:
            logger.info(f"Navigating to {self.url}")
            self.driver.get(self.url)

            logger.info("Waiting for email and password fields to be clickable...")
            email_input = self.wait.until(EC.element_to_be_clickable((By.ID, "email")))
            password_input = self.wait.until(EC.element_to_be_clickable((By.ID, "password")))

            logger.info("Entering credentials...")
            self.element_interaction.safe_input(email_input, self.username)
            self.element_interaction.safe_input(password_input, self.password)

            # Try multiple ways to locate the submit button
            login_button = self._find_login_button()
            if not login_button:
                logger.error("Login button not found.")
                return False

            self.element_interaction.safe_click(login_button)
            logger.info("Clicked login button. Waiting for post-login element...")

            # Check for login errors
            if self._check_for_login_errors():
                return False

            # Wait for a post-login element to confirm successful login
            try:
                self.wait.until(EC.presence_of_element_located((By.ID, "ui_container")))
                logger.info("Login successful! UI container found.")
                return True
            except TimeoutException:
                logger.error("Login seems to have failed - UI container not found.")
                return False

        except TimeoutException:
            logger.error("Timed out waiting for page elements during login.")
            return False
        except NoSuchElementException as e:
            logger.error(f"Missing expected element during login: {e}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error during login: {e}")
            return False

    def _find_login_button(self) -> Optional[WebElement]:
        """Find the login button using multiple selectors."""
        try:
            return self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @value='Login']"))
            )
        except TimeoutException:
            logger.warning("Submit button not found with type='submit', trying alternative selectors...")
            try:
                return self.driver.find_element(By.XPATH, "//button[contains(text(),'Login')]")
            except NoSuchElementException:
                try:
                    return self.driver.find_element(By.CSS_SELECTOR, "button")
                except NoSuchElementException:
                    return None

    def _check_for_login_errors(self) -> bool:
        """
        Check for login error messages.
        
        Returns:
            bool: True if errors found, False otherwise
        """
        logger.info("Checking for login errors...")
        time.sleep(2)  # wait briefly for error message to appear
        try:
            error_element = self.driver.find_element(By.XPATH, "//div[contains(@class, 'error')]")
            error_text = error_element.text.strip().lower()

            if error_element and error_text:
                logger.error(f"Login error detected: {error_text}")
                return True
        except NoSuchElementException:
            logger.info("No login error message detected.")
        
        return False

    def is_on_job_posting_form(self) -> bool:
        """
        Check if currently on the job posting form.
        
        Returns:
            bool: True if on form, False otherwise
        """
        try:
            logger.info("Checking if job posting form is loaded...")

            # Wait for form presence
            self.wait.until(
                EC.presence_of_element_located((By.NAME, "createJobProfileForm"))
            )

            # Verify "Company" label exists within the form
            self.driver.find_element(By.XPATH, "//label[@for='campus_placement' and contains(text(), 'Company')]")
            
            logger.info("Job posting form is present.")
            return True
        except TimeoutException:
            logger.warning("Job posting form not found in time.")
            return False
        except NoSuchElementException:
            logger.warning("Company label not found inside the form.")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking form presence: {str(e)}")
            return False

    def select_placement_option(self, option_text: str = "Placements 2025") -> bool:
        """
        Select a placement option from the dropdown.
        
        Args:
            option_text: The text of the option to select
            
        Returns:
            bool: True if selection successful, False otherwise
        """
        try:
            # Click the dropdown button
            logger.info("Clicking 'Add Job Profile' dropdown...")
            dropdown_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Add Job Profile')]"))
            )

            # Scroll into view to avoid overlay issues
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", dropdown_button)
            time.sleep(0.5)  # Small delay to ensure visibility

            # Wait until clickable after scroll
            self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Add Job Profile')]"))).click()

            time.sleep(1)

            # Wait for the dropdown to render and select the desired option
            logger.info(f"Looking for dropdown option: {option_text}")
            placement_option = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, f"//ul[contains(@class, 'dropdown-menu')]//a[contains(text(), '{option_text}')]"))
            )
            placement_option.click()

            logger.info(f"'{option_text}' option selected successfully.")
            time.sleep(5)
            return True
        
        except TimeoutException:
            logger.error(f"Dropdown option '{option_text}' not found or not clickable.")
            return False
        except Exception as e:
            logger.error(f"Error selecting '{option_text}': {str(e)}")
            return False

    def add_new_company(self, company_name: str) -> bool:
        """
        Add a new company if it doesn't exist.
        
        Args:
            company_name: Name of the company to add
            
        Returns:
            bool: True if company added successfully, False otherwise
        """
        try:
            no_match_message = self.driver.find_element(By.XPATH, "//p[contains(text(), 'No matching companies found in your account')]")
            if no_match_message.is_displayed():
                logger.info("No matching companies found. Adding a new company...")
        
                add_new_company_button = self.driver.find_element(By.XPATH, "//button[@type='button' and @ng-click='addNewCompany(true);']")
                add_new_company_button.click()
                
                # Wait for the modal popup with the specified header to appear
                logger.info("Waiting for 'Add a Company Contact' modal to appear...")
                self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//h3[@class='modal-title' and text()='Add a Company Contact']"))
                )
                logger.info("'Add a Company Contact' modal is now visible.")

                # Locate the company name input field in the modal
                company_name_input = self.wait.until(
                    EC.presence_of_element_located((By.ID, "companyName"))
                )

                # Enter the company name into the input field
                company_name_input.clear()
                company_name_input.send_keys(company_name)

                logger.info(f"Entered company name '{company_name}' in the modal input field.")

                # Wait for the list of companies to appear
                logger.info("Waiting for the list of companies to load...")
                company_list = self.wait.until(
                    EC.presence_of_all_elements_located(
                        (By.XPATH, "//ul[contains(@class, 'inline-select-list')]/li")
                    )
                )

                # Iterate through the list to find a matching company
                selected = False
                for company in company_list:
                    if company_name.lower() == company.text.lower():
                        logger.info(f"Selecting exact matching company: {company.text}")
                        company.click()
                        selected = True
                        break

                if not selected:
                    logger.warning("No matching company found in the list.")

                # Locate and click the "Add Company" button
                add_company_button = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[@class='btn btn-primary' and @type='submit' and text()='Add Company']"))
                )
                add_company_button.click()
                logger.info("Clicked 'Add Company' button.")

                # Wait for the toast message indicating success
                logger.info("Waiting for success toast message...")
                self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//div[@class='toast-message' and text()='Company added successfully.']"))
                )
                logger.info("Success toast message detected: 'Company added successfully.'")

                return True
                
        except NoSuchElementException:
            logger.info("No 'No matching companies found' message displayed.")
        except Exception as e:
            logger.error(f"Error adding new company: {str(e)}")
        
        return False

    def select_company(self, company_name: str = "Mercedes Benz") -> bool:
        """
        Select a company from the dropdown.
        
        Args:
            company_name: Name of the company to select
            
        Returns:
            bool: True if selection successful, False otherwise
        """
        try:
            logger.info(f"Typing company name: {company_name}")

            # Locate the search box
            company_input = self.wait.until(
                EC.presence_of_element_located((By.ID, "campus_placement"))
            )
            company_input.clear()
            company_input.send_keys(company_name)
            time.sleep(1.5)  # Wait for debounce and dropdown render

            # Wait for the dropdown list to appear
            logger.info("Waiting for company suggestions...")
            suggestions = self.wait.until(
                EC.presence_of_all_elements_located(
                    (By.XPATH, "//ul[contains(@class, 'dropdown-menu')]/li/a")
                )
            )

            # Select the first matching result
            for suggestion in suggestions:
                if company_name.lower() in suggestion.text.lower():
                    logger.info(f"Selecting company: {suggestion.text}")
                    suggestion.click()
                    return True
            
            logger.warning(f"No matching company found for '{company_name}'")
            return False
            
        except TimeoutException:
            logger.error("Timeout while waiting for company suggestions.")
            return False
        except Exception as e:
            logger.error(f"Error during company selection: {str(e)}")
            return False

    def fill_company_data(self, company_name: str) -> bool:
        """
        Fill out company information in the job posting form.
        
        Args:
            company_name: Name of the company
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info("Starting company data input process...")

            company_selected = self.select_company(company_name)

            if not company_selected:
                new_company_added = self.add_new_company(company_name)
                if new_company_added:
                    self.select_company(company_name)
                    logger.info("Company created and selected.")
                else:
                    logger.info("Company selection failed.")
                    return False

            return True
        except Exception as e:
            logger.error(f"Error filling company data: {str(e)}")
            return False
    
    def fill_job_profile_title(self, job_title: str) -> bool:
        """
        Fill the job profile title field.
        
        Args:
            job_title: The title of the job
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Filling job profile title: {job_title}")

            # Locate the job title input field
            job_title_input = self.wait.until(
                EC.presence_of_element_located((By.ID, "title"))
            )

            # Clear the input field and enter the job title
            job_title_input.clear()
            job_title_input.send_keys(job_title)

            logger.info("Job profile title filled successfully.")
            return True
        except TimeoutException:
            logger.error("Timeout while waiting for job title input field.")
            return False
        except Exception as e:
            logger.error(f"Error while filling job profile title: {str(e)}")
            return False

    def fill_job_profile_source(self) -> bool:
        """
        Select 'Campus Placement' as the job profile source.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info("Selecting 'Campus Placement' option from dropdown...")

            # Locate the dropdown container
            dropdown_container = self.wait.until(
                EC.element_to_be_clickable((By.CLASS_NAME, "chosen-container"))
            )
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", dropdown_container)
            time.sleep(0.5)  # Small delay to ensure visibility
            dropdown_container.click()

            # Wait for the dropdown options to appear
            time.sleep(0.5)  # Small delay to ensure options are rendered
            logger.info("Waiting for dropdown options to load...")
            dropdown_options = self.wait.until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "active-result"))
            )

            # Iterate through the options and select 'Campus Placement'
            for option in dropdown_options:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", option)
                option.click()
                logger.info("'Campus Placement' option selected successfully.")
                return True

            logger.error("'Campus Placement' option not found in the dropdown.")
            return False
            
        except TimeoutException:
            logger.error("Timeout while waiting for dropdown options.")
            return False
        except Exception as e:
            logger.error(f"Error while selecting 'Campus Placement': {str(e)}")
            return False

    def fill_job_location(self, location: str) -> bool:
        """
        Fill the job location field.
        
        Args:
            location: The location of the job
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Filling job location: {location}")

            # Locate the job location input field
            location_input = self.wait.until(
                EC.presence_of_element_located((By.ID, "location"))
            )

            # Clear the input field and enter the location
            location_input.clear()
            location_input.send_keys(location)

            logger.info("Job location filled successfully.")
            return True
        except TimeoutException:
            logger.error("Timeout while waiting for job location input field.")
            return False
        except Exception as e:
            logger.error(f"Error while filling job location: {str(e)}")
            return False

    def fill_position_type(self) -> bool:
        """
        Select 'Full Time' as the position type.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info("Selecting 'Full Time' from position type dropdown...")

            # Wait for the dropdown container
            dropdown_container = self.wait.until(
                EC.presence_of_element_located((By.ID, "position_type_chosen"))
            )
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", dropdown_container)

            # Click to open the dropdown
            dropdown_toggle = dropdown_container.find_element(By.CLASS_NAME, "chosen-single")
            dropdown_toggle.click()
            logger.info("Dropdown opened.")

            # Wait for the "Full Time" option to appear and click it
            full_time_option = self.wait.until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//div[@id='position_type_chosen']//ul[contains(@class, 'chosen-results')]/li[normalize-space()='Full Time']"
                ))
            )
            full_time_option.click()
            logger.info("'Full Time' option selected successfully.")

            return True

        except TimeoutException:
            logger.error("Timeout while waiting for position type dropdown or 'Full Time' option.")
        except NoSuchElementException:
            logger.error("Could not find the dropdown or the 'Full Time' option.")
        except ElementClickInterceptedException as e:
            logger.error(f"Click intercepted: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during dropdown selection: {str(e)}")

        return False

    def fill_job_function(self, item) -> bool:
        """
        Select 'Product Management' as the job function.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f'Selecting ${item} as job function...')

            # Open the dropdown
            container = self.wait.until(
                EC.element_to_be_clickable((By.ID, "sectorCode_chosen"))
            )
            container.click()

            # Locate the input box inside the dropdown
            input_box = container.find_element(By.XPATH, ".//input[@class='chosen-search-input' or contains(@class, 'default')]")
            input_box.clear()
            input_box.send_keys(item)

            # Wait for the matching option to appear
            match_option = self.wait.until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    f"//div[@id='sectorCode_chosen']//ul[@class='chosen-results']/li[normalize-space()='{item}']"
                ))
            )
            match_option.click()

            logger.info(f"{item} selected successfully.")
            return True

        except TimeoutException:
            logger.error(f"Timeout while trying to select '{item}'.")
        except Exception as e:
            logger.error(f"Error selecting '{item}': {e}")

        return False

    def fill_category(self) -> bool:
        """
        Select 'Level 1 - Open to all students' as the job category.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info("Selecting 'Level 1 - Open to all students'...")

            # Open the dropdown
            dropdown = self.wait.until(
                EC.element_to_be_clickable((By.ID, "jpCategory_chosen"))
            )
            dropdown.click()

            # Wait and click on the matching option
            option = self.wait.until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//div[@id='jpCategory_chosen']//ul[@class='chosen-results']/li[normalize-space()='Level 1 - Open to all students']"
                ))
            )
            option.click()

            logger.info("'Level 1 - Open to all students' selected successfully.")
            return True

        except Exception as e:
            logger.error(f"Error selecting 'Level 1 - Open to all students': {e}")
            return False

    def add_ctc_details(self, min_salary: int = 100000, max_salary: int = 500000) -> bool:
        """
        Fill in the CTC (Cost to Company) salary range.
        
        Args:
            min_salary: Minimum salary amount
            max_salary: Maximum salary amount
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info("Filling CTC details...")

            # Click "Specify Range"
            specify_range = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//div[text()='Specify Range']")))
            self.driver.execute_script("arguments[0].scrollIntoView(true);", specify_range)
            try:
                specify_range.click()
                logger.info("Clicked on specify range")
            except ElementClickInterceptedException:
                self.driver.execute_script("arguments[0].click();", specify_range)

            # Add a delay to allow animation/rendering
            time.sleep(2)

            # Force scroll to top — if inputs are getting pushed up
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)

            # Use JS to access and set values if not visible/interactable
            min_input = self.driver.find_element(By.ID, "ctcMin")
            max_input = self.driver.find_element(By.ID, "ctcMax")

            # Set min salary using JS
            self.element_interaction.js_input(min_input, min_salary)
            time.sleep(0.5)  # Give Angular time to process

            # Set max salary
            self.element_interaction.js_input(max_input, max_salary)

            logger.info("CTC details filled successfully.")
            return True

        except TimeoutException:
            logger.error("Timeout while waiting for CTC input fields.")
            return False
        except NoSuchElementException:
            logger.error("CTC input fields not found on the page.")
            return False
        except ElementClickInterceptedException as e:
            logger.error(f"Click intercepted while interacting with CTC fields: {e}")
            return False
        except WebDriverException as e:
            logger.error(f"WebDriver exception occurred while filling CTC details: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error filling CTC details: {e}")
            return False

    def click_is_equity_checkbox(self) -> bool:
        """
        Click the 'isEquity' checkbox.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info("Clicking 'isEquity' checkbox...")

            checkbox = self.wait.until(EC.presence_of_element_located((By.ID, "isEquity")))

            # Scroll into view in case it's off-screen
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", checkbox)
            time.sleep(0.5)

            # Click via JavaScript due to potential invisibility
            self.driver.execute_script("arguments[0].click();", checkbox)

            logger.info("'isEquity' checkbox clicked successfully.")
            return True

        except TimeoutException:
            logger.error("Timeout: 'isEquity' checkbox not found.")
            return False
        except Exception as e:
            logger.error(f"Error clicking 'isEquity' checkbox: {e}")
            return False

    def fill_tinymce_field_by_label(self, label_text: str, content: str) -> bool:
        """
        Fill text in a TinyMCE editor field identified by its label.
        
        Args:
            label_text: Text of the label associated with the editor
            content: Content to enter in the editor
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Find label with matching text
            label = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, f"//label[contains(text(), '{label_text}')]"))
            )

            # Find the iframe that follows the label
            iframe = label.find_element(By.XPATH, ".//following::iframe[contains(@id, '_ifr')]")
            self.driver.switch_to.frame(iframe)

            # Wait for and interact with TinyMCE body
            body = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            body.clear()
            body.send_keys(content)

            # Always switch back
            self.driver.switch_to.default_content()

            logger.info(f"Successfully filled content in '{label_text}' field")
            return True

        except (TimeoutException, NoSuchElementException) as e:
            logger.error(f"Error while filling TinyMCE field '{label_text}': {e}")
            try:
                self.driver.switch_to.default_content()  # Ensure clean state
            except:
                pass
            return False

    def click_create_and_confirm(self) -> bool:
        """
        Click the 'Create New Job Profile' button and confirm in the modal.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info("Attempting to click 'Create New Job Profile' button.")
            
            # Find the button
            create_button = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Create New Job Profile')]"))
            )
            
            # Scroll the button into view to ensure it's visible
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", create_button)
            
            # Wait a moment for the scroll to complete
            time.sleep(1)
            
            # Try multiple click methods
            try:
                # First try: standard click
                logger.info("Attempting standard click...")
                create_button.click()
            except ElementClickInterceptedException:
                # Second try: JavaScript click
                logger.info("Standard click failed. Attempting JavaScript click...")
                self.driver.execute_script("arguments[0].click();", create_button)
            except Exception as e:
                logger.warning(f"Both click methods failed: {e}")
                
                # Third try: Find any overlays/dialogs and close them
                try:
                    logger.info("Looking for potential overlays...")
                    overlays = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'modal') or contains(@class, 'overlay')]")
                    if overlays:
                        for overlay in overlays:
                            if overlay.is_displayed():
                                logger.info("Found visible overlay, attempting to close it")
                                close_buttons = overlay.find_elements(By.XPATH, ".//button[contains(@class, 'close') or contains(text(), 'Close')]")
                                if close_buttons:
                                    close_buttons[0].click()
                                    time.sleep(0.5)
                except Exception as overlay_e:
                    logger.warning(f"Error handling overlays: {overlay_e}")
                
                # Try one more time with Actions
                logger.info("Attempting click with Actions chain...")
                from selenium.webdriver.common.action_chains import ActionChains
                actions = ActionChains(self.driver)
                actions.move_to_element(create_button).click().perform()
            
            logger.info("'Create New Job Profile' button clicked or click attempted.")

            # Wait for confirmation modal
            logger.info("Waiting for confirmation modal...")
            ok_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@class='modal-footer']//button[contains(text(), 'OK')]"))
            )
            
            # Scroll to ensure OK button is in view
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", ok_button)
            time.sleep(0.5)
            
            # Try to click the OK button
            try:
                ok_button.click()
            except ElementClickInterceptedException:
                self.driver.execute_script("arguments[0].click();", ok_button)
                
            logger.info("Confirmation 'OK' button clicked successfully.")
            
            # Wait for success message or new page to confirm action completed
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'toast-success') or contains(text(), 'successfully')]"))
                )
                logger.info("Success toast message detected.")
            except TimeoutException:
                logger.info("No success toast message found, but proceeding.")
                
            return True

        except (TimeoutException, NoSuchElementException, WebDriverException) as e:
            logger.error(f"Error during job profile creation: {e}")
            return False

    def select_applicable_courses(self) -> bool:
        """
        Select applicable courses for the job profile.
        
        Returns:
            bool: True if selection successful, False otherwise
        """
        try:
            # Use a longer timeout for this operation
            long_wait = WebDriverWait(self.driver, 30)
            
            logger.info("Waiting for page to fully load after job creation...")
            # Give the page time to fully load and stabilize after job creation
            time.sleep(10)
            
            # Wait for and click the "Select applicable courses" link
            logger.info("Looking for 'Select applicable courses' link...")
            
            try:
                # Try multiple XPath patterns to find the element
                xpath_patterns = [
                    "//li//a[@href='#jp-applicable-courses']//span[contains(@class, 'text') and contains(text(), 'Select applicable courses')]",
                    "//a[@href='#jp-applicable-courses']",
                    "//span[contains(text(), 'Select applicable courses')]",
                    "//li[contains(.,'Select applicable courses')]//a"
                ]
                
                applicable_courses_link = None
                for xpath in xpath_patterns:
                    logger.info(f"Trying to find element with xpath: {xpath}")
                    try:
                        applicable_courses_link = long_wait.until(
                            EC.element_to_be_clickable((By.XPATH, xpath))
                        )
                        if applicable_courses_link:
                            logger.info(f"Found element using xpath: {xpath}")
                            break
                    except:
                        logger.info(f"Element not found with xpath: {xpath}")
                
                if not applicable_courses_link:
                    raise Exception("Could not find 'Select applicable courses' link with any patterns")
                
                # Scroll to ensure element is in view
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", applicable_courses_link)
                time.sleep(3)  # Give more time to ensure element is properly rendered
                
                # Try multiple methods to click the element
                try:
                    # Try normal click first
                    logger.info("Attempting to click using standard click method...")
                    applicable_courses_link.click()
                except Exception as e:
                    logger.warning(f"Standard click failed: {e}")
                    try:
                        # Try JavaScript click if normal click fails
                        logger.info("Attempting JavaScript click...")
                        self.driver.execute_script("arguments[0].click();", applicable_courses_link)
                    except Exception as e2:
                        logger.warning(f"JavaScript click failed: {e2}")
                        # Try action chains as a last resort
                        logger.info("Attempting to click using Actions chain...")
                        from selenium.webdriver.common.action_chains import ActionChains
                        actions = ActionChains(self.driver)
                        actions.move_to_element(applicable_courses_link).click().perform()
            except Exception as e:
                logger.error(f"Failed to click on 'Select applicable courses': {e}")
                # Take screenshot for debugging
                self.driver.save_screenshot("courses_link_error.png")
                return False
            
            # CRITICAL NEW STEP: Click the "Add Eligible Courses" button
            logger.info("Looking for 'Add Eligible Courses' button...")
            try:
                # Wait for the content area to load
                time.sleep(5)
                
                # Try multiple selectors to find the "Add Eligible Courses" button
                add_courses_button_selectors = [
                    (By.XPATH, "//button[contains(@class, 'btn-sm') and contains(@ng-click, 'openEditCourseModal()')]"),
                    (By.XPATH, "//button[contains(@class, 'btn-sm')]//span[contains(@class, 'lnr-plus')]/.."),
                    (By.XPATH, "//button[contains(text(), 'Add Eligible Courses')]"),
                    (By.XPATH, "//button[contains(@ng-click, 'openEditCourseModal')]")
                ]
                
                add_courses_button = None
                for selector in add_courses_button_selectors:
                    try:
                        logger.info(f"Trying to find 'Add Eligible Courses' button with: {selector}")
                        add_courses_button = long_wait.until(
                            EC.element_to_be_clickable(selector)
                        )
                        if add_courses_button:
                            logger.info(f"Found 'Add Eligible Courses' button with {selector}")
                            break
                    except:
                        logger.info(f"'Add Eligible Courses' button not found with {selector}")
                
                if not add_courses_button:
                    # Look for any button with a plus icon as a last resort
                    buttons = self.driver.find_elements(By.XPATH, "//button[contains(@class, 'btn')]")
                    for button in buttons:
                        try:
                            if button.is_displayed() and (
                                "Add" in button.text or 
                                "add" in button.text or 
                                button.find_elements(By.XPATH, ".//span[contains(@class, 'lnr-plus') or contains(@class, 'plus') or contains(@class, 'add')]")
                            ):
                                add_courses_button = button
                                logger.info(f"Found potential 'Add Eligible Courses' button with text: {button.text}")
                                break
                        except:
                            continue
                
                if not add_courses_button:
                    # Take screenshot to see the current page state
                    self.driver.save_screenshot("missing_add_courses_button.png")
                    raise Exception("Could not find 'Add Eligible Courses' button with any selectors")
                
                # Scroll to button and click it
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", add_courses_button)
                time.sleep(2)
                
                try:
                    logger.info("Clicking 'Add Eligible Courses' button...")
                    add_courses_button.click()
                except Exception as e:
                    logger.warning(f"Standard button click failed: {e}")
                    try:
                        # Try JavaScript click if normal click fails
                        logger.info("Attempting JavaScript click on 'Add Eligible Courses' button...")
                        self.driver.execute_script("arguments[0].click();", add_courses_button)
                    except Exception as e2:
                        logger.warning(f"JavaScript click failed: {e2}")
                        # Try action chains as a last resort
                        logger.info("Attempting to click using Actions chain...")
                        from selenium.webdriver.common.action_chains import ActionChains
                        actions = ActionChains(self.driver)
                        actions.move_to_element(add_courses_button).click().perform()
                
                time.sleep(3)  # Wait for the modal to appear
            except Exception as e:
                logger.error(f"Failed to click on 'Add Eligible Courses' button: {e}")
                self.driver.save_screenshot("add_courses_button_error.png")
                return False
            
            # Wait for the popup/dialog to appear with a longer timeout
            logger.info("Waiting for course selection popup...")
            try:
                popup = long_wait.until(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'modal-dialog') or contains(@class, 'modal-content')]"))
                )
                logger.info("Course selection popup found")
            except Exception as e:
                logger.error(f"Course selection popup not found: {e}")
                self.driver.save_screenshot("popup_error.png")
                return False
                
            # Rest of the method continues as before
            # Wait for checkboxes to be loaded - try multiple approaches
            logger.info("Looking for course checkboxes...")
            checkboxes = None
            try:
                # Try different locators
                checkbox_locators = [
                    (By.XPATH, "//input[@type='checkbox' and @checklist-model='selectedCourses']"),
                    (By.XPATH, "//input[@type='checkbox' and contains(@class, 'ng-pristine')]"),
                    (By.XPATH, "//input[@type='checkbox']"),
                    (By.CSS_SELECTOR, "input[type='checkbox']")
                ]
                
                for locator in checkbox_locators:
                    try:
                        logger.info(f"Trying to find checkboxes with: {locator}")
                        checkboxes = long_wait.until(
                            EC.presence_of_all_elements_located(locator)
                        )
                        if checkboxes and len(checkboxes) > 0:
                            logger.info(f"Found {len(checkboxes)} checkboxes with {locator}")
                            break
                    except:
                        logger.info(f"No checkboxes found with {locator}")
            except Exception as e:
                logger.error(f"Failed to find any checkboxes: {e}")
                self.driver.save_screenshot("checkbox_error.png")
                return False
            
            if not checkboxes or len(checkboxes) == 0:
                logger.warning("No course checkboxes found.")
                return False
                
            # Try to click the first checkbox
            logger.info("Selecting the first available course...")
            try:
                checkbox = checkboxes[0]
                # Scroll to ensure checkbox is in view
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", checkbox)
                time.sleep(2)
                
                # Try multiple click methods
                try:
                    logger.info("Attempting standard click on checkbox...")
                    checkbox.click()
                except Exception as e:
                    logger.warning(f"Standard checkbox click failed: {e}")
                    try:
                        logger.info("Attempting JavaScript click on checkbox...")
                        self.driver.execute_script("arguments[0].click();", checkbox)
                    except Exception as e2:
                        logger.warning(f"JavaScript checkbox click failed: {e2}")
                        logger.info("Attempting to force check the checkbox...")
                        self.driver.execute_script("arguments[0].checked = true; arguments[0].dispatchEvent(new Event('change'));", checkbox)
            except Exception as e:
                logger.error(f"Failed to select checkbox: {e}")
                self.driver.save_screenshot("checkbox_click_error.png")
                return False
            
            # Wait for Save button and click it
            logger.info("Looking for Save button...")
            try:
                # Try different selectors for the save button
                save_button_selectors = [
                    (By.XPATH, "//button[contains(@class, 'btn-primary') and contains(text(), 'Save') and contains(@ng-click, 'editCourses')]"),
                    (By.XPATH, "//button[contains(@class, 'btn-primary') and contains(text(), 'Save')]"),
                    (By.XPATH, "//button[contains(text(), 'Save')]"),
                    (By.CSS_SELECTOR, ".modal-footer .btn-primary")
                ]
                
                save_button = None
                for selector in save_button_selectors:
                    try:
                        logger.info(f"Trying to find save button with: {selector}")
                        save_button = long_wait.until(
                            EC.element_to_be_clickable(selector)
                        )
                        if save_button:
                            logger.info(f"Found save button with {selector}")
                            break
                    except:
                        logger.info(f"Save button not found with {selector}")
                
                if not save_button:
                    raise Exception("Could not find Save button with any selectors")
                
                # Scroll to save button and click it
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", save_button)
                time.sleep(2)
                
                try:
                    logger.info("Clicking Save button...")
                    save_button.click()
                except Exception as e:
                    logger.warning(f"Standard save button click failed: {e}")
                    self.driver.execute_script("arguments[0].click();", save_button)
            except Exception as e:
                logger.error(f"Error clicking save button: {e}")
                self.driver.save_screenshot("save_button_error.png")
                return False
            
            # Wait longer after saving to ensure the process completes
            logger.info("Waiting 10 seconds after saving course selection...")
            time.sleep(10)
            
            # Look for success indicators
            try:
                success_elements = self.driver.find_elements(By.XPATH, 
                    "//div[contains(@class, 'toast-success') or contains(text(), 'successfully')]")
                if success_elements:
                    logger.info("Found success message after saving courses")
            except:
                logger.info("No explicit success message found, but proceeding")
            
            return True
            
        except TimeoutException as e:
            logger.error(f"Timeout while selecting applicable courses: {e}")
            self.driver.save_screenshot("timeout_error.png")
            return False
        except Exception as e:
            logger.error(f"Error selecting applicable courses: {e}")
            self.driver.save_screenshot("general_error.png")
            return False

    def set_eligibility_criteria(self) -> bool:
        """
        Set eligibility criteria for the job profile by allowing all students.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Use a longer timeout for this operation
            long_wait = WebDriverWait(self.driver, 30)
            
            logger.info("Starting eligibility criteria setup...")
            time.sleep(5)  # Give the page time to fully stabilize
            
            # Click on the "Set eligibility criteria" link
            logger.info("Looking for 'Set eligibility criteria' link...")
            
            # Try multiple XPath patterns to find the element
            eligibility_link_patterns = [
                "//li//a[@href='#jp-eligibility-criteria']//span[contains(@class, 'text') and contains(text(), 'Set eligibility criteria')]",
                "//a[@href='#jp-eligibility-criteria']",
                "//span[contains(text(), 'Set eligibility criteria')]",
                "//li[contains(.,'Set eligibility criteria')]//a"
            ]
            
            eligibility_link = None
            for xpath in eligibility_link_patterns:
                logger.info(f"Trying to find eligibility link with xpath: {xpath}")
                try:
                    eligibility_link = long_wait.until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    if eligibility_link:
                        logger.info(f"Found eligibility link using xpath: {xpath}")
                        break
                except:
                    logger.info(f"Eligibility link not found with xpath: {xpath}")
            
            if not eligibility_link:
                raise Exception("Could not find 'Set eligibility criteria' link with any patterns")
            
            # Scroll to ensure element is in view
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", eligibility_link)
            time.sleep(3)  # Give more time to ensure element is properly rendered
            
            # Try multiple methods to click the element
            try:
                logger.info("Attempting to click eligibility criteria link...")
                eligibility_link.click()
            except Exception as e:
                logger.warning(f"Standard click failed: {e}")
                try:
                    logger.info("Attempting JavaScript click...")
                    self.driver.execute_script("arguments[0].click();", eligibility_link)
                except Exception as e2:
                    logger.warning(f"JavaScript click failed: {e2}")
                    logger.info("Attempting to click using Actions chain...")
                    from selenium.webdriver.common.action_chains import ActionChains
                    actions = ActionChains(self.driver)
                    actions.move_to_element(eligibility_link).click().perform()
            
            # Wait for the eligibility criteria section to load (looking for the "Allow all students" button)
            logger.info("Waiting for 'Allow all students' button to appear...")
            time.sleep(5)  # Give time for the content to load
            
            # Try to find the "Allow all students" button using multiple selectors
            allow_all_button_selectors = [
                (By.XPATH, "//button[contains(@ng-click, 'updateAllEligibileIfNoItemsFlag') and contains(@confirm, 'make all students')]"),
                (By.XPATH, "//button[contains(@class, 'btn-sm')]//span[contains(@class, 'lnr-users')]/.."),
                (By.XPATH, "//button[contains(text(), 'Allow all students')]"),
                (By.XPATH, "//button[contains(@ng-click, 'updateAllEligibileIfNoItemsFlag')]")
            ]
            
            allow_all_button = None
            for selector in allow_all_button_selectors:
                try:
                    logger.info(f"Trying to find 'Allow all students' button with: {selector}")
                    allow_all_button = long_wait.until(
                        EC.element_to_be_clickable(selector)
                    )
                    if allow_all_button:
                        logger.info(f"Found 'Allow all students' button with {selector}")
                        break
                except:
                    logger.info(f"'Allow all students' button not found with {selector}")
            
            if not allow_all_button:
                # Look for any button with "users" icon as a last resort
                try:
                    buttons = self.driver.find_elements(By.XPATH, "//button[contains(@class, 'btn')]")
                    for button in buttons:
                        if button.is_displayed() and (
                            "Allow all" in button.text or 
                            "all students" in button.text or 
                            button.find_elements(By.XPATH, ".//span[contains(@class, 'lnr-users')]")
                        ):
                            allow_all_button = button
                            logger.info(f"Found potential 'Allow all students' button with text: {button.text}")
                            break
                except Exception as e:
                    logger.warning(f"Failed to find alternative 'Allow all students' button: {e}")
            
            if not allow_all_button:
                # Take screenshot to see the current page state
                self.driver.save_screenshot("missing_allow_all_button.png")
                raise Exception("Could not find 'Allow all students' button with any selectors")
            
            # Scroll to ensure button is in view and click it
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", allow_all_button)
            time.sleep(2)
            
            try:
                logger.info("Clicking 'Allow all students' button...")
                allow_all_button.click()
            except Exception as e:
                logger.warning(f"Standard button click failed: {e}")
                try:
                    logger.info("Attempting JavaScript click...")
                    self.driver.execute_script("arguments[0].click();", allow_all_button)
                except Exception as e2:
                    logger.warning(f"JavaScript click failed: {e2}")
                    logger.info("Attempting to click using Actions chain...")
                    from selenium.webdriver.common.action_chains import ActionChains
                    actions = ActionChains(self.driver)
                    actions.move_to_element(allow_all_button).click().perform()
            
            # Wait for confirmation popup and click "Yes"
            logger.info("Waiting for confirmation popup...")
            try:
                # Wait for Yes button to appear in confirmation dialog
                confirm_yes_button = long_wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'btn-primary') and (text()='Yes' or @ng-click='ok()')]"))
                )
                
                logger.info("Found confirmation popup 'Yes' button")
                time.sleep(1)  # Short delay before clicking
                
                # Click the Yes button
                try:
                    logger.info("Clicking 'Yes' button...")
                    confirm_yes_button.click()
                except Exception as e:
                    logger.warning(f"Standard click on Yes button failed: {e}")
                    self.driver.execute_script("arguments[0].click();", confirm_yes_button)
            except Exception as e:
                logger.error(f"Error handling confirmation popup: {e}")
                self.driver.save_screenshot("confirm_popup_error.png")
                return False
            
            # Wait for success indicator or changes to take effect
            logger.info("Waiting for eligibility criteria to be applied...")
            time.sleep(5)  # Wait for the action to complete
            
            # Look for success indicators
            try:
                success_elements = self.driver.find_elements(By.XPATH, 
                    "//div[contains(@class, 'toast-success') or contains(text(), 'successfully')]")
                if success_elements:
                    logger.info("Found success message after setting eligibility criteria")
            except:
                logger.info("No explicit success message found, but proceeding")
            
            # Check if the eligibility is now marked as done
            try:
                done_mark = self.driver.find_element(By.XPATH, 
                    "//a[@href='#jp-eligibility-criteria']//span[contains(@class, 'checklist-done')]")
                if done_mark:
                    logger.info("Eligibility criteria item is now marked as 'done' in the checklist")
            except:
                logger.info("Couldn't verify if eligibility criteria is marked as done")
            
            return True
            
        except TimeoutException as e:
            logger.error(f"Timeout while setting eligibility criteria: {e}")
            self.driver.save_screenshot("eligibility_timeout_error.png")
            return False
        except Exception as e:
            logger.error(f"Error setting eligibility criteria: {e}")
            self.driver.save_screenshot("eligibility_general_error.png")
            return False

    def setup_hiring_workflow(self) -> bool:
        """
        Set up the hiring workflow by adding interview stages and submit the job profile.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Use a longer timeout for this operation
            long_wait = WebDriverWait(self.driver, 30)
            
            logger.info("Starting hiring workflow setup...")
            time.sleep(5)  # Give the page time to fully stabilize
            
            # Click on the "Setup hiring workflow" link
            logger.info("Looking for 'Setup hiring workflow' link...")
            
            # Try multiple XPath patterns to find the element
            workflow_link_patterns = [
                "//li//a[@href='#jp-stages']//span[contains(@class, 'text') and contains(text(), 'Setup hiring workflow')]",
                "//a[@href='#jp-stages']",
                "//span[contains(text(), 'Setup hiring workflow')]",
                "//li[contains(.,'Setup hiring workflow')]//a"
            ]
            
            workflow_link = None
            for xpath in workflow_link_patterns:
                logger.info(f"Trying to find workflow link with xpath: {xpath}")
                try:
                    workflow_link = long_wait.until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    if workflow_link:
                        logger.info(f"Found workflow link using xpath: {xpath}")
                        break
                except:
                    logger.info(f"Workflow link not found with xpath: {xpath}")
            
            if not workflow_link:
                raise Exception("Could not find 'Setup hiring workflow' link with any patterns")
            
            # Scroll to ensure element is in view
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", workflow_link)
            time.sleep(3)  # Give more time to ensure element is properly rendered
            
            # Try multiple methods to click the element
            try:
                logger.info("Attempting to click workflow link...")
                workflow_link.click()
            except Exception as e:
                logger.warning(f"Standard click failed: {e}")
                try:
                    logger.info("Attempting JavaScript click...")
                    self.driver.execute_script("arguments[0].click();", workflow_link)
                except Exception as e2:
                    logger.warning(f"JavaScript click failed: {e2}")
                    logger.info("Attempting to click using Actions chain...")
                    from selenium.webdriver.common.action_chains import ActionChains
                    actions = ActionChains(self.driver)
                    actions.move_to_element(workflow_link).click().perform()
            
            # Wait for the workflow stages to load
            logger.info("Waiting for workflow stages to load...")
            time.sleep(5)  # Give time for the content to load
            
            # Define the stages we want to add in order
            stages = ["Resume shortlisting", "Technical interview", "HR interview"]
            
            # Add each stage
            for stage_name in stages:
                logger.info(f"Looking for '{stage_name}' stage...")
                
                try:
                    # Find the stage container
                    stage_container = long_wait.until(
                        EC.presence_of_element_located((By.XPATH, 
                            f"//div[contains(@class, 'has-light-border') and contains(text(), '{stage_name}')]"))
                    )
                    
                    # Find the Add button within this container
                    add_button = stage_container.find_element(By.XPATH, 
                        ".//button[contains(@ng-click, 'addPopularStage')]")
                    
                    # Scroll to the add button
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", add_button)
                    time.sleep(1)
                    
                    # Click the Add button
                    try:
                        logger.info(f"Adding '{stage_name}' stage...")
                        add_button.click()
                    except Exception as e:
                        logger.warning(f"Standard click failed for '{stage_name}': {e}")
                        self.driver.execute_script("arguments[0].click();", add_button)
                    
                    # Wait a moment for the stage to be added
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Failed to add '{stage_name}' stage: {e}")
                    self.driver.save_screenshot(f"{stage_name.replace(' ', '_')}_stage_error.png")
            
            # Wait for all stages to be processed
            logger.info("Waiting for all stages to be processed...")
            time.sleep(5)
            
            # Look for the Submit Now button
            logger.info("Looking for 'Submit Now' button...")
            
            # Try different selectors for the Submit Now button
            submit_button_selectors = [
                (By.XPATH, "//button[contains(@class, 'btn-success') and contains(@ng-click, 'submitJobProfile')]"),
                (By.XPATH, "//button[contains(text(), 'Submit Now')]"),
                (By.XPATH, "//button[contains(@confirm, 'Are you sure you want to submit job profile')]")
            ]
            
            submit_button = None
            for selector in submit_button_selectors:
                try:
                    logger.info(f"Trying to find submit button with: {selector}")
                    submit_button = long_wait.until(
                        EC.element_to_be_clickable(selector)
                    )
                    if submit_button:
                        logger.info(f"Found submit button with {selector}")
                        break
                except:
                    logger.info(f"Submit button not found with {selector}")
            
            if not submit_button:
                # Look for any button with "Submit" text as a last resort
                try:
                    buttons = self.driver.find_elements(By.XPATH, "//button[contains(@class, 'btn')]")
                    for button in buttons:
                        if button.is_displayed() and ("Submit" in button.text or "submit" in button.text.lower()):
                            submit_button = button
                            logger.info(f"Found potential Submit button with text: {button.text}")
                            break
                except Exception as e:
                    logger.warning(f"Failed to find alternative Submit button: {e}")
            
            if not submit_button:
                logger.error("Submit button not found!")
                self.driver.save_screenshot("missing_submit_button.png")
                return False
            
            # Scroll to ensure submit button is in view
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_button)
            time.sleep(2)
            
            # Click the Submit button
            try:
                logger.info("Clicking Submit button...")
                submit_button.click()
            except Exception as e:
                logger.warning(f"Standard click failed for Submit button: {e}")
                try:
                    self.driver.execute_script("arguments[0].click();", submit_button)
                except Exception as e2:
                    logger.warning(f"JavaScript click failed for Submit button: {e2}")
                    from selenium.webdriver.common.action_chains import ActionChains
                    actions = ActionChains(self.driver)
                    actions.move_to_element(submit_button).click().perform()
            
            # Wait for confirmation dialog and click Yes
            logger.info("Waiting for confirmation dialog...")
            try:
                # Wait for "Yes" button in confirmation dialog
                yes_button = long_wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[text()='Yes' and contains(@class, 'btn-primary')]"))
                )
                
                logger.info("Found confirmation dialog 'Yes' button")
                time.sleep(1)
                
                # Click the Yes button
                yes_button.click()
                logger.info("Clicked 'Yes' to confirm submission")
                
            except Exception as e:
                logger.error(f"Failed to confirm submission: {e}")
                self.driver.save_screenshot("confirm_submit_error.png")
                return False
            
            # Wait for success message or redirect
            logger.info("Waiting for submission to complete...")
            time.sleep(10)
            
            # Look for success indicators
            try:
                success_elements = self.driver.find_elements(By.XPATH, 
                    "//div[contains(@class, 'toast-success') or contains(text(), 'successfully') or contains(text(), 'submitted')]")
                if success_elements:
                    logger.info("Found success message after submission")
                    return True
            except:
                pass
            
            # If no specific success message but no errors either, consider it successful
            logger.info("Job profile submission completed")
            return True
            
        except TimeoutException as e:
            logger.error(f"Timeout during hiring workflow setup: {e}")
            self.driver.save_screenshot("workflow_timeout_error.png")
            return False
        except Exception as e:
            logger.error(f"Error setting up hiring workflow: {e}")
            self.driver.save_screenshot("workflow_general_error.png")
            return False
        
    def teardown(self) -> None:
        """Close the browser and clean up resources."""
        if self.driver:
            logger.info("Closing browser...")
            self.driver.quit()

    def run(self, job_data: Optional[JobData] = None) -> bool:
        """
        Main execution flow for the automation process.
        
        Args:
            job_data: JobData object containing information to fill in the form
            
        Returns:
            bool: True if job posting was successful, False otherwise
        """
        if job_data is None:
            job_data = JobData(
                company_name="Mercedes Benz",
                job_title="Full Stack Developer"
            )
            
        success = False
            
        try:
            self.setup_driver()
            login_success = self.login()
            
            if not login_success:
                logger.error("Login failed, cannot proceed with automation")
                return False
                
            logger.info("Login successful, proceeding with placement selection")
            placement_success = self.select_placement_option()
            
            if not placement_success:
                logger.error("Placement selection failed, cannot proceed with job posting")
                return False
                
            logger.info("Placement selection successful, proceeding with job posting")
            
            # Step 1: Fill company data
            company_name_success = self.fill_company_data(job_data.company_name)
            if not company_name_success:
                logger.error("Company data filling failed")
                return False
                
            # Step 2: Fill job profile title
            job_title_success = self.fill_job_profile_title(job_data.job_title)
            if not job_title_success:
                logger.error("Job title filling failed")
                return False
                
            # Step 3: Fill job profile source
            job_profile_source_success = self.fill_job_profile_source()
            if not job_profile_source_success:
                logger.error("Job profile source filling failed")
                return False
                
            # Step 4: Fill job location
            job_location_success = self.fill_job_location(job_data.location)
            if not job_location_success:
                logger.error("Job location filling failed")
                return False
            logger.info("Job location filled successfully")
            
            # Step 5: Fill position type
            position_type_success = self.fill_position_type()
            if not position_type_success:
                logger.error("Position type filling failed")
                return False
            logger.info("Position type filled successfully")
            
            # Step 6: Fill job function
            job_function_success = self.fill_job_function(job_data.job_function)
            if not job_function_success:
                logger.error("Job function filling failed")
                return False
            logger.info("Job function filled successfully")
            
            # Step 7: Fill category
            fill_category_success = self.fill_category()
            if not fill_category_success:
                logger.error("Category filling failed")
                return False
            logger.info("Category filled successfully")
            
            # Step 8: Add CTC details
            ctc_details_success = self.add_ctc_details(job_data.min_salary, job_data.max_salary)
            if not ctc_details_success:
                logger.error("CTC details filling failed")
                return False
            logger.info("CTC details added successfully")
            
            # Step 9: Check equity checkbox
            equity_check_success = self.click_is_equity_checkbox()
            if not equity_check_success:
                logger.error("Equity checkbox clicking failed")
                return False
            logger.info("Equity checked successfully")
            
            # Step 10: Fill CTC breakdown field
            ctc_breakdown_success = self.fill_tinymce_field_by_label("Salary break-up / Additional Compensation", job_data.salary_breakup)
            if not ctc_breakdown_success:
                logger.error("CTC breakdown filling failed")
                return False
            logger.info("Salary breakdown added successfully")
            
            # Step 11: Fill job description field
            jd_success = self.fill_tinymce_field_by_label("Job Description", job_data.job_description)
            if not jd_success:
                logger.error("Job description filling failed")
                return False
            logger.info("Job description added successfully")
            
            # Final step: Create and confirm job profile
            create_and_confirm_success = self.click_create_and_confirm()
            if not create_and_confirm_success:
                logger.error("Job creation confirmation failed")
                return False
            
            # Step 12: Select applicable courses
            applicable_courses_success = self.select_applicable_courses()
            if not applicable_courses_success:
                logger.error("Applicable courses selection failed")
                return False
            logger.info("Applicable courses selected successfully")
            
            # Step 13: Set eligibility criteria
            eligibility_criteria_success = self.set_eligibility_criteria()
            if not eligibility_criteria_success:
                logger.error("Eligibility criteria setup failed")
                return False
            logger.info("Eligibility criteria set successfully")
            
            # Step 14: Setup hiring workflow
            hiring_workflow_success = self.setup_hiring_workflow()
            if not hiring_workflow_success:
                logger.error("Hiring workflow setup failed")
                return False
            logger.info("Hiring workflow set up successfully")

            logger.info("Job profile created successfully!")
            success = True
            
            # Wait for a moment to see the final state
            time.sleep(10)
            
        except Exception as e:
            logger.exception(f"Unexpected error in automation process: {e}")
            success = False
        finally:
            # Uncomment the following line in production to close the browser
            self.teardown()
            
        return success


def run_automation(url: str, username: str, password: str, headless: bool = False, **job_kwargs: Any) -> bool:
    """
    Helper function to run the automation with specified parameters.
    
    Args:
        url: The URL of the Superset platform
        username: The username for login
        password: The password for login
        headless: Whether to run the browser in headless mode
        **job_kwargs: Additional keyword arguments for job data
        
    Returns:
        bool: True if job posting was successful, False otherwise
    """
    job_data = JobData(**job_kwargs) if job_kwargs else None
    automator = SupersetAutomator(url, username, password, headless)
    return automator.run(job_data)


if __name__ == "__main__":
    # Replace with actual values or load from env/config
    run_automation(
        url="https://app.joinsuperset.com/",
        username="rishikesh@mesaschool.co",
        password="@Mesa2025",
        headless=False,  # Set True to run without opening the browser window
        company_name="Mercedes Benz",
        job_title="Full Stack Developer"
    )