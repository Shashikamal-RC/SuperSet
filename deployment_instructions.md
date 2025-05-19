# SuperSet Job Posting Automation

This application automates job posting on the SuperSet platform.

## Deployment Instructions for Linux Servers

### Prerequisites

The application uses Selenium with Chrome WebDriver for automation. On Linux servers, you need to install the necessary dependencies:

```bash
# Update package repository
sudo apt update

# Install Chromium browser and ChromeDriver
sudo apt install -y chromium-browser chromium-chromedriver

# Install required libraries
sudo apt install -y libglib2.0-0 libnss3 libgconf-2-4 libfontconfig1

# Make sure ChromeDriver is executable
sudo chmod +x /usr/bin/chromedriver
```

### Verify Installation

Check if the installation was successful:

```bash
# Check Chrome version
chromium-browser --version

# Check ChromeDriver version
chromedriver --version
```

Make sure both Chrome and ChromeDriver are installed and have compatible versions.

### Environment Variables

You can configure the application behavior using environment variables:

- `HEADLESS`: Set to "True" to run Chrome in headless mode (default: "False")
- `USE_REMOTE_WEBDRIVER`: Set to "True" to use remote WebDriver mode (default: "False")

### Debugging ChromeDriver Issues

If you encounter ChromeDriver errors:

1. Check if ChromeDriver is in the PATH:
   ```bash
   which chromedriver
   ```

2. Verify ChromeDriver permissions:
   ```bash
   ls -la $(which chromedriver)
   ```

3. Check if the application user has permission to execute ChromeDriver:
   ```bash
   # Make ChromeDriver executable by all users
   sudo chmod +x $(which chromedriver)
   ```

4. Test ChromeDriver manually:
   ```bash
   chromedriver --version
   ```

5. Common locations for ChromeDriver:
   - `/usr/bin/chromedriver`
   - `/usr/local/bin/chromedriver`
   - `/snap/bin/chromedriver`
   - `/home/appuser/.local/bin/chromedriver`

### Alternative: Using Selenium Grid

For more reliable automation in production environments, consider using Selenium Grid:

1. Run Selenium Grid container:
   ```bash
   docker run -d -p 4444:4444 --shm-size="2g" selenium/standalone-chrome:latest
   ```

2. Set environment variable:
   ```bash
   export USE_REMOTE_WEBDRIVER=True
   ```

### Common Error Messages and Solutions

1. **Error: Service unexpectedly exited. Status code was: 127**
   - This means the ChromeDriver executable was not found
   - Solution: Install ChromeDriver (`sudo apt install -y chromium-chromedriver`)

2. **Error: unknown error: Chrome failed to start: crashed**
   - This can happen due to missing dependencies or permission issues
   - Solution: Install the required libraries mentioned above

3. **Error: Permission denied**
   - The ChromeDriver executable doesn't have execution permission
   - Solution: `sudo chmod +x /usr/bin/chromedriver`

4. **Error: DevToolsActivePort file doesn't exist**
   - This happens in Docker/containerized environments
   - Solution: Add these Chrome options:
     - `--no-sandbox`
     - `--disable-dev-shm-usage`
