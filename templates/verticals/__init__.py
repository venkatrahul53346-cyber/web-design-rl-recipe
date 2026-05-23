"""VERTICALS registry — explicit dict of vertical_name → module."""
from __future__ import annotations

from typing import Dict

from templates.verticals import (
    auth_flow,
    dashboard_app,
    developer_docs,
    ecom_storefront,
    editorial_pub,
    government,
    healthcare_clinic,
    hotel_booking,
    marketplace,
    news_portal,
    pricing_page,
    portfolio_studio,
    product_splash,
    restaurant,
    saas_landing,
)


VERTICALS: Dict[str, object] = {
    "saas_landing":      saas_landing,
    "developer_docs":    developer_docs,
    "pricing_page":      pricing_page,
    "auth_flow":         auth_flow,
    "editorial_pub":     editorial_pub,
    "dashboard_app":     dashboard_app,
    "portfolio_studio":  portfolio_studio,
    "ecom_storefront":   ecom_storefront,
    "product_splash":    product_splash,
    "restaurant":        restaurant,
    "government":        government,
    "hotel_booking":     hotel_booking,
    "news_portal":       news_portal,
    "healthcare_clinic": healthcare_clinic,
    "marketplace":       marketplace,
}
