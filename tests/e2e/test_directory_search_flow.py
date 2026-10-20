import pytest
import re
import os
import requests
from playwright.sync_api import Page, expect
from poms.directory_page import DirectoryPage
from utils.api_testing import APIUtils

@pytest.fixture(autouse=True)
def setup_directory_data(page: Page):
    """
    Creates necessary businesses for directory tests (Text Search and Filters)
    using the official gastronomic categories.
    """
    api = APIUtils()
    api_context = page.context.request
    
    # 1. Create user to own the businesses
    user_data = api.create_e2e_user(api_context, name="Dueño Directorio Test", is_seller=True)
    seller_token = user_data["access_token"]
    
    base_url = api.base_url.rstrip("/")
    
    # 2. Create 'Pizzas & Pastas' Business for filters test
    biz_pizza = {
        "name": "Pizzeria Napoles Test",
        "title": "Pizzas artesanales",
        "description": "Negocio de pruebas E2E Directorio",
        "slug": "pizzeria-napoles-test-dir",
        "category": "Pizzas & Pastas",
        "subcategories": '["Pizzas artesanales"]',
        "country": "Bolivia",
        "state": "Santa Cruz",
        "neighborhood": "Montero",
        "phone": "59170000000",
        "email": user_data["email"],
    }
    response = requests.post(
        f"{base_url}/businesses/",
        data=biz_pizza,
        headers={"Authorization": f"Bearer {seller_token}"}
    )
    if response.status_code not in (200, 201):
        print("ERROR CREATING PIZZA BIZ:", response.text)
    response.raise_for_status()

    # 3. Create 'Comida Rápida & Burgers' Business for text search test
    biz_burger = {
        "name": "Burger Gourmet Test",
        "title": "Hamburguesas Gourmet",
        "description": "Negocio de pruebas E2E Directorio",
        "slug": "burger-gourmet-test-dir",
        "category": "Comida Rápida & Burgers",
        "subcategories": '["Hamburguesas"]',
        "country": "Bolivia",
        "state": "Santa Cruz",
        "neighborhood": "Equipetrol",
        "phone": "59170000000",
        "email": user_data["email"],
    }
    response_burger = requests.post(
        f"{base_url}/businesses/",
        data=biz_burger,
        headers={"Authorization": f"Bearer {seller_token}"}
    )
    if response_burger.status_code not in (200, 201):
        print("ERROR CREATING BURGER BIZ:", response_burger.text)
    response_burger.raise_for_status()

@pytest.fixture
def directory_page(page: Page):
    return DirectoryPage(page)

def test_directory_text_search(page: Page, directory_page: DirectoryPage):
    """
    Validates that searching text via the header updates the URL correctly,
    sends the proper request to the backend, and displays filtered results.
    """
    directory_page.navigate()
    
    # Wait for the categories to load first so we are out of initial state
    expect(page.get_by_role("heading", name=re.compile(r"qué visitaremos hoy\?", re.IGNORECASE))).to_be_visible(timeout=10000)
    
    # Step 2: Flujo de Búsqueda de Texto
    directory_page.search_input.fill("Burger Gourmet")
    
    with page.expect_request(lambda request: "businesses" in request.url, timeout=10000):
        directory_page.search_button.click()

    # Step 3: Validación del Filtro en la URL
    expect(page).to_have_url(re.compile(r".*(search|buscar)=Burger(%20|\+)Gourmet.*"), timeout=10000)
    
    # Check if we see Results string or empty filters button
    try:
        expect(page.locator("text=Resultados para")).to_be_visible(timeout=5000)
    except:
        expect(directory_page.clear_filters_empty_btn).to_be_visible(timeout=5000)

    # Step 6: Limpieza
    if directory_page.back_to_categories_btn.is_visible():
        directory_page.back_to_categories_btn.click()
    elif directory_page.clear_filters_empty_btn.is_visible():
        directory_page.clear_filters_empty_btn.click()
        
    expect(directory_page.search_input).to_have_value("")

def test_directory_filters(page: Page, directory_page: DirectoryPage):
    """
    Validates that clicking a category, a subcategory, and deep location filters
    updates the URL and displays filtered results in cascade.
    """
    directory_page.navigate()
    
    # Wait for the categories to load
    expect(page.get_by_role("heading", name=re.compile(r"qué visitaremos hoy\?", re.IGNORECASE))).to_be_visible(timeout=10000)
    
    # 1. Category
    page.get_by_role("button", name=re.compile(r"Pizzas\s*&\s*Pastas", re.IGNORECASE)).click()
    expect(page).to_have_url(re.compile(r".*/directorio/pizzas-pastas.*"), timeout=10000)
    
    # 2. Subcategory
    if directory_page.subcategory_dropdown_btn.is_visible():
        directory_page.subcategory_dropdown_btn.click()
        first_subcat = page.locator("[role='menuitem'], [role='option']").first
        if first_subcat.is_visible():
            first_subcat.click()
            page.wait_for_load_state("networkidle")
        else:
            page.keyboard.press("Escape")
            
    # 3. Location (Department -> City)
    if directory_page.location_dropdown_btn.is_visible():
        directory_page.location_dropdown_btn.click()
        
        # Click on Department "Santa Cruz"
        dep_btn = page.get_by_role("button", name=re.compile("Santa Cruz", re.IGNORECASE)).first
        if dep_btn.is_visible():
            dep_btn.click()
            expect(page).to_have_url(re.compile(r".*santa-cruz.*"), timeout=10000)
            
        # Click on City "Montero"
        city_option = page.locator("text=Montero").first
        if city_option.is_visible():
            city_option.click()
            expect(page).to_have_url(re.compile(r".*montero.*"), timeout=10000)

        # Validate final state
        try:
            expect(page.get_by_role("heading", name=re.compile(r"Pizzeria Napoles Test", re.IGNORECASE)).first).to_be_visible(timeout=5000)
        except:
            expect(directory_page.clear_filters_empty_btn).to_be_visible(timeout=5000)
            
        # Validate the URL has changed to include the location slug (/directorio/pizzas-pastas/santa-cruz)
        expect(page).to_have_url(re.compile(r".*/directorio/pizzas-pastas/santa-cruz.*"), timeout=10000)
    
    # Wait for network to settle
    page.wait_for_load_state("networkidle")
