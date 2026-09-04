"""
RecoverAI - Razorpay Integration Configuration
Reads Razorpay Test Mode credentials and provider settings from environment variables.
Enforces secret protection rules.
"""

import os
from dataclasses import dataclass

@dataclass
class RazorpayConfig:
    RAZORPAY_MODE: str = os.getenv("RAZORPAY_MODE", "mock").lower()
    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID", "rzp_test_mock_key_id")
    RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_KEY_SECRET", "mock_key_secret")
    RAZORPAY_WEBHOOK_SECRET: str = os.getenv("RAZORPAY_WEBHOOK_SECRET", "test_webhook_secret")
    
    # Razorpay REST API Base URL
    API_BASE_URL: str = "https://api.razorpay.com/v1"

    def is_real_test_mode(self) -> bool:
        return self.RAZORPAY_MODE == "test" and self.RAZORPAY_KEY_ID != "rzp_test_mock_key_id"

    def validate_test_credentials(self) -> None:
        """Validates that credentials are format-appropriate for Razorpay Test Mode."""
        if self.is_real_test_mode():
            if not self.RAZORPAY_KEY_ID.startswith("rzp_test_"):
                raise ValueError(
                    "Invalid Razorpay Key ID format. Test Mode Key IDs must start with 'rzp_test_'."
                )
            if not self.RAZORPAY_KEY_SECRET or self.RAZORPAY_KEY_SECRET == "mock_key_secret":
                raise ValueError(
                    "Razorpay Key Secret missing for Test Mode execution."
                )

RAZORPAY_CONFIG = RazorpayConfig()
