# -*- coding: utf-8 -*-
"""
Amazon SP API Settings Override
This module overrides the Amazon SP API Settings doctype to customize
the behavior of the Amazon SP API integration.
It includes custom validation for credentials, order details retrieval,
and custom field setup.
"""

from ecommerce_integrations.amazon.doctype.amazon_sp_api_settings.amazon_sp_api import SPAPI as BaseAPI, SPAPIError, Util
from ecommerce_integrations.amazon.doctype.amazon_sp_api_settings.amazon_sp_api import Finances as BaseFinances
from ecommerce_integrations.amazon.doctype.amazon_sp_api_settings.amazon_sp_api import Orders as BaseOrders
from ecommerce_integrations.amazon.doctype.amazon_sp_api_settings.amazon_sp_api import CatalogItems as BaseCatalogItems
import requests


class SPAPI(BaseAPI):
    """
    Simplified Amazon SP-API class that uses only OAuth tokens
    without requiring AWS credentials
    """
    
    AUTH_URL = "https://api.amazon.com/auth/o2/token"
    
    BASE_URI = "/"
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        country_code: str = "US",
        iam_arn=None, 
        aws_access_key=None, 
        aws_secret_key=None
    ) -> None:
        # Only store the OAuth credentials, no AWS credentials
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.country_code = country_code

        if iam_arn and aws_access_key and aws_secret_key:
            self.iam_arn = iam_arn
            self.aws_access_key = aws_access_key
            self.aws_secret_key = aws_secret_key
        else:
            self.iam_arn = None
            self.aws_access_key = None
            self.aws_secret_key = None
        
        # Get marketplace data
        self.region, self.endpoint, self.marketplace_id = Util.get_marketplace_data(country_code)
        
        # Initialize access token
        self._access_token = None
    
    def get_access_token(self) -> str:
        """Get or refresh the access token"""
        if self._access_token:
            return self._access_token
            
        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        response = requests.post(url=self.AUTH_URL, data=data, headers=headers)
        result = response.json()
        
        if response.status_code == 200:
            self._access_token = result.get("access_token")
            return self._access_token
        
        exception = SPAPIError(
            error=result.get("error"), 
            error_description=result.get("error_description")
        )
        raise exception
    
    def get_headers(self) -> dict:
        """Get request headers with access token"""
        return {
            "x-amz-access-token": self.get_access_token(),
            "User-Agent": "python-amazon-mws/0.0.1 (Language=Python)",
            "Content-Type": "application/json"
        }
    
    def make_request(
        self, 
        method: str = "GET", 
        append_to_base_uri: str = "", 
        params: dict = None, 
        data: dict = None,
    ) -> dict:
        """Make API request using only the access token (no AWS auth)"""
        if isinstance(params, dict):
            params = Util.remove_empty(params)
        if isinstance(data, dict):
            data = Util.remove_empty(data)
            
        url = self.endpoint + self.BASE_URI + append_to_base_uri
        
        response = requests.request(
            method=method,
            url=url,
            params=params,
            json=data,  # Use json instead of data for proper JSON formatting
            headers=self.get_headers()
        )
        
        if response.status_code >= 400:
            raise SPAPIError(
                error=f"HTTP {response.status_code}", 
                error_description=response.text
            )
            
        return response.json()


class Finances(SPAPI, BaseFinances):
    """Amazon Finances API with simplified auth"""
    
    BASE_URI = "/finances/v0/"  
    

class Orders(SPAPI, BaseOrders):
    """Amazon Orders API with simplified auth"""
    
    BASE_URI = "/orders/v0/orders"


class CatalogItems(SPAPI, BaseCatalogItems):
    """Amazon Catalog Items API with simplified auth"""
    
    BASE_URI = "/catalog/v0"