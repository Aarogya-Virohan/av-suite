import asyncio
import re
from playwright import async_api
from playwright.async_api import expect

async def run_test():
    pw = None
    browser = None
    context = None

    try:
        # Start a Playwright session in asynchronous mode
        pw = await async_api.async_playwright().start()

        # Launch a Chromium browser in headless mode with custom arguments
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--window-size=1280,720",
                "--disable-dev-shm-usage",
                "--ipc=host",
                "--single-process"
            ],
        )

        # Create a new browser context (like an incognito window)
        context = await browser.new_context()
        # Wider default timeout to match the agent's DOM-stability budget;
        # auto-waiting Playwright APIs (expect, locator.wait_for) inherit this.
        context.set_default_timeout(15000)

        # Open a new page in the browser context
        page = await context.new_page()

        # Interact with the page elements to simulate user flow
        # -> navigate
        await page.goto("http://localhost:3000")
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
        
        # -> Navigate to the clinic booking page at /booking/avtest and check for the appointment request form and service/time selectors.
        await page.goto("http://localhost:3000/booking/avtest")
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
        
        # -> Click the 'Physiotherapy Consultation' service button to reveal time selection controls.
        # Physiotherapy Consultation button
        elem = page.get_by_role('button', name='Physiotherapy Consultation', exact=True)
        await elem.click(timeout=10000)
        
        # --> Assertions to verify final state
        
        # --> The booking card 'Request an appointment online' is visible.
        # Assert-outcome: passed
        # Assert: Booking card header 'Request an appointment online' is visible.
        await expect(page.locator("xpath=/html/body/div[2]/div/div[1]/div[1]").nth(0)).to_contain_text("Request an appointment online", timeout=15000), "Booking card header 'Request an appointment online' is visible."
        
        # --> Service selection controls are available on the booking page.
        # Assert-outcome: passed
        # Assert: Step label '1. Service' is visible, indicating service selection is available.
        await expect(page.locator("xpath=/html/body/div[2]/div/div[1]/div[1]").nth(0)).to_contain_text("1. Service", timeout=15000), "Step label '1. Service' is visible, indicating service selection is available."
        
        # --> Time selection controls (Preferred Time Slot buttons) are visible after selecting a service.
        # Assert-outcome: passed
        # Assert: Preferred Time Slot button '10:00 AM' is visible.
        await expect(page.locator("xpath=/html/body/div[2]/div/form/div/div[2]/div/button[2]").nth(0)).to_have_text("10:00 AM", timeout=15000), "Preferred Time Slot button '10:00 AM' is visible."
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
    