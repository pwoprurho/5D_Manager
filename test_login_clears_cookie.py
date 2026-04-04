import httpx

BASE = "http://127.0.0.1:8000"

with httpx.Client() as s:
    print("1. Injecting an expired fake JWT into cookies...")
    s.cookies.set("access_token", "fake_expired_jwt_token", domain="127.0.0.1", path='/')
    
    print("\n2. Making an API request with the token...")
    res_api_expired = s.get(f"{BASE}/api/v1/projects/")
    print("API status with expired token (should be 401 Unauthorized):", res_api_expired.status_code)
    
    print("\n3. Visiting the /login page...")
    res_page = s.get(f"{BASE}/login")
    print("Login page status:", res_page.status_code)
    
    # Check if access_token cookie was cleared correctly
    token_in_cookies = "access_token" in dict(s.cookies)
    print("Is the expired access_token still present in cookies after visiting /login?:", token_in_cookies)
    if token_in_cookies:
        print("Value of access_token cookie:", dict(s.cookies).get("access_token"))

    print("\n4. Making another API request after /login cleared it...")
    res_api_cleared = s.get(f"{BASE}/api/v1/projects/")
    print("API status without token (should be 401 Unauthorized):", res_api_cleared.status_code)

